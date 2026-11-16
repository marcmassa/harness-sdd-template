"""R11/R17 regressions from the M3 review: symlink escapes, malformed state, races, hooks."""
import json
import os
from pathlib import Path
import shutil
import tempfile
import threading
import time
from unittest import mock

from workflow_support import ROOT, WorkflowTest, ops
import safe_fs
import workflow_ops
import workflow_store


class OutsideDirectory(WorkflowTest):
    def outside(self):
        directory = tempfile.TemporaryDirectory(prefix='harness-outside-')
        self.addCleanup(directory.cleanup)
        return Path(directory.name)

    def redirect(self, relative):
        """Replace a state directory with a symlink to an external copy of it."""
        outside = self.outside()
        source = self.root / relative
        if source.exists():
            shutil.copytree(str(source), str(outside / 'copy'))
            shutil.rmtree(str(source))
        else:
            (outside / 'copy').mkdir()
        source.parent.mkdir(parents=True, exist_ok=True)
        os.symlink(str(outside / 'copy'), str(source))
        return outside / 'copy'


class SymlinkEscapeTests(OutsideDirectory):
    def test_codex_probe_rollback_through_symlinked_work_directory_refused(self):
        self.init_record()
        self.approve()
        record_text = (self.root / 'progress/work/feat-a.json').read_text()
        external = self.redirect('progress/work')
        after = json.dumps(dict(json.loads(record_text), status='in_progress'), indent=2) + '\n'
        (external / 'feat-a.json').write_text(after)
        (external / '.transition-journal.json').write_text(json.dumps({
            'format_version': 1, 'feature_id': 'FEAT-A', 'target': 'in_progress',
            'files': [{'path': 'progress/work/feat-a.json', 'before': record_text, 'after': after}]}))
        self.assert_rejected('symlink', ops.rollback_mutation, self.root, 'maintainer', 'ref')
        self.assertEqual((external / 'feat-a.json').read_text(), after)
        self.assertTrue((external / '.transition-journal.json').exists())

    def test_record_writes_never_follow_a_symlinked_work_directory(self):
        external = self.redirect('progress/work')
        self.assert_rejected('symlink', self.init_record)
        self.assertEqual(list(external.iterdir()), [])

    def test_symlinked_progress_parent_refused_for_reads_writes_and_check(self):
        self.init_record()
        external = self.redirect('progress')
        before = (external / 'work/feat-a.json').read_text()
        self.assert_rejected('symlink', self.approve)
        self.assert_rejected('symlink', ops.check_repository, self.root)
        self.assert_rejected('symlink', ops.mutate_transition, self.root, 'FEAT-A', 'blocked', {'reason': 'x'})
        self.assertEqual((external / 'work/feat-a.json').read_text(), before)

    def test_symlinked_record_file_refused_by_check_listing(self):
        self.init_record()
        path = self.root / 'progress/work/feat-a.json'
        target = self.root / 'progress/real.json'
        path.rename(target)
        os.symlink('../real.json', str(path))
        self.assert_rejected('regular file|symlink', ops.check_repository, self.root)
        self.assert_rejected('symlink', ops.mutate_transition, self.root, 'FEAT-A', 'blocked', {'reason': 'x'})

    def test_symlinked_feature_list_refused(self):
        (self.root / 'feature_list.json').rename(self.root / 'features.json')
        os.symlink('features.json', str(self.root / 'feature_list.json'))
        self.assert_rejected('symlink', ops.check_repository, self.root)
        self.assert_rejected('symlink', self.init_record)


class MalformedStateTests(WorkflowTest):
    def test_malformed_journals_refused_without_writing(self):
        self.init_record()
        self.approve()
        before = self.snapshot()
        valid_record = (self.root / 'progress/work/feat-a.json').read_text()
        journals = ('[]', '{not json', json.dumps({'format_version': 1, 'files': []}),
                    json.dumps({'format_version': 1, 'feature_id': 'FEAT-A', 'files': [
                        {'path': 'feature_list.json', 'before': '{}', 'after': '{}'},
                        {'path': 'feature_list.json', 'before': '{}', 'after': '{}'}]}),
                    json.dumps({'format_version': 1, 'feature_id': 'FEAT-A', 'files': [
                        {'path': 'progress/work/feat-a.json', 'before': '[1]', 'after': valid_record}]}),
                    json.dumps({'format_version': 2, 'feature_id': 'FEAT-A', 'files': [{}]}))
        for text in journals:
            with self.subTest(text[:40]):
                workflow_store.journal_path(self.root).write_text(text)
                with self.assertRaises(ValueError):
                    ops.rollback_mutation(self.root, 'maintainer', 'ref')
                self.assertEqual(self.snapshot(), before)

    def test_malformed_records_fail_as_diagnostics_not_crashes(self):
        self.init_record()
        bad = ({'pending_hook': 'oops'}, {'evidence': ['x']}, {'approval': 'yes'},
               {'lightweight': []}, {'checks': {}}, {'scope_changes': 'none'})
        for change in bad:
            with self.subTest(change):
                record = self.copy_record(**change)
                self.save_record(record)
                with self.assertRaisesRegex(ValueError, 'work record'):
                    ops.check_repository(self.root)
                result = self.bootstrap('workflow-check')
                self.assertEqual(result.returncode, 1)
                self.assertIn('[FAIL] workflow', result.stderr)
        for text in ('[]', '{', '"x"'):
            (self.root / 'progress/work/feat-a.json').write_text(text)
            with self.subTest(text), self.assertRaises(ValueError):
                ops.mutate_transition(self.root, 'FEAT-A', 'blocked', {'reason': 'x'})

    def test_malformed_feature_list_is_a_diagnostic(self):
        for text in ('[]', '{"features": {}}', '{"features": [1]}'):
            (self.root / 'feature_list.json').write_text(text)
            with self.subTest(text), self.assertRaisesRegex(ValueError, 'feature_list'):
                ops.check_repository(self.root)

    def test_missing_feature_list_fails_under_active_policy(self):
        (self.root / 'feature_list.json').unlink()
        self.assert_rejected('missing while team_policy is active', ops.check_repository, self.root)

    def test_missing_feature_list_without_policy_skips(self):
        (self.root / 'feature_list.json').unlink()
        self.write_json('.agents/agentic.json', {})
        self.assertIn('[SKIP]', ops.check_repository(self.root))

    def test_check_script_runs_workflow_check_even_without_feature_list(self):
        text = (ROOT / 'check.sh').read_text()
        workflow_call = text.index('workflow_cli.py" --root "$ROOT_DIR" check')
        feature_block_end = text.index('fi', text.index('if [ -f "feature_list.json" ]; then'))
        self.assertGreater(workflow_call, text.index('feature_list.json not found'))
        self.assertGreater(workflow_call, feature_block_end)


class StaleSnapshotTests(WorkflowTest):
    def test_codex_probe_commit_with_stale_before_snapshot_refused(self):
        self.init_record()
        relative = 'progress/work/feat-a.json'
        stale = (self.root / relative).read_text()
        newer = self.copy_record(owner='newer-owner')
        self.save_record(newer)
        newer_text = (self.root / relative).read_text()
        with self.assertRaisesRegex(safe_fs.StateConflict, 'changed after validation'):
            workflow_store.commit_transition(self.root, 'FEAT-A', 'blocked', [(relative, stale, '{}\n')])
        self.assertEqual((self.root / relative).read_text(), newer_text)
        self.assertFalse(workflow_store.journal_path(self.root).exists())

    def test_edit_during_validation_is_not_overwritten(self):
        self.init_record()
        self.approve()
        real = workflow_ops.validate_transition

        def racing(*args, **kwargs):
            result = real(*args, **kwargs)
            self.save_record(self.copy_record(owner='concurrent-editor'))
            return result
        with mock.patch.object(workflow_ops, 'validate_transition', racing):
            self.assert_rejected('changed after validation', ops.mutate_transition, self.root, 'FEAT-A', 'in_progress')
        self.assertEqual(self.record()['owner'], 'concurrent-editor')
        self.assertEqual(self.read_json('feature_list.json')['features'][0]['status'], 'spec_ready')

    def test_record_update_detects_a_concurrent_hand_edit(self):
        self.init_record()
        import workflow_io
        real = workflow_io.read_record_text

        def read_then_edit(root_path, feature):
            value = real(root_path, feature)
            self.save_record(self.copy_record(owner='hand-edit'))
            return value
        with mock.patch.object(workflow_io, 'read_record_text', read_then_edit):
            self.assert_rejected('changed since it was read', self.approve)
        self.assertEqual(self.record()['owner'], 'hand-edit')
        self.assertIsNone(self.record()['approval'])


class ConcurrentCommandTests(WorkflowTest):
    def slow(self, module, name, delay=0.4):
        real = getattr(module, name)

        def wrapper(*args, **kwargs):
            value = real(*args, **kwargs)
            time.sleep(delay)
            return value
        return mock.patch.object(module, name, wrapper)

    def run_threads(self, *functions):
        outcomes = [None] * len(functions)

        def runner(index, function):
            try:
                outcomes[index] = ('ok', function())
            except Exception as error:  # noqa: BLE001  (collected for assertions)
                outcomes[index] = ('error', str(error))
        threads = [threading.Thread(target=runner, args=(index, function))
                   for index, function in enumerate(functions)]
        for thread in threads:
            thread.start()
            time.sleep(0.05)
        for thread in threads:
            thread.join(30)
        return outcomes

    def test_max_concurrent_race_admits_exactly_one_feature(self):
        self.init_record()
        self.approve()
        ops.create_record(self.root, 'FEAT-B', 'agent-b', 'feat/b', None)
        ops.mutate_transition(self.root, 'FEAT-B', 'spec_ready')
        self.approve('FEAT-B')
        with self.slow(workflow_ops, 'validate_transition'):
            outcomes = self.run_threads(lambda: ops.mutate_transition(self.root, 'FEAT-A', 'in_progress'),
                                        lambda: ops.mutate_transition(self.root, 'FEAT-B', 'in_progress'))
        self.assertEqual(sorted(kind for kind, _ in outcomes), ['error', 'ok'], outcomes)
        self.assertIn('maxConcurrent', [detail for kind, detail in outcomes if kind == 'error'][0])
        statuses = [item['status'] for item in self.read_json('feature_list.json')['features']]
        self.assertEqual(statuses.count('in_progress'), 1)
        self.assertIn('[PASS]', ops.check_repository(self.root))

    def test_concurrent_evidence_and_review_writes_are_both_kept(self):
        self.ready()
        self.finish_tasks()
        self.commit('candidate')
        import workflow_updates
        item = {'requirement_id': 'R1', 'kind': 'automated', 'source': 'tests/test_sample.py::Sample::test_one',
                'result': 'passed', 'check_command': 'python3 -m unittest'}
        with self.slow(workflow_updates, 'validate_evidence_item'):
            outcomes = self.run_threads(
                lambda: ops.add_evidence(self.root, 'FEAT-A', item),
                lambda: ops.record_review(self.root, 'FEAT-A', 'Dana Reviewer', 'human-reviewer', 'approved', 'r'))
        self.assertEqual([kind for kind, _ in outcomes], ['ok', 'ok'], outcomes)
        record = self.record()
        self.assertEqual(len(record['evidence']), 1)
        self.assertEqual(record['closing_review']['decision'], 'approved')

    def test_review_recorded_while_check_sh_runs_is_not_lost(self):
        self.ready()
        lib = ROOT / '.agents/lib'
        self.write('check.sh', '#!/bin/sh\npython3 -c "import sys; sys.path.insert(0, \'{}\'); '
                   'import workflow_ops as o; o.record_review(\'{}\', \'FEAT-A\', \'Dana\', \'human-reviewer\', '
                   '\'approved\', \'during-checks\')"\n'.format(lib, self.root)).chmod(0o755)
        self.commit('checks that write')
        self.assertEqual(ops.run_checks(self.root, 'FEAT-A')['check'], 'passed')
        record = self.record()
        self.assertEqual(record['closing_review']['evidence_ref'], 'during-checks')
        self.assertEqual(record['checks'][0]['result'], 'passed')

    def test_lock_waits_then_fails_with_a_diagnostic(self):
        acquired, release = threading.Event(), threading.Event()

        def holder():
            with safe_fs.workflow_lock(self.root):
                acquired.set()
                release.wait(10)
        thread = threading.Thread(target=holder)
        thread.start()
        acquired.wait(5)
        try:
            with self.assertRaisesRegex(ValueError, 'holds'):
                with safe_fs.workflow_lock(self.root, timeout=0.2):
                    pass
        finally:
            release.set()
            thread.join(10)
        with safe_fs.workflow_lock(self.root, timeout=1):
            pass


class HookOutcomeTests(WorkflowTest):
    def install(self, event, script, on_failure='error'):
        self.write('hooks/run-hooks.sh', (ROOT / 'hooks/run-hooks.sh').read_text()).chmod(0o755)
        self.write('hooks/fixture.sh', '#!/bin/bash\n' + script).chmod(0o755)
        manifest = self.read_json('.agents/agentic.json')
        manifest['hooks'] = [{'event': event, 'script': 'hooks/fixture.sh', 'on_failure': on_failure,
                              'description': 'fixture'}]
        self.write_json('.agents/agentic.json', manifest)

    def test_hook_edit_to_record_is_preserved(self):
        self.install('on_spec_approved', 'python3 - <<EOF\nimport json\np="$ROOT_DIR/progress/work/feat-a.json"\n'
                     'r=json.load(open(p)); r["hook_note"]="kept"\njson.dump(r, open(p, "w"))\nEOF\n')
        self.init_record()
        self.approve()
        self.assertFalse(ops.mutate_transition(self.root, 'FEAT-A', 'in_progress')['hook_failed'])
        record = self.record()
        self.assertEqual(record['hook_note'], 'kept')
        self.assertNotIn('pending_hook', record)

    def test_command_hook_failure_is_recorded_and_blocks_closure(self):
        self.install('on_review_start', 'exit 4\n')
        self.ready()
        result = self.bootstrap('workflow-run-hook', '--feature-id', 'FEAT-A', '--event', 'on_review_start')
        self.assertEqual(result.returncode, 1)
        self.assertEqual(self.record()['pending_hook']['event'], 'on_review_start')
        self.assert_rejected('explicit recovery', ops.check_repository, self.root)
        self.assert_rejected('explicit recovery', ops.mutate_transition, self.root, 'FEAT-A', 'done')
        ops.recover_hook(self.root, 'FEAT-A', 'on_review_start', 'maintainer', 'note')
        self.assertIn('[PASS]', ops.check_repository(self.root))

    def test_unsupported_command_hook_event_refused(self):
        self.ready()
        self.assert_rejected('unsupported', ops.run_lifecycle_hook, self.root, 'FEAT-A', 'on_feature_done')

    def test_unmanaged_required_hook_failure_is_persisted(self):
        self.write_json('.agents/agentic.json', {})
        self.install('on_spec_approved', 'exit 3\n')
        self.assertTrue(ops.mutate_transition(self.root, 'FEAT-A', 'in_progress')['hook_failed'])
        feature = self.read_json('feature_list.json')['features'][0]
        self.assertEqual((feature['status'], feature['pending_hook']['state']), ('in_progress', 'failed'))
        self.assert_rejected('explicit recovery', ops.check_repository, self.root)
        self.assert_rejected('explicit recovery', ops.mutate_transition, self.root, 'FEAT-A', 'done')
        self.assert_rejected('declared authorizer', ops.recover_hook, self.root, 'FEAT-A', 'on_spec_approved', '', 'x')
        result = ops.recover_hook(self.root, 'FEAT-A', 'on_spec_approved', 'Maintainer name', 'chat note')
        self.assertEqual(result['assurance'], 'declared-unmanaged-no-roles')
        self.assertIn('[SKIP]', ops.check_repository(self.root))


if __name__ == '__main__':
    import unittest
    unittest.main()
