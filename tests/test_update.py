"""Update plan, apply, and restore (T21): three-way rule, backups, interruption, containment."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.agents/lib'))

import inventory  # noqa: E402
import update  # noqa: E402

BASE = {'check.sh': '#!/bin/sh\necho v1\n', '.agents/lib/tool.py': 'VERSION = 1\n',
        '.agents/lib/old.py': 'gone in v2\n', 'docs/guide.md': 'guide v1\n',
        'feature_list.json': '{"features": []}\n', 'README.md': 'starter readme\n'}
NEXT = {'check.sh': '#!/bin/sh\necho v2\n', '.agents/lib/tool.py': 'VERSION = 2\n',
        '.agents/lib/new.py': 'added in v2\n', 'docs/guide.md': 'guide v1\n',
        'feature_list.json': '{"features": ["template"]}\n', 'README.md': 'new starter readme\n',
        'docs/extra.md': 'a new starter doc\n'}


class UpdateTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='harness-update-')
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name).resolve()
        self.project = self.tree('project', BASE)
        self.release = self.tree('release', NEXT)

    def tree(self, name, files):
        root = self.base / name
        for relative, content in files.items():
            path = root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content)
        inventory.create(root)
        return root

    def write(self, relative, content, root=None):
        path = (root or self.project) / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)

    def read(self, relative):
        return (self.project / relative).read_text()

    def plan(self):
        return update.plan_update(self.project, self.release)

    def actions(self):
        return {item['path']: item['action'] for item in self.plan()['actions']}

    def apply(self):
        return update.apply_update(self.project, self.release, self.plan()['plan_digest'])

    def snapshot(self):
        return {path.relative_to(self.project).as_posix(): path.read_bytes()
                for path in sorted(self.project.rglob('*'))
                if path.is_file() and '.harness/backups' not in path.as_posix()}

    def set_version(self, root, version):
        path = root / inventory.INVENTORY
        document = json.loads(path.read_text())
        document['framework_version'] = version
        path.write_text(json.dumps(document))


class PlanTests(UpdateTest):
    def test_plan_classifies_every_path_and_changes_nothing(self):
        self.write('notes/mine.md', 'not part of the framework\n')
        before = self.snapshot()
        self.assertEqual(self.actions(), {
            'check.sh': 'replace', '.agents/lib/tool.py': 'replace', '.agents/lib/old.py': 'remove',
            '.agents/lib/new.py': 'add', 'docs/guide.md': 'current', 'docs/extra.md': 'add',
            'feature_list.json': 'keep', 'README.md': 'keep'})
        self.assertEqual(self.snapshot(), before)
        self.assertFalse((self.project / '.harness/backups').exists())

    def test_local_changes_deletions_and_foreign_files_are_conflicts(self):
        self.write('check.sh', '#!/bin/sh\necho customized\n')
        (self.project / '.agents/lib/tool.py').unlink()
        self.write('.agents/lib/old.py', 'still used here\n')
        self.write('.agents/lib/new.py', 'the project already had a file here\n')
        reasons = {item['path']: item['reason'] for item in self.plan()['actions']
                   if item['action'] == 'conflict'}
        self.assertEqual(reasons, {
            'check.sh': 'changed locally', '.agents/lib/tool.py': 'deleted locally',
            '.agents/lib/old.py': 'no longer shipped, but changed locally',
            '.agents/lib/new.py': 'a file of the project occupies this path'})

    def test_plan_digest_is_stable_and_tracks_the_project(self):
        first = self.plan()['plan_digest']
        self.assertEqual(self.plan()['plan_digest'], first)
        self.write('check.sh', 'edited\n')
        self.assertNotEqual(self.plan()['plan_digest'], first)

    def test_downgrade_and_missing_inventory_are_refused(self):
        self.set_version(self.release, '0.8.0')
        with self.assertRaisesRegex(ValueError, 'refusing to downgrade'):
            self.plan()
        (self.project / inventory.INVENTORY).unlink()
        with self.assertRaisesRegex(ValueError, 'update-adopt'):
            self.plan()

    def test_traversal_in_an_inventory_is_refused(self):
        outside = self.base / 'outside.txt'
        outside.write_text('untouched')
        for root in (self.project, self.release):
            path = root / inventory.INVENTORY
            original = path.read_text()
            document = json.loads(original)
            document['files']['../outside.txt'] = {'sha256': 'a' * 64, 'ownership': 'framework'}
            path.write_text(json.dumps(document))
            with self.assertRaisesRegex(ValueError, 'plain relative path'):
                self.plan()
            path.write_text(original)
        self.assertEqual(outside.read_text(), 'untouched')


class ApplyTests(UpdateTest):
    def test_apply_updates_owned_files_and_preserves_everything_else(self):
        self.write('notes/mine.md', 'mine\n')
        self.write('.cursor/rules/user.mdc', 'foreign tool configuration\n')
        journal = self.apply()
        self.assertEqual(journal['state'], 'complete')
        self.assertEqual(self.read('check.sh'), NEXT['check.sh'])
        self.assertEqual(self.read('.agents/lib/new.py'), NEXT['.agents/lib/new.py'])
        self.assertFalse((self.project / '.agents/lib/old.py').exists())
        self.assertEqual(self.read('feature_list.json'), BASE['feature_list.json'])
        self.assertEqual(self.read('README.md'), BASE['README.md'])
        self.assertEqual(self.read('docs/extra.md'), NEXT['docs/extra.md'])
        self.assertEqual(self.read('notes/mine.md'), 'mine\n')
        self.assertEqual(self.read('.cursor/rules/user.mdc'), 'foreign tool configuration\n')
        self.assertTrue(all(action in ('current', 'keep') for action in self.actions().values()))
        self.assertNotIn('.agents/lib/old.py', inventory.load(self.project)['files'])

    def test_conflicts_are_left_alone_and_the_incoming_copy_is_saved(self):
        self.write('check.sh', '#!/bin/sh\necho customized\n')
        journal = self.apply()
        self.assertEqual([item['path'] for item in journal['conflicts']], ['check.sh'])
        self.assertEqual(self.read('check.sh'), '#!/bin/sh\necho customized\n')
        saved = self.project / '.harness/backups' / journal['id'] / 'incoming/check.sh'
        self.assertEqual(saved.read_text(), NEXT['check.sh'])
        self.assertEqual(inventory.load(self.project)['conflicts'], ['check.sh'])
        self.assertEqual(self.actions()['check.sh'], 'conflict')
        update.keep(self.project, ['check.sh'])
        self.assertEqual(self.actions()['check.sh'], 'keep')
        self.assertNotIn('conflicts', {k: v for k, v in inventory.load(self.project).items() if v})

    def test_apply_refuses_a_stale_or_unreviewed_plan(self):
        reviewed = self.plan()['plan_digest']
        self.write('check.sh', 'edited after review\n')
        before = self.snapshot()
        with self.assertRaisesRegex(ValueError, 'changed since the plan was reviewed'):
            update.apply_update(self.project, self.release, reviewed)
        with self.assertRaisesRegex(ValueError, 'changed since the plan was reviewed'):
            update.apply_update(self.project, self.release, 'f' * 64)
        self.assertEqual(self.snapshot(), before)

    def test_symlinks_are_never_followed(self):
        outside = self.base / 'outside.py'
        outside.write_text('external file\n')
        (self.project / '.agents/lib/tool.py').unlink()
        (self.project / '.agents/lib/tool.py').symlink_to(outside)
        (self.project / 'docs').rename(self.project / 'real-docs')
        (self.project / 'docs').symlink_to(self.base)
        actions = self.actions()
        self.assertEqual(actions['.agents/lib/tool.py'], 'conflict')
        self.assertEqual(actions['docs/extra.md'], 'conflict')
        self.apply()
        self.assertEqual(outside.read_text(), 'external file\n')
        self.assertFalse((self.base / 'extra.md').exists())
        self.assertTrue((self.project / '.agents/lib/tool.py').is_symlink())

    def test_symlinked_backup_directory_is_refused(self):
        (self.project / '.harness/backups').symlink_to(self.base)
        before = self.snapshot()
        with self.assertRaises(ValueError):
            self.apply()
        self.assertEqual(self.snapshot(), before)


class RestoreTests(UpdateTest):
    def test_restore_returns_the_project_to_its_previous_bytes(self):
        before = self.snapshot()
        self.apply()
        self.assertNotEqual(self.snapshot(), before)
        result = update.restore_update(self.project)
        self.assertEqual(result['files'], 5)
        self.assertEqual(self.snapshot(), before)
        self.assertEqual(self.actions()['check.sh'], 'replace')
        self.apply()
        self.assertEqual(self.read('check.sh'), NEXT['check.sh'])

    def test_restore_refuses_to_overwrite_edits_made_after_the_update(self):
        self.apply()
        self.write('check.sh', '#!/bin/sh\necho edited after update\n')
        with self.assertRaisesRegex(ValueError, 'check.sh'):
            update.restore_update(self.project)
        self.assertEqual(self.read('check.sh'), '#!/bin/sh\necho edited after update\n')
        self.assertEqual(self.read('.agents/lib/tool.py'), NEXT['.agents/lib/tool.py'])
        update.restore_update(self.project, overwrite_edits=True)
        self.assertEqual(self.read('check.sh'), BASE['check.sh'])

    def test_interrupted_update_is_detected_and_recoverable(self):
        before = self.snapshot()
        real, calls = update._mutate, []

        def crash_on_third(root, release, item):
            calls.append(item['path'])
            if len(calls) == 3:
                raise OSError('simulated crash')
            real(root, release, item)

        with mock.patch.object(update, '_mutate', crash_on_third):
            with self.assertRaises(OSError):
                self.apply()
        self.assertNotEqual(self.snapshot(), before)
        with self.assertRaisesRegex(ValueError, 'interrupted update'):
            self.plan()
        update.restore_update(self.project)
        self.assertEqual(self.snapshot(), before)
        self.assertEqual(self.apply()['state'], 'complete')

    def test_nothing_to_restore_is_reported(self):
        with self.assertRaisesRegex(ValueError, 'no update to restore'):
            update.restore_update(self.project)


class LegacyAndCommandTests(UpdateTest):
    def test_legacy_adoption_then_update_touches_only_matching_files(self):
        (self.project / inventory.INVENTORY).unlink()
        self.write('check.sh', '#!/bin/sh\necho heavily customized\n')
        old = self.tree('old-release', BASE)
        inventory.adopt(self.project, old)
        actions = self.actions()
        self.assertEqual(actions['check.sh'], 'conflict')
        self.assertEqual(actions['.agents/lib/tool.py'], 'replace')
        self.apply()
        self.assertEqual(self.read('check.sh'), '#!/bin/sh\necho heavily customized\n')
        self.assertEqual(self.read('.agents/lib/tool.py'), NEXT['.agents/lib/tool.py'])
        self.assertEqual(inventory.load(self.project)['framework_version'],
                         inventory.declared()['framework_version'])

    def test_bootstrap_commands_drive_a_real_export(self):
        consumer = self.base / 'consumer'
        env = {k: v for k, v in os.environ.items() if not k.startswith('GIT_') and k != 'ROOT_DIR'}

        def run(*args):
            return subprocess.run([str(ROOT / '.agents/bootstrap.sh')] + [str(a) for a in args],
                                  text=True, capture_output=True, env=env, cwd=str(ROOT))

        self.assertEqual(run('export', consumer).returncode, 0)
        (consumer / 'docs/quality-checks.md').write_text('local edit\n')
        planned = run('update-plan', consumer)
        self.assertEqual(planned.returncode, 0, planned.stderr)
        self.assertIn('conflict docs/quality-checks.md  (changed locally)', planned.stdout)
        digest = planned.stdout.strip().rsplit(' ', 1)[-1]
        self.assertEqual(run('update-apply', consumer).returncode, 1)
        applied = run('update-apply', consumer, '--plan', digest)
        self.assertEqual(applied.returncode, 0, applied.stderr)
        self.assertEqual(json.loads(applied.stdout)['conflicts'], ['docs/quality-checks.md'])
        self.assertEqual(run('update-restore', consumer).returncode, 0)
        self.assertEqual(run('update-plan', consumer / 'missing').returncode, 1)


if __name__ == '__main__':
    unittest.main()
