"""Adapter capability matrix (T22): every claim is checked against a real render."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.agents/lib'))

import capabilities  # noqa: E402
import evidence  # noqa: E402

PERMISSION = {'edit': {'specs/**': 'deny', 'src/**': 'allow', '*': 'ask'}}


def clean_env():
    return {key: value for key, value in os.environ.items()
            if not key.startswith('GIT_') and key != 'ROOT_DIR'}


class RenderedProject(unittest.TestCase):
    """One exported project with a role that denies edits to specs, rendered for every CLI."""

    @classmethod
    def setUpClass(cls):
        cls.data = capabilities.load()
        cls.temp = tempfile.TemporaryDirectory(prefix='harness-capabilities-')
        cls.root = Path(cls.temp.name).resolve() / 'project'
        cls.run_tool(ROOT / '.agents/bootstrap.sh', 'export', cls.root, cwd=ROOT)
        path = cls.root / '.agents/agentic.json'
        manifest = json.loads(path.read_text())
        manifest['subagents'] = [{
            'name': 'fixture-engineer', 'mode': 'subagent', 'default': True,
            'description': 'Maintains the fixture application.',
            'role_file': '.agents/subagents/fixture-engineer/SUBAGENT.md', 'permission': PERMISSION}]
        manifest['target_clis'] = list(cls.data['adapters'])
        role = cls.root / '.agents/subagents/fixture-engineer'
        role.mkdir()
        (role / 'SUBAGENT.md').write_text('# Fixture engineer\nMaintain the fixture.\n')
        (role / 'SOUL.md').write_text('# Identity\nCareful.\n')
        path.write_text(json.dumps(manifest, indent=2) + '\n')
        cls.before = cls.files()
        for name in cls.data['adapters']:
            cls.run_tool(cls.root / '.agents/bootstrap.sh', name, cwd=cls.root)
        cls.generated = cls.files() - cls.before

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    @classmethod
    def run_tool(cls, *args, cwd):
        result = subprocess.run([str(arg) for arg in args], cwd=str(cwd), env=clean_env(),
                                text=True, capture_output=True)
        assert result.returncode == 0, result.stdout + result.stderr

    @classmethod
    def files(cls):
        return {path.relative_to(cls.root).as_posix() for path in cls.root.rglob('*')
                if path.is_file() and '.git/' not in path.as_posix()
                and '__pycache__' not in path.parts}

    def text(self, relative):
        return (self.root / relative).read_text(encoding='utf-8')


class AdapterClaimTests(RenderedProject):
    def test_matrix_covers_exactly_the_adapters_the_renderer_knows(self):
        listed = subprocess.run(
            [sys.executable, str(ROOT / '.agents/adapters/_common/render.py'), '--list-renderers',
             '--root', str(ROOT)], text=True, capture_output=True, env=clean_env())
        self.assertEqual(listed.returncode, 0, listed.stderr)
        self.assertEqual(sorted(listed.stdout.split()), sorted(self.data['adapters']))

    def test_generated_files_match_the_declared_outputs(self):
        declared = set()
        for adapter in self.data['adapters'].values():
            for pattern in adapter['generates']:
                names = [item['name'] for item in json.loads(self.text('.agents/agentic.json'))['commands']]
                if '<name>' not in pattern:
                    declared.add(pattern)
                elif '/agents/' in pattern:
                    declared.add(pattern.replace('<name>', 'fixture-engineer'))
                else:
                    declared.update(pattern.replace('<name>', name) for name in names)
        self.assertEqual(self.generated, declared)

    def test_opencode_writes_permissions_into_native_config(self):
        agent = json.loads(self.text('opencode.json'))['agent']['fixture-engineer']
        self.assertEqual(agent['permission'], PERMISSION)
        self.assertEqual(self.data['adapters']['opencode']['edit_permissions']['level'], 'native-config')

    def test_claude_code_permissions_are_instruction_only(self):
        settings = json.loads(self.text('.claude/settings.json'))['permissions']
        self.assertEqual(settings['deny'], [])
        self.assertTrue(all(rule.startswith('Read(') for rule in settings['allow']))
        self.assertIn('"specs/**": "deny"', self.text('.claude/agents/fixture-engineer.md'))
        self.assertEqual(self.data['adapters']['claude-code']['edit_permissions']['level'],
                         'instruction-only')
        self.assertNotIn('enforces', self.text('CLAUDE.md'))

    def test_gemini_declares_its_permissions_soft(self):
        text = self.text('GEMINI.md')
        self.assertIn('Permission contract (soft', text)
        self.assertIn('"specs/**": "deny"', text)
        self.assertEqual(self.data['adapters']['gemini-cli']['edit_permissions']['level'],
                         'instruction-only')

    def test_cursor_does_not_render_the_permission_map(self):
        rule = self.text('.cursor/rules/harness-sdd.mdc')
        self.assertNotIn('"specs/**"', rule)
        self.assertNotIn('src/**', rule)
        self.assertIn('Never edit the approved spec', rule)
        self.assertFalse((self.root / '.cursor/hooks.json').exists())
        self.assertEqual(self.data['adapters']['cursor']['edit_permissions']['level'], 'not-rendered')

    def test_codex_generates_nothing(self):
        self.assertEqual(self.data['adapters']['codex']['generates'], [])
        self.assertFalse((self.root / '.codex').exists())
        self.assertNotIn('AGENTS.md', self.generated)

    def test_no_adapter_registers_a_native_lifecycle_hook(self):
        for name, adapter in self.data['adapters'].items():
            self.assertEqual(adapter['lifecycle_hooks']['level'], 'instruction-only', name)
        self.assertNotIn('hooks', json.loads(self.text('.claude/settings.json')))
        self.assertIn('workflow-transition', (ROOT / '.agents/commands/done.md').read_text())


class MatrixDocumentTests(unittest.TestCase):
    def test_document_is_generated_from_the_data_file(self):
        self.assertEqual((ROOT / capabilities.DOCUMENT).read_text(encoding='utf-8'),
                         capabilities.render())
        self.assertEqual(capabilities.main(['--root', str(ROOT), '--check']), 0)

    def test_drift_is_detected(self):
        with tempfile.TemporaryDirectory() as temp:
            (Path(temp) / 'docs').mkdir()
            self.assertEqual(capabilities.main(['--root', temp, '--check']), 1)
            self.assertEqual(capabilities.main(['--root', temp, '--write']), 0)
            self.assertEqual(capabilities.main(['--root', temp, '--check']), 0)

    def test_every_evidence_reference_exists(self):
        data = capabilities.load()
        references = [ref for adapter in data['adapters'].values() for ref in adapter['evidence']]
        references += [item['evidence'] for item in data['cli_independent_controls']]
        for reference in references:
            relative, _, symbol = reference.partition('::')
            path = ROOT / relative
            self.assertTrue(path.is_file(), reference)
            if symbol:
                self.assertTrue(evidence._symbol_exists(relative, path.read_text(), symbol), reference)

    def test_every_element_states_a_level_and_plugin_packaging_is_marked_optional(self):
        data = capabilities.load()
        text = capabilities.render(data)
        for name in data['adapters']:
            self.assertIn('## `{}`'.format(name), text)
        self.assertIn('FEAT-009', data['native_plugin_packaging'])
        self.assertIn('Optional and not shipped', data['native_plugin_packaging'])


if __name__ == '__main__':
    unittest.main()
