"""R9, R11-R14: state machine, digest-bound approval, and record binding."""
import json
import os

from workflow_support import WorkflowTest, ops, team_policy
import approval
import workflow
import workflow_store


class TransitionTests(WorkflowTest):
    def context(self):
        return {'root': self.root, 'feature_data': self.read_json('feature_list.json')}

    def feature_a(self):
        return workflow.find_feature(self.read_json('feature_list.json'), 'FEAT-A')

    def set_status(self, status, identifier='FEAT-A'):
        data = self.read_json('feature_list.json')
        workflow.find_feature(data, identifier)['status'] = status
        self.write_json('feature_list.json', data)

    def test_approved_spec_moves_to_in_progress(self):
        self.ready()
        self.assertEqual(self.feature_a()['status'], 'in_progress')
        self.assertEqual(self.record()['status'], 'in_progress')

    def test_full_sdd_requires_approval_before_implementation(self):
        self.init_record()
        before = self.snapshot()
        self.assert_rejected('approval record is required', ops.mutate_transition,
                             self.root, 'FEAT-A', 'in_progress')
        self.assertEqual(self.snapshot(), before)

    def test_illegal_transitions_do_not_change_state(self):
        self.init_record()
        for current, target in (('pending', 'done'), ('pending', 'in_progress'), ('spec_ready', 'done'),
                                ('spec_ready', 'pending'), ('done', 'spec_ready'), ('done', 'pending')):
            self.set_status(current)
            record = self.record()
            record['status'] = current
            self.save_record(record)
            before = self.snapshot()
            with self.assertRaises(ValueError, msg='{}->{}'.format(current, target)):
                ops.mutate_transition(self.root, 'FEAT-A', target, {'reason': 'because'})
            self.assertEqual(self.snapshot(), before)

    def test_unknown_target_and_same_status_rejected(self):
        self.init_record()
        self.assert_rejected('unsupported target', ops.mutate_transition, self.root, 'FEAT-A', 'shipped')
        self.assert_rejected('must change status', ops.mutate_transition, self.root, 'FEAT-A', 'spec_ready')

    def test_reopen_requires_reason_and_invalidates_completion(self):
        self.ready_for_closure()
        result = ops.mutate_transition(self.root, 'FEAT-A', 'done')
        self.assertEqual(result['status'], 'done')
        self.assert_rejected('requires a reason', ops.mutate_transition, self.root, 'FEAT-A', 'in_progress')
        ops.mutate_transition(self.root, 'FEAT-A', 'in_progress', {'reason': 'defect found'})
        record = self.record()
        self.assertEqual(record['evidence'], [])
        self.assertNotIn('closing_review', record)
        self.assertNotIn('checks', record)
        self.assertEqual(record['completion_history'][0]['reason'], 'defect found')

    def test_blocked_requires_reason_and_returns_only_to_previous_status(self):
        self.ready()
        self.assert_rejected('requires a reason', ops.mutate_transition, self.root, 'FEAT-A', 'blocked')
        ops.mutate_transition(self.root, 'FEAT-A', 'blocked', {'reason': 'waiting on vendor'})
        self.assert_rejected('previous status', ops.mutate_transition, self.root, 'FEAT-A', 'spec_ready')
        ops.mutate_transition(self.root, 'FEAT-A', 'in_progress')
        self.assertNotIn('blocked_from', self.record())

    def test_blocked_record_without_origin_cannot_choose_return_status(self):
        self.ready()
        ops.mutate_transition(self.root, 'FEAT-A', 'blocked', {'reason': 'wait'})
        record = self.record()
        del record['blocked_from']
        self.save_record(record)
        self.assert_rejected('previous status', ops.mutate_transition, self.root, 'FEAT-A', 'in_progress')

    def test_returning_from_blocked_rechecks_approval(self):
        self.ready()
        ops.mutate_transition(self.root, 'FEAT-A', 'blocked', {'reason': 'wait'})
        self.write('specs/feat-a/design.md', '# changed while blocked\n')
        self.assert_rejected('reapproval required', ops.mutate_transition, self.root, 'FEAT-A', 'in_progress')

    def test_pending_feature_may_be_blocked_before_specs_exist(self):
        ops.create_record(self.root, 'FEAT-B', 'agent-session', 'feat/b', None)
        for name in ('requirements.md', 'design.md', 'tasks.md'):
            (self.root / 'specs/feat-b' / name).unlink()
        ops.mutate_transition(self.root, 'FEAT-B', 'blocked', {'reason': 'needs a decision'})
        self.assertEqual(self.record('feat-b')['status'], 'blocked')


class ApprovalTests(WorkflowTest):
    def test_digest_is_deterministic_and_unambiguous(self):
        first = approval.spec_digest(b'abc', b'def')
        self.assertEqual(first, approval.spec_digest(b'abc', b'def'))
        self.assertNotEqual(first, approval.spec_digest(b'ab', b'cdef'))
        self.assertNotEqual(first, approval.spec_digest(b'def', b'abc'))

    def test_digest_has_no_normalization(self):
        self.assertNotEqual(approval.spec_digest(b'a\n', b''), approval.spec_digest(b'a\r\n', b''))

    def test_changed_requirements_or_design_require_reapproval(self):
        for name in ('requirements.md', 'design.md'):
            with self.subTest(name):
                self.setUp()
                self.ready()
                path = self.root / 'specs/feat-a' / name
                path.write_text(path.read_text() + '\n')
                self.assert_rejected('reapproval required', workflow.validate_transition,
                                     {'id': 'FEAT-A', 'name': 'feat-a', 'status': 'in_progress', 'sdd': True},
                                     'in_progress', self.record(), [], self.policy,
                                     {'root': self.root, 'feature_data': self.read_json('feature_list.json')})
                self.approve()
                self.assertEqual(ops.check_repository(self.root),
                                 '[PASS] team policy and 1 work record(s) validated')

    def test_stale_approval_blocks_check_and_completion(self):
        self.ready_for_closure()
        self.write('specs/feat-a/design.md', '# rewritten\n')
        self.commit('rewrite design')
        self.assert_rejected('reapproval required', ops.check_repository, self.root)
        self.assert_rejected('reapproval required', ops.mutate_transition, self.root, 'FEAT-A', 'done')

    def test_checkbox_changes_preserve_approval(self):
        self.ready()
        self.finish_tasks()
        self.assertIn('[PASS]', ops.check_repository(self.root))

    def test_task_digest_ignores_only_markers(self):
        base = b'- [ ] **T1** build\n'
        self.assertEqual(approval.task_structure_digest(base),
                         approval.task_structure_digest(b'- [x] **T1** build\n'))
        self.assertNotEqual(approval.task_structure_digest(base),
                            approval.task_structure_digest(b'- [ ] **T1** build more\n'))

    def test_changed_task_text_needs_scope_change(self):
        self.ready()
        path = self.root / 'specs/feat-a/tasks.md'
        path.write_text(path.read_text() + '- [ ] **T3** — Extra scope\n')
        self.assert_rejected('beyond completion markers', ops.check_repository, self.root)
        ops.record_scope_change(self.root, 'FEAT-A', 'accepted extra task', 'maintainer',
                                ['task-scope'], 'not-required')
        self.assertIn('[PASS]', ops.check_repository(self.root))

    def test_scope_change_requiring_reapproval_does_not_cover_difference(self):
        self.ready()
        path = self.root / 'specs/feat-a/tasks.md'
        path.write_text(path.read_text() + '- [ ] **T3** — Extra\n')
        ops.record_scope_change(self.root, 'FEAT-A', 'needs signoff', 'maintainer', ['scope'], 'required')
        self.assert_rejected('requires a new approval', ops.check_repository, self.root)
        self.approve()
        self.assertIn('[PASS]', ops.check_repository(self.root))

    def test_agent_cannot_authorize_scope_change_or_approval(self):
        self.ready()
        self.assert_rejected('cannot authorize', ops.record_scope_change, self.root, 'FEAT-A', 'x',
                             'implementing-agent', ['c'], 'not-required')
        self.assert_rejected('cannot authorize', ops.record_approval, self.root, 'FEAT-A', 'Bot',
                             'implementing-agent', 'ref')

    def test_approval_requires_reviewer_and_evidence(self):
        self.init_record()
        self.assert_rejected('reviewer is required', ops.record_approval, self.root, 'FEAT-A', ' ', 'maintainer', 'r')
        self.assert_rejected('evidence reference', ops.record_approval, self.root, 'FEAT-A', 'H', 'maintainer', ' ')

    def test_reapproval_keeps_history(self):
        self.ready()
        self.approve()
        self.assertEqual(len(self.record()['approval_history']), 1)

    def test_fabricated_approved_revision_rejected(self):
        self.ready()
        record = self.record()
        record['approval']['approved_revision'] = 'a' * 40
        self.save_record(record)
        self.assert_rejected('not a commit', ops.check_repository, self.root)

    def test_approved_revision_from_unrelated_history_rejected(self):
        self.ready()
        self.commit('workflow state')
        branch = self.git('rev-parse', '--abbrev-ref', 'HEAD')
        self.git('checkout', '-q', '--orphan', 'unrelated')
        unrelated = self.commit('unrelated root')
        self.git('checkout', '-q', branch)
        record = self.record()
        record['approval']['approved_revision'] = unrelated
        self.save_record(record)
        self.assert_rejected('not an ancestor', ops.check_repository, self.root)


class RecordBindingTests(WorkflowTest):
    """Regressions for gates that a caller could otherwise sidestep."""

    def feature_a(self, status='in_progress'):
        return {'id': 'FEAT-A', 'name': 'feat-a', 'status': status, 'sdd': True}

    def context(self):
        return {'root': self.root, 'feature_data': self.read_json('feature_list.json')}

    def test_none_record_cannot_complete_under_active_policy(self):
        for policy in (self.policy, None):
            self.assert_rejected('requires a work record', workflow.validate_transition,
                                 self.feature_a(), 'done', None, [], policy, self.context())

    def test_caller_cannot_substitute_an_easier_policy(self):
        self.ready()
        easier = json.loads(json.dumps(self.policy))
        easier['max_concurrent'] = 9
        self.write('specs/feat-a/design.md', '# drift\n')
        self.assert_rejected('reapproval', workflow.validate_transition, self.feature_a(),
                             'in_progress', self.record(), [], easier, self.context())

    def test_deleting_opted_in_record_blocks_mutation_and_check(self):
        self.ready()
        (self.root / 'progress/work/feat-a.json').unlink()
        self.assert_rejected('requires a work record', ops.mutate_transition, self.root, 'FEAT-A', 'done')
        self.assert_rejected('no work record', ops.check_repository, self.root)

    def test_done_without_record_needs_historical_listing(self):
        data = self.read_json('feature_list.json')
        data['features'][0]['status'] = 'done'
        self.write_json('feature_list.json', data)
        self.assert_rejected('no work record', ops.check_repository, self.root)
        self.policy['historical_features'] = ['FEAT-A']
        self.write_json('.agents/team-policy.json', self.policy)
        self.assert_rejected('adoption_revision', ops.check_repository, self.root)

    def test_spec_dir_of_another_feature_rejected(self):
        self.ready()
        record = self.record()
        record['spec_dir'] = 'specs/feat-b'
        record['approval']['spec_digest'] = approval.digest_from_spec_dir(self.root / 'specs/feat-b')
        self.save_record(record)
        self.assert_rejected('spec_dir must be', workflow.validate_transition, self.feature_a(),
                             'in_progress', record, [], self.policy, self.context())

    def test_symlinked_spec_directory_rejected(self):
        self.ready()
        target = self.root / 'specs/feat-a'
        target.rename(self.root / 'specs/feat-a-real')
        os.symlink(str(self.root / 'specs/feat-b'), str(target))
        self.assert_rejected('symlink', ops.check_repository, self.root)

    def test_record_for_other_feature_or_status_rejected(self):
        self.ready()
        self.assert_rejected('identifiers differ', workflow.validate_transition,
                             {'id': 'FEAT-B', 'name': 'feat-b', 'status': 'in_progress', 'sdd': True},
                             'in_progress', self.record(), [], self.policy, self.context())
        self.assert_rejected('status differ', workflow.validate_transition, self.feature_a('spec_ready'),
                             'in_progress', self.record(), [], self.policy, self.context())

    def test_misnamed_record_rejected_by_check(self):
        self.ready()
        path = self.root / 'progress/work/feat-a.json'
        path.rename(self.root / 'progress/work/other.json')
        self.assert_rejected('must be named', ops.check_repository, self.root)

    def test_unknown_format_version_refused_with_migration_hint(self):
        self.ready()
        before = self.record()
        before['format_version'] = 2
        self.save_record(before)
        self.assert_rejected('migrate', ops.mutate_transition, self.root, 'FEAT-A', 'blocked', {'reason': 'x'})

    def test_missing_record_fields_rejected(self):
        self.ready()
        for field in ('owner', 'revision', 'dependencies', 'approval', 'handoff'):
            record = self.record()
            del record[field]
            with self.assertRaises(ValueError, msg=field):
                workflow.validate_record(record)
        record = self.record()
        record['branch'] = None
        record['worktree'] = None
        self.assert_rejected('branch or worktree', workflow.validate_record, record)

    def test_fabricated_record_revision_rejected(self):
        self.ready()
        record = self.record()
        record['revision'] = 'b' * 40
        self.save_record(record)
        self.assert_rejected('not a commit', ops.check_repository, self.root)

    def test_risk_must_match_sdd_classification(self):
        self.ready()
        record = self.record()
        record['risk'] = 'lightweight'
        self.save_record(record)
        self.assert_rejected('sdd classification', ops.check_repository, self.root)

    def test_sdd_flag_cannot_be_flipped_to_escape_full_route(self):
        self.ready()
        data = self.read_json('feature_list.json')
        data['features'][0]['sdd'] = False
        self.write_json('feature_list.json', data)
        self.assert_rejected('sdd classification', ops.check_repository, self.root)

    def test_existing_record_is_not_replaced(self):
        self.init_record()
        self.assert_rejected('already exists', self.init_record)

    def test_record_paths_for_unsafe_feature_names_refused(self):
        data = self.read_json('feature_list.json')
        data['features'][0]['name'] = '../../etc'
        self.write_json('feature_list.json', data)
        self.assert_rejected('safe identifier', ops.mutate_transition, self.root, 'FEAT-A', 'blocked', {'reason': 'x'})


class ConcurrencyTests(WorkflowTest):
    def activate_b(self):
        ops.create_record(self.root, 'FEAT-B', 'other-session', 'feat/b', None)
        ops.mutate_transition(self.root, 'FEAT-B', 'spec_ready')
        ops.record_approval(self.root, 'FEAT-B', 'Dana Reviewer', 'maintainer', 'ref')

    def test_default_limit_rejects_second_active_feature(self):
        self.ready()
        self.activate_b()
        self.assert_rejected('maxConcurrent', ops.mutate_transition, self.root, 'FEAT-B', 'in_progress')

    def test_team_policy_may_raise_limit(self):
        self.policy['max_concurrent'] = 2
        self.write_json('.agents/team-policy.json', self.policy)
        self.ready()
        self.activate_b()
        self.assertEqual(ops.mutate_transition(self.root, 'FEAT-B', 'in_progress')['status'], 'in_progress')

    def test_invalid_policy_limit_rejected(self):
        for value in (0, True, '2'):
            self.policy['max_concurrent'] = value
            self.assert_rejected('positive integer', team_policy.validate_policy, self.policy)

    def test_check_detects_hand_edited_second_active_feature(self):
        self.ready()
        data = self.read_json('feature_list.json')
        data['features'][1]['status'] = 'in_progress'
        self.write_json('feature_list.json', data)
        self.assert_rejected('maxConcurrent', ops.check_repository, self.root)

    def test_reopen_honors_limit(self):
        self.ready_for_closure()
        ops.mutate_transition(self.root, 'FEAT-A', 'done')
        self.activate_b()
        ops.mutate_transition(self.root, 'FEAT-B', 'in_progress')
        self.assert_rejected('maxConcurrent', ops.mutate_transition, self.root, 'FEAT-A', 'in_progress',
                             {'reason': 'regression'})


class StoreTests(WorkflowTest):
    def test_atomic_write_preserves_mode_and_leaves_no_temporaries(self):
        path = self.write('progress/state.json', '{}\n')
        path.chmod(0o640)
        workflow_store.write_state_json(self.root, 'progress/state.json', '{}\n', {'a': 1})
        self.assertEqual(path.stat().st_mode & 0o777, 0o640)
        self.assertEqual(json.loads(path.read_text()), {'a': 1})
        self.assertEqual([item.name for item in path.parent.iterdir() if item.name.startswith('.state')], [])


if __name__ == '__main__':
    import unittest
    unittest.main()
