"""End-to-end distribution exercise (T24): legacy upgrade, clean install, five entry
points, rollback, and removal, each against real exported projects."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.agents/lib'))

import capabilities  # noqa: E402
import inventory  # noqa: E402

# The last release published before inventories existed (FEAT-008, 2026-10).
LEGACY_RELEASE = 'e286f4b800165d0cc29b43907ac3ce428273e417'
NATIVE_BINARIES = {'opencode': 'opencode', 'gemini-cli': 'gemini', 'claude-code': 'claude',
                   'cursor': 'cursor-agent', 'codex': 'codex'}
ROLE = {'name': 'fixture-engineer', 'mode': 'primary', 'default': True,
        'description': 'Maintains the fixture application and its verification.',
        'role_file': '.agents/subagents/fixture-engineer/SUBAGENT.md',
        'soul': '.agents/subagents/fixture-engineer/SOUL.md',
        'permission': {'edit': {'specs/**': 'deny', '*': 'ask'}}}


def clean_env():
    return {key: value for key, value in os.environ.items()
            if not key.startswith('GIT_') and key != 'ROOT_DIR'}


class ExportedProject(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='harness-e2e-')
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name).resolve()
        self.project = self.base / 'project'

    def run_tool(self, *args, cwd=None, ok=True):
        result = subprocess.run([str(arg) for arg in args], cwd=str(cwd or self.project),
                                env=clean_env(), text=True, capture_output=True)
        if ok:
            self.assertEqual(result.returncode, 0, '{}\n{}{}'.format(args, result.stdout, result.stderr))
        return result

    def source(self, *args, ok=True):
        """Run the framework source's bootstrap, as a maintainer updating a project would."""
        return self.run_tool(ROOT / '.agents/bootstrap.sh', *args, cwd=ROOT, ok=ok)

    def local(self, *args, ok=True):
        return self.run_tool(self.project / '.agents/bootstrap.sh', *args, ok=ok)

    def snapshot(self):
        return {path.relative_to(self.project).as_posix(): path.read_bytes()
                for path in sorted(self.project.rglob('*')) if path.is_file()
                and '.harness/backups' not in path.as_posix() and '__pycache__' not in path.parts}

    def plan_digest(self, operation):
        output = self.source(operation, self.project).stdout
        return output, output.strip().rsplit(' ', 1)[-1]

    def shape(self):
        """What /init does: one project role, the CLIs in use, scaffolds dropped."""
        path = self.project / '.agents/agentic.json'
        manifest = json.loads(path.read_text())
        manifest['subagents'] = [ROLE]
        manifest['default_agent'] = ROLE['name']
        manifest['target_clis'] = list(NATIVE_BINARIES)
        role = self.project / '.agents/subagents/fixture-engineer'
        role.mkdir(parents=True)
        (role / 'SUBAGENT.md').write_text('# Fixture engineer\nMaintains the fixture.\n')
        (role / 'SOUL.md').write_text(
            '## Identity\nCareful.\n\n## Decision Principles\n1. Evidence.\n\n'
            '## Boundaries\n- Never edits specs.\n\n## Tone & Style\n- Plain.\n')
        path.write_text(json.dumps(manifest, indent=2) + '\n')
        self.local('remove-examples', '--yes')

    def assert_five_entry_points(self):
        data = capabilities.load()
        commands = [item['name'] for item in json.loads(
            (self.project / '.agents/agentic.json').read_text())['commands']]
        for name, adapter in data['adapters'].items():
            self.local(name)
            for pattern in adapter['generates']:
                targets = [pattern] if '<name>' not in pattern else (
                    [pattern.replace('<name>', ROLE['name'])] if '/agents/' in pattern
                    else [pattern.replace('<name>', command) for command in commands])
                for target in targets:
                    self.assertTrue((self.project / target).is_file(), '{}: {}'.format(name, target))
        self.assertTrue((self.project / 'AGENTS.md').is_file())  # codex entry point
        self.local('--check')


class CleanInstallTests(ExportedProject):
    def test_install_render_check_remove_and_restore(self):
        self.source('export', self.project)
        self.assertEqual(self.local('version').stdout.count('0 modified, 0 missing'), 1)
        self.shape()
        self.local('init', '--validate')
        self.assert_five_entry_points()
        self.run_tool(self.project / 'check.sh', '--no-color')
        quiet = self.run_tool(self.project / 'check.sh', '--quiet').stdout
        self.assertIn('check.sh: PASS', quiet)
        self.local('clean', '--all')
        self.assertFalse((self.project / 'opencode.json').exists())

        # Removal by inventory: only unchanged framework files go.
        (self.project / 'docs/quality-checks.md').write_text('adapted to this project\n')
        (self.project / 'src').mkdir()
        (self.project / 'src/app.py').write_text('print("mine")\n')
        before = self.snapshot()
        listing, digest = self.plan_digest('update-remove')
        self.assertIn('keep     docs/quality-checks.md  (changed locally)', listing)
        self.assertEqual(self.snapshot(), before)  # the plan changes nothing
        result = json.loads(self.source('update-remove', self.project, '--plan', digest).stdout)
        self.assertGreater(result['removed'], 50)
        self.assertIn('docs/quality-checks.md', [item['path'] for item in result['kept']])
        for kept in ('feature_list.json', '.agents/agentic.json', 'DESIGN.md', 'progress/current.md',
                     'docs/quality-checks.md', 'src/app.py',
                     '.agents/subagents/fixture-engineer/SUBAGENT.md'):
            self.assertTrue((self.project / kept).is_file(), kept)
        for gone in ('.agents/lib/workflow.py', '.agents/bootstrap.sh', 'check.sh',
                     '.agents/adapters/_common/render.py'):
            self.assertFalse((self.project / gone).exists(), gone)
        self.assertFalse((self.project / '.agents/lib').exists())  # emptied directories are pruned
        self.assertEqual(self.source('update-remove', self.project, '--plan', 'f' * 64, ok=False)
                         .returncode, 1)

        self.source('update-restore', self.project)
        self.assertEqual(self.snapshot(), before)
        self.run_tool(self.project / 'check.sh', '--quiet')


class LegacyUpgradeTests(ExportedProject):
    def legacy_install(self):
        present = subprocess.run(['git', '-C', str(ROOT), 'cat-file', '-e', LEGACY_RELEASE + '^{commit}'],
                                 env=clean_env(), capture_output=True)
        if present.returncode:
            self.skipTest('legacy release {} is not in this clone (shallow history); the legacy '
                          'upgrade was NOT exercised'.format(LEGACY_RELEASE[:7]))
        old = self.base / 'old-source'
        old.mkdir()
        archive = subprocess.run(['git', '-C', str(ROOT), 'archive', LEGACY_RELEASE],
                                 env=clean_env(), capture_output=True, check=True).stdout
        subprocess.run(['tar', '-x', '-C', str(old)], input=archive, check=True)
        self.run_tool(old / '.agents/bootstrap.sh', 'export', self.project, cwd=old)
        self.assertFalse((self.project / '.harness').exists())
        self.assertFalse((self.project / '.agents/lib').exists())

    def test_upgrade_preserves_local_work_and_can_be_rolled_back(self):
        self.legacy_install()
        custom = (self.project / 'check.sh').read_text() + '\n# project-specific gate\n'
        (self.project / 'check.sh').write_text(custom)
        (self.project / 'src').mkdir()
        (self.project / 'src/app.py').write_text('print("mine")\n')

        adopted = json.loads(self.source('update-adopt', self.project).stdout)
        self.assertGreater(adopted['earlier_release'], 10)
        self.assertGreaterEqual(adopted['uncertain'], 1)
        installed = inventory.load(self.project)
        self.assertEqual(installed['framework_version'], 'legacy')
        self.assertIsNone(installed['files']['check.sh']['sha256'])
        before = self.snapshot()

        listing, digest = self.plan_digest('update-plan')
        self.assertIn('conflict check.sh  (uncertain baseline (legacy adoption))', listing)
        self.assertIn('replace  .agents/bootstrap.sh  (unchanged since install)', listing)
        self.assertIn('add      .agents/lib/update.py  (new file)', listing)
        self.assertNotIn('add      steering/', listing)
        self.assertEqual(self.snapshot(), before)

        applied = json.loads(self.source('update-apply', self.project, '--plan', digest).stdout)
        self.assertIn('check.sh', applied['conflicts'])
        self.assertEqual((self.project / 'check.sh').read_text(), custom)
        self.assertEqual((self.project / 'src/app.py').read_text(), 'print("mine")\n')
        self.assertIn('framework ' + inventory.declared()['framework_version'],
                      self.local('version').stdout)
        self.assertEqual(inventory.load(self.project)['framework_version'],
                         inventory.declared()['framework_version'])

        # The upgraded project works with the new tooling, on all five entry points.
        self.shape()
        self.assert_five_entry_points()
        self.assertIn('Harness SDD brief', self.local('brief').stdout)
        self.local('clean', '--all')
        # Its own old gateway is a conflict; once the maintainer accepts the new one, it passes.
        self.source('update-accept', self.project, 'check.sh')
        self.run_tool(self.project / 'check.sh', '--quiet')

    def test_rollback_returns_the_legacy_project_byte_for_byte(self):
        self.legacy_install()
        self.source('update-adopt', self.project)
        before = self.snapshot()
        _listing, digest = self.plan_digest('update-plan')
        self.source('update-apply', self.project, '--plan', digest)
        self.assertNotEqual(self.snapshot(), before)
        self.source('update-restore', self.project)
        self.assertEqual(self.snapshot(), before)


class NativeToolChecks(unittest.TestCase):
    def test_native_cli_validation_is_reported_as_not_performed(self):
        """Nothing here runs a vendor CLI. That is recorded, never counted as validation."""
        data = capabilities.load()
        self.assertEqual(sorted(NATIVE_BINARIES), sorted(data['adapters']))
        self.assertIn('not validated', data['native_validation'])
        for name, binary in sorted(NATIVE_BINARIES.items()):
            found = shutil.which(binary) is not None
            print('[SKIP] native check {}: not run ({} {} on this machine)'.format(
                name, binary, 'is' if found else 'is not'))


if __name__ == '__main__':
    unittest.main()
