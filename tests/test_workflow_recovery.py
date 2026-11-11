"""R11, R17: journaled mutation recovery and explicit lifecycle hook handling."""
import json
from unittest import mock

from workflow_support import ROOT, WorkflowTest, ops
import workflow_store


class SimulatedCrash(BaseException):
    """Not an Exception, so in-process cleanup cannot run: models a killed process."""


class JournalTests(WorkflowTest):
    def crash_on_write(self, index):
        real = workflow_store.safe_fs.write_text
        calls = []

        def writer(root, relative, text):
            calls.append(relative)
            if len(calls) == index:
                raise SimulatedCrash()
            real(root, relative, text)
        return mock.patch.object(workflow_store.safe_fs, 'write_text', writer)

    def prepared(self):
        self.init_record()
        self.approve()
        return self.snapshot()

    def test_crash_between_files_is_detected_and_blocks_everything(self):
        self.prepared()
        with self.crash_on_write(2), self.assertRaises(SimulatedCrash):
            ops.mutate_transition(self.root, 'FEAT-A', 'in_progress')
        self.assertEqual(self.record()['status'], 'in_progress')
        self.assertEqual(self.read_json('feature_list.json')['features'][0]['status'], 'spec_ready')
        self.assert_rejected('incomplete workflow mutation', ops.check_repository, self.root)
        self.assert_rejected('incomplete workflow mutation', ops.mutate_transition, self.root, 'FEAT-A', 'blocked',
                             {'reason': 'x'})
        self.assert_rejected('incomplete workflow mutation', self.approve)

    def test_rollback_restores_consistent_state_and_transition_can_rerun(self):
        before = self.prepared()
        with self.crash_on_write(2), self.assertRaises(SimulatedCrash):
            ops.mutate_transition(self.root, 'FEAT-A', 'in_progress')
        result = ops.rollback_mutation(self.root, 'maintainer', 'incident-note')
        self.assertEqual(result['attempted_target'], 'in_progress')
        self.assertEqual(self.snapshot(), before)
        self.assertFalse(workflow_store.journal_path(self.root).exists())
        self.assertEqual(ops.mutate_transition(self.root, 'FEAT-A', 'in_progress')['status'], 'in_progress')

    def test_rollback_requires_human_authority(self):
        self.prepared()
        with self.crash_on_write(1), self.assertRaises(SimulatedCrash):
            ops.mutate_transition(self.root, 'FEAT-A', 'in_progress')
        self.assert_rejected('cannot authorize', ops.rollback_mutation, self.root, 'implementing-agent', 'ref')
        self.assert_rejected('evidence reference', ops.rollback_mutation, self.root, 'maintainer', '')

    def test_rollback_refuses_edits_made_after_crash(self):
        self.prepared()
        with self.crash_on_write(2), self.assertRaises(SimulatedCrash):
            ops.mutate_transition(self.root, 'FEAT-A', 'in_progress')
        record = self.record()
        record['owner'] = 'someone-else'
        self.save_record(record)
        self.assert_rejected('changed after', ops.rollback_mutation, self.root, 'maintainer', 'ref')

    def test_forged_journal_cannot_write_outside_workflow_state(self):
        self.prepared()
        target = self.write('notes.txt', 'original')
        workflow_store.journal_path(self.root).write_text(json.dumps({
            'format_version': 1, 'feature_id': 'FEAT-A', 'files': [{'path': '../notes.txt', 'before': 'x', 'after': 'y'},
                                           {'path': 'notes.txt', 'before': 'x', 'after': 'original'}]}))
        self.assert_rejected('outside workflow state', ops.rollback_mutation, self.root, 'maintainer', 'ref')
        self.assertEqual(target.read_text(), 'original')

    def test_ordinary_write_failure_rolls_back_and_clears_journal(self):
        before = self.prepared()
        real = workflow_store.safe_fs.write_text
        calls = []

        def failing(root, relative, text):
            calls.append(relative)
            if len(calls) == 2:
                raise OSError('disk full')
            real(root, relative, text)
        with mock.patch.object(workflow_store.safe_fs, 'write_text', failing), self.assertRaises(OSError):
            ops.mutate_transition(self.root, 'FEAT-A', 'in_progress')
        self.assertEqual(self.snapshot(), before)
        self.assertFalse(workflow_store.journal_path(self.root).exists())

    def test_rollback_without_journal_reports_nothing_to_do(self):
        self.prepared()
        self.assert_rejected('no incomplete', ops.rollback_mutation, self.root, 'maintainer', 'ref')


class HookTests(WorkflowTest):
    def install_hook(self, event, exit_code, on_failure='error'):
        self.write('hooks/run-hooks.sh', (ROOT / 'hooks/run-hooks.sh').read_text()).chmod(0o755)
        script = self.write('hooks/fixture.sh',
                            '#!/bin/bash\necho run >> "$ROOT_DIR/hook-runs.log"\nexit {}\n'.format(exit_code))
        script.chmod(0o755)
        manifest = self.read_json('.agents/agentic.json')
        manifest['hooks'] = [{'event': event, 'script': 'hooks/fixture.sh', 'on_failure': on_failure,
                              'description': 'fixture'}]
        self.write_json('.agents/agentic.json', manifest)
        self.write('.gitignore', 'hook-runs.log\n')

    def hook_runs(self):
        log = self.root / 'hook-runs.log'
        return len(log.read_text().splitlines()) if log.exists() else 0

    def failed_at_implementation(self):
        self.install_hook('on_spec_approved', 3)
        self.init_record()
        self.approve()
        result = ops.mutate_transition(self.root, 'FEAT-A', 'in_progress')
        self.assertTrue(result['hook_failed'])
        return result

    def test_hook_runs_after_transition_and_clears_pending(self):
        self.install_hook('on_spec_approved', 0)
        self.init_record()
        self.approve()
        self.assertFalse(ops.mutate_transition(self.root, 'FEAT-A', 'in_progress')['hook_failed'])
        self.assertEqual(self.hook_runs(), 1)
        self.assertNotIn('pending_hook', self.record())

    def test_failed_required_hook_keeps_state_and_records_incomplete_event(self):
        self.failed_at_implementation()
        record = self.record()
        self.assertEqual(record['status'], 'in_progress')
        self.assertEqual(record['pending_hook']['state'], 'failed')
        self.assertEqual(record['pending_hook']['event'], 'on_spec_approved')

    def test_pending_hook_blocks_implementation_gate_and_closure(self):
        self.failed_at_implementation()
        self.assert_rejected('requires explicit recovery', ops.check_repository, self.root)
        result = self.bootstrap('workflow-validate', '--feature-id', 'FEAT-A', '--target', 'in_progress')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('explicit recovery', result.stderr)
        self.assert_rejected('explicit recovery', ops.mutate_transition, self.root, 'FEAT-A', 'done')

    def test_pending_hook_still_allows_moving_to_blocked(self):
        self.failed_at_implementation()
        ops.mutate_transition(self.root, 'FEAT-A', 'blocked', {'reason': 'hook owner unavailable'})
        self.assertIn('pending_hook', self.record())

    def test_recovery_needs_human_authority_and_matching_event(self):
        self.failed_at_implementation()
        self.assert_rejected('cannot authorize', ops.recover_hook, self.root, 'FEAT-A', 'on_spec_approved',
                             'implementing-agent', 'ref')
        self.assert_rejected('evidence reference', ops.recover_hook, self.root, 'FEAT-A', 'on_spec_approved',
                             'maintainer', '')
        self.assert_rejected('not pending', ops.recover_hook, self.root, 'FEAT-A', 'on_feature_done',
                             'maintainer', 'ref')

    def test_recovery_records_decision_without_rerunning_side_effects(self):
        self.failed_at_implementation()
        self.assertEqual(self.hook_runs(), 1)
        result = ops.recover_hook(self.root, 'FEAT-A', 'on_spec_approved', 'maintainer', 'ops-note')
        self.assertEqual(result['side_effects'], 'not-rerun')
        self.assertEqual(self.hook_runs(), 1)
        record = self.record()
        self.assertNotIn('pending_hook', record)
        self.assertEqual(record['hook_recoveries'][0]['authorized_by'], 'maintainer')
        self.assertIn('[PASS]', ops.check_repository(self.root))

    def test_hook_crash_leaves_a_blocking_pending_event(self):
        self.install_hook('on_spec_approved', 0)
        self.init_record()
        self.approve()
        with mock.patch.object(ops, '_run_hooks', side_effect=SimulatedCrash()), self.assertRaises(SimulatedCrash):
            ops.mutate_transition(self.root, 'FEAT-A', 'in_progress')
        self.assertEqual(self.record()['pending_hook']['state'], 'started')
        self.assert_rejected('explicit recovery', ops.check_repository, self.root)

    def test_warn_hook_failure_is_recorded_without_blocking(self):
        self.install_hook('on_spec_approved', 1, on_failure='warn')
        self.init_record()
        self.approve()
        result = ops.mutate_transition(self.root, 'FEAT-A', 'in_progress')
        self.assertFalse(result['hook_failed'])
        self.assertEqual(result['hook_warning'], 'on_spec_approved')
        record = self.record()
        self.assertNotIn('pending_hook', record)
        self.assertEqual(len(record['hook_warnings']), 1)

    def test_missing_hook_runner_counts_as_failure(self):
        self.install_hook('on_spec_approved', 0)
        (self.root / 'hooks/run-hooks.sh').unlink()
        self.init_record()
        self.approve()
        self.assertTrue(ops.mutate_transition(self.root, 'FEAT-A', 'in_progress')['hook_failed'])
        self.assertIn('pending_hook', self.record())


if __name__ == '__main__':
    import unittest
    unittest.main()
