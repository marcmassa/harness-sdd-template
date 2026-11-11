"""R16-R17: requirement evidence, unfinished tasks, checks, and closing review."""
import os
import tempfile
from pathlib import Path

from workflow_support import WorkflowTest, ops
import evidence
import workflow

IDS = ['R1', 'R2']


def automated(requirement, revision, source='tests/test_sample.py::Sample::test_one'):
    return {'requirement_id': requirement, 'kind': 'automated', 'source': source, 'result': 'passed',
            'revision': revision, 'check_command': 'python3 -m unittest'}


class TaskParsingTests(WorkflowTest):
    def test_codex_reproduction_unbolded_pending_task_blocks(self):
        with self.assertRaisesRegex(ValueError, 'unfinished required tasks: T2'):
            evidence.validate_tasks('- [x] **T1** done\n- [ ] T2 unfinished\n')

    def test_completed_tasks_pass_in_supported_forms(self):
        evidence.validate_tasks('- [x] **T1** — a\n- [X] T2 — b\n* [x] **T3**: c\n1. [x] T4 d\n')

    def test_unfinished_variants_block(self):
        for line in ('- [ ] **T2** x', '* [ ] T2 x', '+ [ ] T2 x', '1. [ ] T2 x', '-[ ] T2 x',
                     '  - [ ] **T2** nested', '- [~] T2 partial', '- [] T2 empty', '[ ] T2 bare box'):
            with self.subTest(line), self.assertRaises(ValueError):
                evidence.validate_tasks('- [x] **T1** ok\n{}\n'.format(line))

    def test_malformed_declarations_rejected(self):
        for line, pattern in (('- [x] finished without id', 'malformed task'),
                              ('- **T2** — no checkbox', 'no checkbox'),
                              ('**T2** — no checkbox', 'no checkbox'),
                              ('- [x] **T1** duplicate', 'duplicate')):
            with self.subTest(line), self.assertRaisesRegex(ValueError, pattern):
                evidence.validate_tasks('- [x] **T1** ok\n{}\n'.format(line))

    def test_empty_task_file_rejected(self):
        with self.assertRaisesRegex(ValueError, 'no required tasks'):
            evidence.validate_tasks('# Tasks\n\nNothing here.\n')

    def test_links_and_prose_are_not_tasks(self):
        evidence.validate_tasks('- [x] **T1** ok\n[see docs](x.md)\n| T9 | table row |\nThe T2 step is prose.\n')


class RequirementParsingTests(WorkflowTest):
    def test_declared_identifiers(self):
        self.assertEqual(evidence.requirement_ids('### R1 — a\n\n### R12\n'), ['R1', 'R12'])

    def test_malformed_and_duplicate_declarations_rejected(self):
        for text in ('### R1\n### R1\n', '### R3a — x\n', '## R4 — wrong level\n', '####R5\n', 'no requirements\n'):
            with self.subTest(text), self.assertRaises(ValueError):
                evidence.requirement_ids(text)


class EvidenceTests(WorkflowTest):
    def validate(self, entries, revision=None):
        return evidence.validate_evidence(IDS, entries, revision or self.head(), self.root, self.policy, 'agent-session')

    def good(self):
        head = self.head()
        return [automated('R1', head), automated('R2', head, 'tests/test_sample.py::test_two')]

    def test_complete_evidence_accepted_and_multiple_entries_allowed(self):
        self.validate(self.good())
        entries = self.good() + [automated('R1', self.head(), 'tests/test_sample.py::Sample')]
        self.assertEqual(len(self.validate(entries)['R1']), 2)

    def test_missing_requirement_blocks(self):
        with self.assertRaisesRegex(ValueError, 'missing requirement evidence: R2'):
            self.validate(self.good()[:1])

    def test_unknown_requirement_blocks(self):
        with self.assertRaisesRegex(ValueError, 'unknown evidence'):
            self.validate(self.good() + [automated('R9', self.head())])

    def test_failed_entry_blocks_even_with_another_pass(self):
        bad = automated('R1', self.head())
        bad['result'] = 'failed'
        with self.assertRaisesRegex(ValueError, 'must pass'):
            self.validate(self.good() + [bad])

    def test_stale_revision_blocks(self):
        entries = self.good()
        self.commit('new candidate')
        with self.assertRaisesRegex(ValueError, 'stale evidence'):
            self.validate(entries)

    def test_arbitrary_revision_shape_rejected(self):
        fake = 'a' * 40
        with self.assertRaisesRegex(ValueError, 'not a commit'):
            self.validate([automated('R1', fake), automated('R2', fake)], fake)

    def test_short_revision_rejected(self):
        with self.assertRaisesRegex(ValueError, 'full Git object id'):
            self.validate([], self.head()[:12])

    def test_symbol_must_exist(self):
        for source, pattern in (('tests/test_sample.py::test_missing', 'not found'),
                                ('tests/test_sample.py::Sample::test_missing', 'not found'),
                                ('tests/test_sample.py::helper', 'not found'),
                                ('tests/test_sample.py::Sample::helper', 'not found'),
                                ('tests/test_sample.py::', 'not found'),
                                ('tests/test_sample.py', 'path::test_symbol')):
            with self.subTest(source), self.assertRaisesRegex(ValueError, pattern):
                self.validate([automated('R1', self.head(), source)])

    def test_non_test_file_cannot_claim_automated_coverage(self):
        self.write('README.md', 'test_one\n')
        head = self.commit()
        with self.assertRaisesRegex(ValueError, 'test file'):
            self.validate([automated('R1', head, 'README.md::test_one')], head)

    def test_shell_symbol_must_be_a_function(self):
        self.write('tests/test_s.sh', 'test_real() { true; }\n# test_comment\n')
        head = self.commit()
        evidence._verify_test_reference(self.root, 'tests/test_s.sh::test_real', head)
        with self.assertRaisesRegex(ValueError, 'not found'):
            evidence._verify_test_reference(self.root, 'tests/test_s.sh::test_comment', head)

    def test_symbol_only_in_working_tree_does_not_count(self):
        head = self.head()
        path = self.root / 'tests/test_sample.py'
        path.write_text(path.read_text() + '\n\ndef test_uncommitted():\n    pass\n')
        with self.assertRaisesRegex(ValueError, 'not found at candidate'):
            evidence._verify_test_reference(self.root, 'tests/test_sample.py::test_uncommitted', head)

    def test_untracked_test_file_does_not_count(self):
        head = self.head()
        self.write('tests/test_new.py', 'def test_x():\n    pass\n')
        with self.assertRaisesRegex(ValueError, 'not in candidate'):
            evidence._verify_test_reference(self.root, 'tests/test_new.py::test_x', head)

    def test_traversal_and_absolute_sources_rejected(self):
        for source in ('../outside.py::test_x', '/etc/hosts::test_x', 'tests/../../x.py::test_x'):
            with self.subTest(source), self.assertRaises(ValueError):
                evidence._source_exists(self.root, source)

    def test_codex_reproduction_symlink_file_escape_rejected(self):
        with tempfile.TemporaryDirectory() as outside:
            target = Path(outside) / 'outside.py'
            target.write_text('def test_x():\n    pass\n')
            os.symlink(str(target), str(self.root / 'tests/test_link.py'))
            with self.assertRaisesRegex(ValueError, 'escapes the repository'):
                evidence._source_exists(self.root, 'tests/test_link.py::test_x')

    def test_external_symlink_directory_rejected(self):
        with tempfile.TemporaryDirectory() as outside:
            (Path(outside) / 'test_x.py').write_text('def test_x():\n    pass\n')
            os.symlink(outside, str(self.root / 'tests/linked'))
            with self.assertRaisesRegex(ValueError, 'escapes the repository'):
                evidence._source_exists(self.root, 'tests/linked/test_x.py::test_x')

    def test_internal_symlink_resolves_to_tracked_target(self):
        os.symlink('test_sample.py', str(self.root / 'tests/test_alias.py'))
        head = self.commit('alias')
        self.assertEqual(evidence._source_exists(self.root, 'tests/test_alias.py::test_two'), 'tests/test_sample.py')
        evidence._verify_test_reference(self.root, 'tests/test_alias.py::test_two', head)

    def test_git_internals_are_not_evidence(self):
        for source in ('.git/HEAD', 'sub/.git/config::test_x'):
            with self.subTest(source), self.assertRaisesRegex(ValueError, 'inside the repository'):
                evidence._source_exists(self.root, source)

    def manual(self, **changes):
        self.write('docs/review.md', 'reviewed\n')
        head = self.commit('manual evidence')
        item = {'requirement_id': 'R1', 'kind': 'manual', 'source': 'docs/review.md', 'result': 'reviewed',
                'revision': head, 'reviewer': 'Dana', 'reviewer_role': 'human-reviewer'}
        item.update(changes)
        return item, head

    def test_manual_evidence_accepted_with_human_reviewer(self):
        item, head = self.manual()
        evidence.validate_evidence_item(item, IDS, head, self.root, self.policy, 'agent-session')

    def test_manual_evidence_rejections(self):
        for changes, pattern in (({'reviewer': ''}, 'reviewer required'),
                                 ({'reviewer': 'AGENT-SESSION'}, 'author cannot'),
                                 ({'reviewer_role': 'reviewing-agent'}, 'human reviewer role'),
                                 ({'result': 'passed'}, 'must be reviewed'),
                                 ({'source': 'docs/missing.md'}, 'does not exist')):
            item, head = self.manual(**changes)
            with self.subTest(changes), self.assertRaisesRegex(ValueError, pattern):
                evidence.validate_evidence_item(item, IDS, head, self.root, self.policy, 'agent-session')

    def test_manual_evidence_needs_active_policy(self):
        item, head = self.manual()
        with self.assertRaisesRegex(ValueError, 'active team policy'):
            evidence.validate_evidence_item(item, IDS, head, self.root, None, 'agent-session')

    def test_unknown_kind_rejected(self):
        item = automated('R1', self.head())
        item['kind'] = 'vibes'
        with self.assertRaisesRegex(ValueError, 'automated or manual'):
            self.validate([item])


class ClosingGateTests(WorkflowTest):
    def blocked_by(self, pattern, change):
        self.ready_for_closure()
        change()
        before = self.snapshot()
        self.assert_rejected(pattern, ops.mutate_transition, self.root, 'FEAT-A', 'done')
        self.assertEqual(self.snapshot(), before)
        self.assertEqual(self.read_json('feature_list.json')['features'][0]['status'], 'in_progress')

    def alter(self, **changes):
        record = self.record()
        record.update(changes)
        self.save_record(record)

    def test_complete_closure_succeeds_and_binds_revision(self):
        self.ready_for_closure()
        result = ops.mutate_transition(self.root, 'FEAT-A', 'done')
        self.assertEqual(result, {'status': 'done', 'hook_failed': False, 'legacy': False,
                                  'assurance': 'declared-local-decision'})
        record = self.record()
        self.assertEqual(record['revision'], self.head())
        self.assertIn('[PASS]', ops.check_repository(self.root))

    def test_done_record_remains_valid_after_later_commits(self):
        self.ready_for_closure()
        ops.mutate_transition(self.root, 'FEAT-A', 'done')
        self.commit('record closure')
        self.write('later.txt', 'more\n')
        self.commit('later work')
        self.assertIn('[PASS]', ops.check_repository(self.root))

    def test_unfinished_task_blocks(self):
        def change():
            path = self.root / 'specs/feat-a/tasks.md'
            path.write_text(path.read_text().replace('- [x] **T2**', '- [ ] **T2**'))
            self.commit('reopen task')
            self.alter(evidence=[dict(item, revision=self.head()) for item in self.record()['evidence']])
        self.blocked_by('unfinished required tasks', change)

    def test_missing_evidence_blocks(self):
        self.blocked_by('missing requirement evidence', lambda: self.alter(evidence=[]))

    def test_failed_check_blocks(self):
        self.blocked_by('mandatory check failed', lambda: self.alter(
            checks=[dict(self.record()['checks'][0], result='failed')]))

    def test_missing_check_blocks(self):
        self.blocked_by('mandatory check evidence', lambda: self.alter(checks=[]))

    def test_optional_marked_check_blocks(self):
        self.blocked_by('not marked required', lambda: self.alter(
            checks=[dict(self.record()['checks'][0], required=False)]))

    def test_new_commit_makes_evidence_stale(self):
        def change():
            self.write('src.txt', 'new\n')
            self.commit('new code')
        self.blocked_by('stale evidence revision', change)

    def test_uncommitted_candidate_change_blocks(self):
        self.blocked_by('working tree differs', lambda: self.write('tests/test_sample.py', 'tampered\n'))

    def test_untracked_candidate_file_blocks(self):
        self.blocked_by('working tree differs', lambda: self.write('new_code.py', 'x = 1\n'))

    def test_progress_and_feature_list_are_exempt_from_dirty_check(self):
        self.ready_for_closure()
        self.write('progress/note.md', 'in flight\n')
        self.assertEqual(ops.mutate_transition(self.root, 'FEAT-A', 'done')['status'], 'done')

    def test_requested_revision_must_be_head(self):
        self.ready_for_closure()
        self.assert_rejected('not the current candidate', ops.mutate_transition, self.root, 'FEAT-A', 'done',
                             {'revision': 'a' * 40})

    def test_missing_review_blocks(self):
        self.blocked_by('independent closing review', lambda: self.alter(closing_review=None))

    def review_change(self, **changes):
        self.alter(closing_review=dict(self.record()['closing_review'], **changes))

    def test_self_review_blocks(self):
        self.blocked_by('author cannot', lambda: self.review_change(reviewer='agent-session'))

    def test_self_review_case_variation_blocks(self):
        self.blocked_by('author cannot', lambda: self.review_change(reviewer=' AGENT-Session '))

    def test_agent_review_blocks_full_sdd(self):
        self.blocked_by('human closing review', lambda: self.review_change(role='reviewing-agent'))

    def test_unauthorized_role_blocks(self):
        self.blocked_by('cannot authorize', lambda: self.review_change(role='implementing-agent'))

    def test_rejected_review_blocks(self):
        self.blocked_by('has not approved', lambda: self.review_change(decision='changes_requested'))

    def test_stale_review_blocks(self):
        self.blocked_by('stale closing review', lambda: self.review_change(revision='a' * 40))

    def test_review_without_reference_blocks(self):
        self.blocked_by('reference required', lambda: self.review_change(evidence_ref=' '))

    def test_run_checks_records_observed_failure(self):
        self.ready()
        self.finish_tasks()
        self.write('check.sh', '#!/bin/sh\nexit 7\n').chmod(0o755)
        self.commit('failing check')
        outcome = ops.run_checks(self.root, 'FEAT-A')
        self.assertEqual((outcome['check'], outcome['exit_code']), ('failed', 7))
        self.assertEqual(self.record()['checks'][0]['result'], 'failed')

    def test_run_checks_refuses_dirty_candidate(self):
        self.ready()
        self.write('uncommitted.py', 'x = 1\n')
        self.assert_rejected('commit the candidate', ops.run_checks, self.root, 'FEAT-A')

    def test_add_evidence_validates_immediately(self):
        self.ready()
        self.assert_rejected('not found', ops.add_evidence, self.root, 'FEAT-A', {
            'requirement_id': 'R1', 'kind': 'automated', 'source': 'tests/test_sample.py::test_nope',
            'result': 'passed', 'check_command': 'x'})
        self.assertEqual(self.record()['evidence'], [])

    def test_closed_feature_stays_valid_after_its_tests_are_renamed(self):
        self.ready_for_closure()
        ops.mutate_transition(self.root, 'FEAT-A', 'done')
        self.commit('close')
        (self.root / 'tests/test_sample.py').rename(self.root / 'tests/test_renamed.py')
        self.commit('later refactor')
        self.assertIn('[PASS]', ops.check_repository(self.root))

    def test_closure_evidence_operations_require_in_progress(self):
        self.init_record()
        self.assert_rejected('in_progress', ops.run_checks, self.root, 'FEAT-A')
        self.assert_rejected('in_progress', ops.record_review, self.root, 'FEAT-A', 'D', 'human-reviewer', 'approved', 'r')


class LightweightTests(WorkflowTest):
    def prepared(self, **overrides):
        data = self.read_json('feature_list.json')
        data['features'].append(self.feature('FIX-1', 'fix-1', 'pending', sdd=False))
        self.write_json('feature_list.json', data)
        self.commit('add fix')
        details = {'scope': 'Fix a typo', 'risk_rationale': 'Docs only', 'author_role': 'implementing-agent',
                   'classified_by': 'maintainer', 'classification_ref': 'classification-note'}
        details.update(overrides)
        ops.create_record(self.root, 'FIX-1', 'agent-session', 'fix/typo', None, (), details)

    def close(self, role='reviewing-agent'):
        ops.mutate_transition(self.root, 'FIX-1', 'in_progress')
        ops.run_checks(self.root, 'FIX-1')
        ops.record_review(self.root, 'FIX-1', 'Other Agent', role, 'approved', 'review-ref', 'link to output')
        return ops.mutate_transition(self.root, 'FIX-1', 'done')

    def test_recorded_lightweight_route_closes(self):
        self.prepared()
        self.assertEqual(self.close()['status'], 'done')
        self.assertIn('[PASS]', ops.check_repository(self.root))

    def test_missing_scope_blocks_start(self):
        self.prepared(scope='')
        self.assert_rejected('missing scope', ops.mutate_transition, self.root, 'FIX-1', 'in_progress')

    def test_risk_flag_forces_full_route(self):
        self.prepared()
        record = self.read_json('progress/work/fix-1.json')
        record['lightweight']['risk_flags']['approval_model'] = True
        self.write_json('progress/work/fix-1.json', record)
        self.assert_rejected('explicit false risk flags', ops.mutate_transition, self.root, 'FIX-1', 'in_progress')

    def test_missing_acceptance_evidence_blocks_review(self):
        self.prepared()
        ops.mutate_transition(self.root, 'FIX-1', 'in_progress')
        self.assert_rejected('acceptance evidence', ops.record_review, self.root, 'FIX-1', 'O', 'reviewing-agent',
                             'approved', 'ref')

    def test_author_role_cannot_close_own_work(self):
        self.prepared(author_role='reviewing-agent')
        self.assert_rejected('independent closing review', self.close)

    def test_non_sdd_work_needs_a_record_under_active_policy(self):
        data = self.read_json('feature_list.json')
        data['features'].append(self.feature('FIX-2', 'fix-2', 'in_progress', sdd=False))
        data['features'][0]['status'] = 'pending'
        self.write_json('feature_list.json', data)
        self.assert_rejected('no work record', ops.check_repository, self.root)


if __name__ == '__main__':
    import unittest
    unittest.main()
