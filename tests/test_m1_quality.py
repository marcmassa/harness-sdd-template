import json
import sys

from m1_support import ROOT, RepositoryTest

QUALITY = ROOT / '.agents/lib/quality.py'


class QualityTests(RepositoryTest):
    def run_quality(self):
        return self.command(sys.executable, QUALITY, '--root', self.root, ok=False)

    def manifest(self, checks):
        (self.root / '.agents').mkdir(exist_ok=True)
        self.save_manifest(self.root, {'quality_checks': checks})

    def test_unittest_folder_does_not_require_pytest(self):
        (self.root / 'tests').mkdir()
        (self.root / 'tests/test_example.py').write_text('import unittest\n')
        result = self.run_quality()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('[PASS] python-syntax', result.stdout)
        self.assertIn('[SKIP] pytest', result.stdout)
        self.assertFalse((self.root / 'tests/__pycache__').exists())

    def test_syntax_error_is_mandatory_failure(self):
        (self.root / 'broken.py').write_text('def broken(\n')
        result = self.run_quality()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('[FAIL] python-syntax', result.stdout)

    def test_missing_required_and_optional_tools(self):
        self.manifest([{'id': 'optional', 'command': ['harness-absent-tool-123'], 'required': False}])
        result = self.run_quality()
        self.assertEqual(result.returncode, 0)
        self.assertIn('[SKIP] optional (optional): missing executable', result.stdout)
        self.manifest([{'id': 'required', 'command': ['harness-absent-tool-123']}])
        result = self.run_quality()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('[FAIL] required (required)', result.stdout)

    def test_child_exit_code_blocks_but_other_checks_still_run(self):
        self.manifest([
            {'id': 'broken', 'command': [sys.executable, '-c', 'raise SystemExit(42)']},
            {'id': 'following', 'command': [sys.executable, '-c', 'pass']},
        ])
        result = self.run_quality()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('exit 42', result.stdout)
        self.assertIn('[PASS] following', result.stdout)

    def test_gateway_propagates_failure(self):
        root = self.export()
        (root / 'broken.py').write_text('not valid python !\n')
        result = self.command(root / 'check.sh', cwd=root, ok=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Mandatory project checks failed', result.stdout)

    def test_malformed_configuration_and_duplicates_fail(self):
        for checks in ([{'id': 'x', 'command': 'echo unsafe'}],
                       [{'id': 'x', 'command': [sys.executable, '-c', 'pass'], 'required': 'false'}],
                       [{'id': 'x', 'command': [sys.executable, '-c', 'pass']}] * 2):
            self.manifest(checks)
            result = self.run_quality()
            self.assertNotEqual(result.returncode, 0)
