"""Disposable repositories for M1 integration tests."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class RepositoryTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='harness-m1-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.env = os.environ.copy()
        for key in list(self.env):
            if key.startswith('GIT_') or key == 'ROOT_DIR':
                self.env.pop(key)

    def command(self, *args, cwd=None, ok=True, env=None):
        result = subprocess.run([str(arg) for arg in args], cwd=str(cwd or self.root),
                                env=env or self.env, text=True, capture_output=True)
        if ok:
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return result

    def export(self):
        dest = self.root / 'consumer'
        self.command(ROOT / '.agents/bootstrap.sh', 'export', dest, cwd=ROOT)
        return dest

    def save_manifest(self, root, manifest):
        (root / '.agents/agentic.json').write_text(json.dumps(manifest, indent=2) + '\n')

    def initialize(self, root):
        manifest = json.loads((root / '.agents/agentic.json').read_text())
        manifest['subagents'] = [{
            'name': 'fixture-engineer', 'mode': 'subagent', 'default': True,
            'description': 'Maintains the fixture application and its verification.',
            'role_file': '.agents/subagents/fixture-engineer/SUBAGENT.md',
            'permission': {'edit': {'specs/**': 'deny', '*': 'ask'}},
        }]
        manifest['target_clis'] = ['cursor', 'codex']
        agent = root / '.agents/subagents/fixture-engineer'
        agent.mkdir()
        (agent / 'SUBAGENT.md').write_text('# Fixture engineer\nMaintain the fixture application.\n')
        (agent / 'SOUL.md').write_text('# Identity\nA careful fixture engineer.\n')
        self.save_manifest(root, manifest)
        return manifest
