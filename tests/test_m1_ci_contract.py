"""Static CI contract; actual runner evidence is recorded separately."""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class CIContractTests(unittest.TestCase):
    def test_four_supported_combinations_and_read_only_permissions(self):
        workflow = (ROOT / '.github/workflows/ci.yml').read_text()
        for required in ('ubuntu-latest', 'macos-latest', "'3.10'", "'3.13'",
                         'contents: read', 'persist-credentials: false',
                         'fetch-depth: 0', 'run: ./check.sh', '--base', '--candidate',
                         '--initial', '--direct'):
            self.assertIn(required, workflow)
        self.assertNotIn('pull_request_target', workflow)
        self.assertNotIn('write-all', workflow)

    def test_every_action_is_pinned_to_a_full_commit(self):
        pinned = re.compile(r'^[\w.-]+/[\w./-]+@[0-9a-f]{40}$')
        for workflow in sorted((ROOT / '.github/workflows').glob('*.yml')):
            uses = re.findall(r'^\s*(?:-\s*)?uses:\s*(\S+)', workflow.read_text(), re.MULTILINE)
            self.assertTrue(uses, workflow.name)
            for reference in uses:
                self.assertRegex(reference, pinned, '{}: {}'.format(workflow.name, reference))
