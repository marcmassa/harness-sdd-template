"""init --apply: one deterministic command shapes a fresh project (MAINT-004)."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


def clean_env():
    return {key: value for key, value in os.environ.items()
            if not key.startswith('GIT_') and key != 'ROOT_DIR'}


class FreshProject(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='harness-init-apply-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve() / 'project'
        self.run_tool(ROOT / '.agents/bootstrap.sh', 'export', self.root, cwd=ROOT)

    def run_tool(self, *args, cwd=None, ok=True):
        result = subprocess.run([str(arg) for arg in args], cwd=str(cwd or self.root), env=clean_env(),
                                text=True, capture_output=True)
        if ok:
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return result

    def init(self, *args, ok=True):
        return self.run_tool(self.root / '.agents/bootstrap.sh', 'init', '--apply', *args, ok=ok)

    def manifest(self):
        return json.loads((self.root / '.agents/agentic.json').read_text(encoding='utf-8'))


class ApplyTests(FreshProject):
    def test_one_command_completes_init_and_passes_the_gates(self):
        result = self.init('--clis', 'claude-code')
        self.assertIn('init: COMPLETE', result.stdout)
        self.assertLess(len(result.stdout), 400, 'the report is paid for in tokens')
        manifest = self.manifest()
        self.assertEqual([a['name'] for a in manifest['subagents']],
                         ['harness', 'spec-author', 'implementer', 'reviewer'])
        self.assertEqual(manifest['target_clis'], ['claude-code'])
        self.assertNotIn('_template_subagents_examples', manifest)
        self.assertNotIn('_template_lifecycle', manifest)
        for agent in manifest['subagents']:
            self.assertFalse({'_lifecycle', '_intent', 'category'} & set(agent), agent['name'])
            self.assertIn('specs/**', agent['permission']['edit'], agent['name'])
            soul = (self.root / agent['soul']).read_text(encoding='utf-8')
            self.assertNotIn('[', soul, agent['name'] + ' SOUL has a placeholder')
            self.assertTrue((self.root / '.claude/agents' / (agent['name'] + '.md')).is_file())
        self.assertFalse((self.root / 'opencode.json').exists())
        self.run_tool(self.root / '.agents/bootstrap.sh', 'init', '--validate')
        self.run_tool(self.root / 'check.sh', '--quiet')
        brief = self.run_tool(self.root / '.agents/bootstrap.sh', 'brief').stdout
        self.assertNotIn('init:', brief)
        self.assertNotIn('context budget exceeded', brief)
        self.assertNotIn('/init', brief)

    def test_language_implementers_replace_the_generic_one(self):
        self.init('--clis', 'claude-code,opencode', '--implementer', 'python=**/*.py,tests/**',
                  '--implementer', 'ts=**/*.ts')
        agents = {a['name']: a for a in self.manifest()['subagents']}
        self.assertEqual(list(agents), ['harness', 'spec-author', 'python-implementer',
                                        'ts-implementer', 'reviewer'])
        python = agents['python-implementer']
        self.assertEqual(python['permission']['edit'], {
            'specs/**': 'deny', 'feature_list.json': 'ask', '**/*.py': 'allow', 'tests/**': 'allow',
            '*': 'ask'})
        card = (self.root / python['role_file']).read_text(encoding='utf-8')
        self.assertIn('name: python-implementer', card)
        self.assertIn('## Mission', card)
        self.assertFalse((self.root / '.agents/subagents/implementer').exists())
        self.assertTrue((self.root / 'opencode.json').is_file())
        self.run_tool(self.root / 'check.sh', '--quiet')

    def test_optional_scaffold_reports_the_files_to_customize(self):
        result = self.init('--clis', 'claude-code', '--add', 'cloud-architect')
        self.assertIn('.agents/subagents/cloud-architect/SOUL.md', result.stdout)
        self.assertIn('cloud-architect', [a['name'] for a in self.manifest()['subagents']])

    def test_dry_run_writes_nothing(self):
        before = (self.root / '.agents/agentic.json').read_text(encoding='utf-8')
        result = self.init('--clis', 'cursor', '--implementer', 'go=**/*.go', '--dry-run')
        self.assertIn('harness, spec-author, go-implementer, reviewer', result.stdout)
        self.assertEqual((self.root / '.agents/agentic.json').read_text(encoding='utf-8'), before)
        self.assertFalse((self.root / '.agents/subagents/go-implementer').exists())

    def test_bad_plans_are_refused_without_changes(self):
        before = (self.root / '.agents/agentic.json').read_text(encoding='utf-8')
        for args, message in ((('--clis', 'nope'), 'unknown CLI'),
                              ((), '--clis is required'),
                              (('--clis', 'cursor', '--implementer', 'python'), 'is not <language>=<glob>'),
                              (('--clis', 'cursor', '--add', 'harness'), 'not an optional scaffold'),
                              (('--clis', 'cursor', '--implementer', 'go=*.go', '--implementer', 'go=x/**'),
                               'duplicate')):
            result = self.init(*args, ok=False)
            self.assertEqual(result.returncode, 1, args)
            self.assertIn(message, result.stderr, args)
        self.assertEqual((self.root / '.agents/agentic.json').read_text(encoding='utf-8'), before)

    def test_refuses_a_project_that_is_already_shaped(self):
        self.init('--clis', 'claude-code')
        result = self.init('--clis', 'claude-code', ok=False)
        self.assertEqual(result.returncode, 1)
        self.assertIn('only runs on a FRESH manifest', result.stderr)


if __name__ == '__main__':
    unittest.main()
