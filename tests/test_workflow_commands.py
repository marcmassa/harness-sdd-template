"""T11/T15: canonical integration, opt-in consumer safety, and unmanaged projects."""
import json
import shutil
import unittest
import uuid

from workflow_support import BOOTSTRAP, ROOT, SCENARIO_PATH, WorkflowTest, clean_env, ops, team_policy
import subprocess
import workflow

COMMANDS = ROOT / '.agents/commands'


class CanonicalCommandTests(unittest.TestCase):
    def text(self, name):
        return (COMMANDS / (name + '.md')).read_text(encoding='utf-8')

    def test_commands_use_the_shared_gates(self):
        for name, phrases in (('spec', ['workflow-init', 'workflow-transition', '--target spec_ready']),
                              ('approve', ['workflow-approve', 'workflow-transition', '--target in_progress']),
                              ('implement', ['workflow-validate', '--target in_progress']),
                              ('done', ['workflow-evidence', 'workflow-run-checks', 'workflow-review',
                                        '--target done']),
                              ('status', ['workflow-check'])):
            for phrase in phrases:
                self.assertIn(phrase, self.text(name), '{}: {}'.format(name, phrase))

    def test_human_gates_are_retained(self):
        self.assertIn('Only the human may approve', self.text('approve'))
        self.assertIn('not authentication', self.text('approve'))
        self.assertIn('Never invent reviewer names', self.text('done'))
        self.assertIn('external documents', self.text('implement').lower())

    def test_commands_do_not_edit_status_directly(self):
        for name in ('spec', 'approve', 'done'):
            self.assertNotRegex(self.text(name), r'[Ss]et `status: "(in_progress|done)"`')
            self.assertNotIn('status: "done"`.', self.text(name))

    def test_generated_adapter_delegates_to_canonical_body(self):
        generated = ROOT / '.claude/commands/approve.md'
        if not generated.exists():
            self.skipTest('claude-code adapter is not rendered in this checkout')
        self.assertIn('.agents/commands/approve.md', generated.read_text(encoding='utf-8'))


class BootstrapDispatchTests(WorkflowTest):
    def test_subcommands_are_dispatched(self):
        self.init_record()
        result = self.bootstrap('workflow-approve', '--feature-id', 'FEAT-A', '--reviewer', 'Dana', '--role',
                                'maintainer', '--evidence-ref', 'chat-ref')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('declared-local-decision', result.stdout)
        result = self.bootstrap('workflow-transition', '--feature-id', 'FEAT-A', '--target', 'in_progress')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('[PASS]', self.bootstrap('workflow-check').stdout)

    def test_rejected_transition_exits_nonzero_without_rendering(self):
        result = self.bootstrap('workflow-transition', '--feature-id', 'FEAT-A', '--target', 'done')
        self.assertEqual(result.returncode, 1)
        self.assertIn('[FAIL] workflow', result.stderr)

    def test_spec_digest_matches_library(self):
        import approval
        result = self.bootstrap('spec-digest', 'specs/feat-a')
        self.assertEqual(result.stdout.strip(), approval.digest_from_spec_dir(self.root / 'specs/feat-a'))

    def test_failed_required_hook_exits_nonzero(self):
        self.write('hooks/run-hooks.sh', (ROOT / 'hooks/run-hooks.sh').read_text()).chmod(0o755)
        self.write('hooks/fail.sh', '#!/bin/bash\nexit 4\n').chmod(0o755)
        manifest = self.read_json('.agents/agentic.json')
        manifest['hooks'] = [{'event': 'on_spec_approved', 'script': 'hooks/fail.sh', 'on_failure': 'error',
                              'description': 'x'}]
        self.write_json('.agents/agentic.json', manifest)
        self.init_record()
        self.approve()
        result = self.bootstrap('workflow-transition', '--feature-id', 'FEAT-A', '--target', 'in_progress')
        self.assertEqual(result.returncode, 1)
        self.assertEqual(json.loads(result.stdout)['hook_failed'], True)


class ActivationSafetyTests(WorkflowTest):
    def test_example_policy_cannot_be_the_active_policy(self):
        (self.root / 'docs/team-policy/example.json').write_text((ROOT / 'docs/team-policy/example.json').read_text())
        manifest = self.read_json('.agents/agentic.json')
        manifest['team_policy'] = 'docs/team-policy/example.json'
        self.write_json('.agents/agentic.json', manifest)
        self.assert_rejected('not an active default', ops.check_repository, self.root)

    def test_policy_path_cannot_escape_repository(self):
        manifest = self.read_json('.agents/agentic.json')
        manifest['team_policy'] = '../elsewhere.json'
        self.write_json('.agents/agentic.json', manifest)
        self.assert_rejected('inside the repository', ops.check_repository, self.root)

    def test_active_policy_requires_reviewed_scenarios(self):
        manifest = self.read_json('.agents/agentic.json')
        del manifest['team_policy_scenarios']
        self.write_json('.agents/agentic.json', manifest)
        self.assert_rejected('reviewed team_policy_scenarios', ops.check_repository, self.root)

    def test_active_policy_rejects_unreviewed_scenarios(self):
        self.write_json(SCENARIO_PATH, team_policy.sanitize_scenarios(self.read_json(SCENARIO_PATH)))
        self.assert_rejected('cannot authorize', ops.check_repository, self.root)

    def test_removing_policy_while_records_exist_is_detected(self):
        self.ready()
        manifest = self.read_json('.agents/agentic.json')
        del manifest['team_policy']
        self.write_json('.agents/agentic.json', manifest)
        self.assert_rejected('require team_policy', ops.check_repository, self.root)
        self.assert_rejected('team_policy is not active', ops.mutate_transition, self.root, 'FEAT-A', 'blocked',
                             {'reason': 'x'})


class ScenarioReviewTests(WorkflowTest):
    """Real maintainer acceptance and synthetic forgeries are validated separately."""

    def scenarios(self):
        return self.read_json(SCENARIO_PATH)

    def test_real_maintainer_scenarios_match_their_decision_record(self):
        scenarios = json.loads((ROOT / SCENARIO_PATH).read_text())
        record = team_policy.verify_scenario_acceptance(ROOT, self.policy, scenarios)
        self.assertIn('not provider-authenticated', record['assurance'])
        self.assertEqual({s['human_review']['evidence_ref'] for s in scenarios},
                         {'progress/approval_M2-scenarios.json'})

    def test_synthetic_record_with_matching_digest_is_accepted_in_fixture_only(self):
        team_policy.verify_scenario_acceptance(self.root, self.policy, self.scenarios())

    def test_missing_review_rejected(self):
        scenarios = self.scenarios()
        scenarios[2]['human_review'] = None
        self.assert_rejected('cannot authorize', team_policy.verify_scenario_acceptance, self.root, self.policy, scenarios)

    def test_forged_evidence_reference_rejected(self):
        scenarios = self.scenarios()
        for scenario in scenarios:
            scenario['human_review']['evidence_ref'] = 'SYNTHETIC TEST FIXTURE, NOT REAL APPROVAL'
        self.assert_rejected('does not exist', team_policy.verify_scenario_acceptance, self.root, self.policy, scenarios)

    def test_changed_decision_after_acceptance_rejected(self):
        scenarios = self.scenarios()
        scenarios[0]['decision'] = 'Agents may approve anything.'
        self.assert_rejected('differ from the accepted', team_policy.verify_scenario_acceptance, self.root, self.policy,
                             scenarios)

    def test_agent_reviewer_rejected(self):
        scenarios = self.scenarios()
        scenarios[0]['human_review']['role'] = 'implementing-agent'
        self.assert_rejected('cannot authorize', team_policy.verify_scenario_acceptance, self.root, self.policy, scenarios)

    def test_record_from_another_project_rejected(self):
        record = self.read_json('progress/fixture-scenario-decision.json')
        record['feature_id'] = 'FEAT-010'
        self.write_json('progress/fixture-scenario-decision.json', record)
        self.assert_rejected('another project', team_policy.verify_scenario_acceptance, self.root, self.policy,
                             self.scenarios())

    def test_record_without_honest_assurance_rejected(self):
        record = self.read_json('progress/fixture-scenario-decision.json')
        record['assurance'] = 'authenticated'
        self.write_json('progress/fixture-scenario-decision.json', record)
        self.assert_rejected('assurance', team_policy.verify_scenario_acceptance, self.root, self.policy, self.scenarios())

    def test_decision_record_path_cannot_escape(self):
        scenarios = self.scenarios()
        for scenario in scenarios:
            scenario['human_review']['evidence_ref'] = '../../outside.json'
        self.assert_rejected('inside the repository', team_policy.verify_scenario_acceptance, self.root, self.policy,
                             scenarios)


class UnmanagedProjectTests(WorkflowTest):
    def build(self):
        super().build()
        self.write_json('.agents/agentic.json', {})

    def set_status(self, status):
        data = self.read_json('feature_list.json')
        data['features'][0]['status'] = status
        self.write_json('feature_list.json', data)

    def test_workflow_check_skips_without_opt_in(self):
        self.assertIn('[SKIP]', ops.check_repository(self.root))

    def test_transition_is_labeled_structural(self):
        result = ops.mutate_transition(self.root, 'FEAT-A', 'in_progress')
        self.assertEqual(result['assurance'], 'no-team-policy-structural-gates-only')
        self.assertEqual(self.read_json('feature_list.json')['features'][0]['status'], 'in_progress')

    def test_unmanaged_completion_still_requires_finished_tasks(self):
        self.set_status('in_progress')
        self.assert_rejected('unfinished required tasks', ops.mutate_transition, self.root, 'FEAT-A', 'done')

    def test_unmanaged_completion_requires_spec_artifacts(self):
        self.set_status('in_progress')
        (self.root / 'specs/feat-a/design.md').unlink()
        self.assert_rejected('missing spec artifact', ops.mutate_transition, self.root, 'FEAT-A', 'done')

    def test_unmanaged_completion_with_finished_tasks(self):
        self.set_status('in_progress')
        self.finish_tasks()
        self.assertEqual(ops.mutate_transition(self.root, 'FEAT-A', 'done')['status'], 'done')

    def test_unmanaged_blocking_cannot_skip_the_spec_gate(self):
        ops.mutate_transition(self.root, 'FEAT-B', 'blocked', {'reason': 'waiting'})
        feature = self.read_json('feature_list.json')['features'][1]
        self.assertEqual(feature['blocked_from'], 'pending')
        self.assert_rejected('previous status', ops.mutate_transition, self.root, 'FEAT-B', 'in_progress')
        ops.mutate_transition(self.root, 'FEAT-B', 'pending')
        self.assertNotIn('blocked_from', self.read_json('feature_list.json')['features'][1])

    def test_unmanaged_hand_blocked_feature_reenters_before_the_gates(self):
        data = self.read_json('feature_list.json')
        data['features'][1]['status'] = 'blocked'
        self.write_json('feature_list.json', data)
        self.assert_rejected('no recorded origin', ops.mutate_transition, self.root, 'FEAT-B', 'in_progress')
        self.assertEqual(ops.mutate_transition(self.root, 'FEAT-B', 'spec_ready')['status'], 'spec_ready')

    def start(self):
        ops.mutate_transition(self.root, 'FEAT-A', 'in_progress')
        return self.read_json('feature_list.json')['features'][0]['spec_approval']

    def test_unmanaged_start_binds_the_spec_and_edits_are_caught(self):
        approval = self.start()
        self.assertEqual(approval['assurance'], 'recorded-at-transition-not-a-human-decision')
        self.assertIn('1 in-progress approved spec(s) unchanged', ops.check_repository(self.root))
        self.finish_tasks()
        self.assertIn('[SKIP]', ops.check_repository(self.root))
        self.write('specs/feat-a/requirements.md', '### R1\nWeakened.\n')
        self.assert_rejected('requirements/design changed', ops.check_repository, self.root)
        self.assert_rejected('requirements/design changed', ops.mutate_transition, self.root, 'FEAT-A', 'done')

    def test_unmanaged_task_text_change_is_caught_but_checkboxes_are_free(self):
        self.start()
        path = self.root / 'specs/feat-a/tasks.md'
        path.write_text(path.read_text().replace('- [ ] **T2** — Test it _(R2)_\n', ''))
        self.assert_rejected('tasks.md changed beyond completion markers', ops.check_repository, self.root)

    def test_unmanaged_reapproval_rebinds_the_changed_spec(self):
        self.start()
        self.write('specs/feat-a/design.md', '# Design, revised with the human\n')
        self.assert_rejected('re-approve', ops.check_repository, self.root)
        self.assert_rejected('declared reviewer', ops.record_approval, self.root, 'FEAT-A', '', None, 'ref')
        result = ops.record_approval(self.root, 'FEAT-A', 'Dana Reviewer', None, 'chat 2026-11-11')
        self.assertEqual(result['assurance'], 'declared-unmanaged-no-roles')
        self.assertIn('1 in-progress approved spec(s) unchanged', ops.check_repository(self.root))
        approval = self.read_json('feature_list.json')['features'][0]['spec_approval']
        self.assertEqual(approval['reviewer'], 'Dana Reviewer')

    def test_unmanaged_explicit_approval_before_start_is_verified_at_start(self):
        ops.record_approval(self.root, 'FEAT-A', 'Dana Reviewer', None, 'ref')
        self.write('specs/feat-a/design.md', '# changed after approval\n')
        self.assert_rejected('requirements/design changed', ops.mutate_transition, self.root, 'FEAT-A', 'in_progress')

    def test_unmanaged_feature_without_a_recorded_approval_keeps_working(self):
        self.set_status('in_progress')
        self.write('specs/feat-a/design.md', '# legacy project, never bound\n')
        self.assertIn('0 in-progress approved spec(s) unchanged', ops.check_repository(self.root))
        result = self.bootstrap('workflow-validate', '--feature-id', 'FEAT-A', '--target', 'in_progress')
        self.assertIn('"spec_approval": "not-recorded"', result.stdout)

    def test_unmanaged_illegal_transition_rejected(self):
        self.assert_rejected('illegal SDD transition', ops.mutate_transition, self.root, 'FEAT-A', 'done')

    def test_unmanaged_concurrency_enforced(self):
        self.set_status('in_progress')
        data = self.read_json('feature_list.json')
        data['features'][1]['status'] = 'spec_ready'
        self.write_json('feature_list.json', data)
        self.assert_rejected('maxConcurrent', ops.mutate_transition, self.root, 'FEAT-B', 'in_progress')

    def test_record_operations_refused_without_policy(self):
        self.assert_rejected('requires an active team_policy', self.init_record)

    def test_stray_work_record_fails_check(self):
        self.write_json('progress/work/feat-a.json', {'format_version': 1})
        self.assert_rejected('require team_policy', ops.check_repository, self.root)

    def test_non_sdd_feature_without_spec_can_progress(self):
        data = self.read_json('feature_list.json')
        data['features'].append(self.feature('FIX-1', 'fix-1', 'pending', sdd=False))
        self.write_json('feature_list.json', data)
        self.set_status('pending')
        self.assertEqual(ops.mutate_transition(self.root, 'FIX-1', 'in_progress')['status'], 'in_progress')
        self.assertEqual(ops.mutate_transition(self.root, 'FIX-1', 'done')['status'], 'done')

    def test_validator_rejects_record_without_policy(self):
        feature = {'id': 'FEAT-A', 'name': 'feat-a', 'status': 'spec_ready', 'sdd': True}
        self.assert_rejected('require an active', workflow.validate_transition, feature, 'in_progress',
                             {'format_version': 1}, [], None, {'root': self.root})


class ExportedConsumerTests(WorkflowTest):
    def exported(self):
        dest = self.root.parent / ('consumer-' + uuid.uuid4().hex)
        result = subprocess.run([str(BOOTSTRAP), 'export', str(dest)], env=clean_env(), cwd=str(ROOT), text=True,
                                capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.addCleanup(shutil.rmtree, str(dest), True)
        return dest

    def test_export_has_no_active_policy_or_maintainer_acceptance(self):
        dest = self.exported()
        manifest = json.loads((dest / '.agents/agentic.json').read_text())
        self.assertNotIn('team_policy', manifest)
        self.assertNotIn('team_policy_scenarios', manifest)
        scenarios = json.loads((dest / SCENARIO_PATH).read_text())
        self.assertEqual(len(scenarios), 6)
        self.assertTrue(all(item['human_review'] is None for item in scenarios))
        self.assertFalse((dest / 'progress/approval_M2-scenarios.json').exists())
        self.assertFalse((dest / 'progress/approval_FEAT-010.json').exists())
        self.assertFalse((dest / 'progress/work').exists())
        self.assertFalse((dest / 'specs/hybrid-team-stable-release').exists())

    def test_exported_consumer_skips_strict_workflow(self):
        dest = self.exported()
        self.assertIn('[SKIP]', ops.check_repository(dest))

    def test_exported_workflow_cli_dispatches(self):
        dest = self.exported()
        result = self.bootstrap('workflow-check', root=dest)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((dest / '.agents/schemas/work-record.json').is_file())

    def test_copying_maintainer_scenarios_into_consumer_does_not_activate(self):
        dest = self.exported()
        shutil.copy(str(ROOT / SCENARIO_PATH), str(dest / SCENARIO_PATH))
        policy = json.loads((dest / 'docs/team-policy/example.json').read_text())
        scenarios = json.loads((dest / SCENARIO_PATH).read_text())
        self.assert_rejected('does not exist', team_policy.verify_scenario_acceptance, dest, policy, scenarios)
        shutil.copy(str(ROOT / 'progress/approval_M2-scenarios.json'), str(dest / 'progress/'))
        self.assert_rejected('another project', team_policy.verify_scenario_acceptance, dest, policy, scenarios)


class GatewayIntegrationTests(unittest.TestCase):
    def test_check_script_runs_workflow_gate_and_new_suites(self):
        text = (ROOT / 'check.sh').read_text(encoding='utf-8')
        self.assertIn('workflow_cli.py', text)
        self.assertIn('test_m3', text)

    def test_feature_list_failure_is_no_longer_masked(self):
        text = (ROOT / 'check.sh').read_text(encoding='utf-8')
        self.assertNotIn("<<'PYEOF' 2>/dev/null || true", text)


if __name__ == '__main__':
    unittest.main()
