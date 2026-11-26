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
        self.assertEqual([a['name'] for a in manifest['subagents']], ['architect-qa', 'implementer'])
        self.assertEqual(manifest['default_agent'], 'architect-qa')
        self.assertEqual([a['name'] for a in manifest['subagents'] if a['mode'] == 'primary'],
                         ['architect-qa'])
        for pruned in ('harness', 'spec-author', 'reviewer'):
            self.assertFalse((self.root / '.agents/subagents' / pruned).exists(), pruned)
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

    def test_plan_proposes_the_command_from_the_project(self):
        (self.root / 'pyproject.toml').write_text('[project]\nname = "x"\n')
        before = (self.root / '.agents/agentic.json').read_text(encoding='utf-8')
        env = dict(clean_env(), CLAUDECODE='1')
        result = subprocess.run([str(self.root / '.agents/bootstrap.sh'), 'init', '--plan'],
                                cwd=str(self.root), env=env, text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("proposed: ./.agents/bootstrap.sh init --apply --clis claude-code "
                      "--implementer 'python=**/*.py'", result.stdout)
        self.assertLess(len(result.stdout), 500)
        self.assertEqual((self.root / '.agents/agentic.json').read_text(encoding='utf-8'), before)

    def test_check_passes_in_a_project_with_its_own_tests_directory(self):
        (self.root / 'tests').mkdir()
        (self.root / 'tests/test_app.py').write_text('def test_ok():\n    assert True\n')
        self.init('--clis', 'claude-code')
        result = self.run_tool(self.root / 'check.sh', '--quiet')
        self.assertNotIn('Missing required', result.stdout)
        current = (self.root / 'progress/current.md').read_text(encoding='utf-8')
        self.assertNotIn('{YYYY-MM-DD}', current)

    def test_language_implementers_replace_the_generic_one(self):
        self.init('--clis', 'claude-code,opencode', '--implementer', 'python=**/*.py,tests/**',
                  '--implementer', 'ts=**/*.ts')
        agents = {a['name']: a for a in self.manifest()['subagents']}
        self.assertEqual(list(agents), ['architect-qa', 'python-implementer', 'ts-implementer'])
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

    def test_split_duties_are_optional_and_never_a_second_primary(self):
        self.init('--clis', 'claude-code', '--add', 'reviewer', '--add', 'spec-author',
                  '--add', 'harness')
        agents = {a['name']: a for a in self.manifest()['subagents']}
        self.assertEqual(list(agents), ['architect-qa', 'implementer', 'reviewer', 'spec-author', 'harness'])
        self.assertEqual([n for n, a in agents.items() if a['mode'] == 'primary'], ['architect-qa'])
        self.assertEqual(agents['reviewer']['permission']['edit']['specs/**'], 'deny')
        self.run_tool(self.root / 'check.sh', '--quiet')

    def test_dry_run_writes_nothing(self):
        before = (self.root / '.agents/agentic.json').read_text(encoding='utf-8')
        result = self.init('--clis', 'cursor', '--implementer', 'go=**/*.go', '--dry-run')
        self.assertIn('sub-agents: architect-qa, go-implementer |', result.stdout)
        self.assertEqual((self.root / '.agents/agentic.json').read_text(encoding='utf-8'), before)
        self.assertFalse((self.root / '.agents/subagents/go-implementer').exists())

    def test_bad_plans_are_refused_without_changes(self):
        before = (self.root / '.agents/agentic.json').read_text(encoding='utf-8')
        for args, message in ((('--clis', 'nope'), 'unknown CLI'),
                              ((), '--clis is required'),
                              (('--clis', 'cursor', '--implementer', 'python'), 'is not <language>=<glob>'),
                              (('--clis', 'cursor', '--add', 'architect-qa'), 'not an optional scaffold'),
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



class ExtensionCommandTests(FreshProject):
    """add-hook, remove-hook and add-steering accept their documented options."""

    def bootstrap(self, *args, ok=True):
        return self.run_tool(self.root / '.agents/bootstrap.sh', *args, ok=ok)

    def test_add_and_remove_hook_with_every_option(self):
        self.init('--clis', 'claude-code')
        script = self.root / 'hooks/on-implementation-complete_tests.sh'
        script.write_text('#!/bin/bash\nexit 0\n')
        script.chmod(0o755)
        self.bootstrap('add-hook', '--event', 'on_implementation_complete', '--script',
                       'hooks/on-implementation-complete_tests.sh', '--description', 'Run the tests',
                       '--on-failure', 'error', '--yes')
        self.assertEqual(self.manifest()['hooks'], [{
            'event': 'on_implementation_complete', 'script': 'hooks/on-implementation-complete_tests.sh',
            'description': 'Run the tests', 'on_failure': 'error'}])
        self.bootstrap('remove-hook', '--event', 'on_implementation_complete', '--script',
                       'hooks/on-implementation-complete_tests.sh', '--yes')
        self.assertEqual(self.manifest()['hooks'], [])

    def test_add_steering_with_options(self):
        self.init('--clis', 'claude-code')
        self.bootstrap('add-steering', 'api-rules', '--description', 'API conventions',
                       '--applies-to', 'implementer', '--yes')
        entry = [s for s in self.manifest()['steering'] if s['name'] == 'api-rules'][0]
        self.assertEqual(entry['description'], 'API conventions')
        self.assertEqual(entry['applies_to'], ['implementer'])

if __name__ == '__main__':
    unittest.main()
