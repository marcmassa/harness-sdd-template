"""Framework versions, installed inventory, legacy adoption, and unknown-format rejection (T20)."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.agents/lib'))

import inventory  # noqa: E402

BOOTSTRAP = ROOT / '.agents/bootstrap.sh'


def clean_env():
    return {key: value for key, value in os.environ.items()
            if not key.startswith('GIT_') and key != 'ROOT_DIR'}


class InventoryTest(unittest.TestCase):
    exported = None

    @classmethod
    def setUpClass(cls):
        cls.shared = tempfile.TemporaryDirectory(prefix='harness-inventory-')
        cls.exported = Path(cls.shared.name).resolve() / 'release'
        result = subprocess.run([str(BOOTSTRAP), 'export', str(cls.exported)], text=True,
                                capture_output=True, env=clean_env(), cwd=str(ROOT))
        assert result.returncode == 0, result.stdout + result.stderr

    @classmethod
    def tearDownClass(cls):
        cls.shared.cleanup()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='harness-consumer-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve() / 'consumer'

    def install(self):
        result = subprocess.run(['cp', '-R', str(self.exported), str(self.root)])
        self.assertEqual(result.returncode, 0)
        return self.root

    def bootstrap(self, *args, root=None):
        return subprocess.run([str((root or self.root) / '.agents/bootstrap.sh')] + list(args),
                              text=True, capture_output=True, env=clean_env(),
                              cwd=str(root or self.root))

    def document(self):
        return json.loads((self.root / inventory.INVENTORY).read_text())

    def save(self, document):
        (self.root / inventory.INVENTORY).write_text(json.dumps(document))


class VersionDeclarationTests(InventoryTest):
    def test_release_and_format_versions_are_declared_with_ranges(self):
        data = inventory.declared()
        self.assertRegex(data['framework_version'], r'^\d+\.\d+\.\d+$')
        for kind in ('manifest', 'work_record', 'inventory'):
            self.assertIn(data['formats'][kind]['current'], data['formats'][kind]['supported'])
        self.assertLessEqual(inventory.version_key(data['update_from']['minimum']),
                             inventory.version_key(data['framework_version']))
        schema = json.loads((ROOT / '.agents/schemas/work-record.json').read_text())
        self.assertEqual(schema['format_version'], data['formats']['work_record']['current'])
        manifest = json.loads((ROOT / '.agents/agentic.json').read_text())
        self.assertEqual(manifest['version'], data['formats']['manifest']['current'])

    def test_version_command_reports_declarations_and_install_state(self):
        self.install()
        output = self.bootstrap('version').stdout
        self.assertIn('framework ' + inventory.declared()['framework_version'], output)
        self.assertIn('work_record format 1 (supported: 1)', output)
        self.assertRegex(output, r'installed: \d+\.\d+\.\d+ — \d+ unchanged, 0 modified, 0 missing')
        self.assertIn('no .harness/installed.json', subprocess.run(
            [str(BOOTSTRAP), 'version'], text=True, capture_output=True, env=clean_env()).stdout)


class ExportInventoryTests(InventoryTest):
    def test_export_records_every_installed_file_with_owner_and_baseline(self):
        self.install()
        document = self.document()
        self.assertEqual(document['framework_version'], inventory.declared()['framework_version'])
        files = document['files']
        self.assertEqual(sorted(files), inventory.payload(self.root))
        self.assertNotIn(inventory.INVENTORY, files)
        self.assertEqual(files['check.sh']['ownership'], 'framework')
        self.assertEqual(files['.agents/lib/workflow.py']['ownership'], 'framework')
        self.assertEqual(files['specs/README.md']['ownership'], 'framework')
        for seed in ('feature_list.json', '.agents/agentic.json', 'DESIGN.md', 'progress/current.md'):
            self.assertEqual(files[seed]['ownership'], 'seed', seed)
        self.assertEqual(files['check.sh']['sha256'], inventory.digest(self.root / 'check.sh'))

    def test_export_is_deterministic_and_carries_no_maintainer_history(self):
        second = Path(self.shared.name) / 'release-again'
        result = subprocess.run([str(BOOTSTRAP), 'export', str(second)], text=True,
                                capture_output=True, env=clean_env(), cwd=str(ROOT))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((second / inventory.INVENTORY).read_bytes(),
                         (self.exported / inventory.INVENTORY).read_bytes())
        files = json.loads((second / inventory.INVENTORY).read_text())['files']
        self.assertFalse([path for path in files if path.startswith('specs/hybrid-team')
                          or path.startswith('progress/impl_') or path.startswith('tests/')])

    def test_status_distinguishes_modified_missing_and_foreign_files(self):
        self.install()
        (self.root / 'check.sh').write_text('#!/bin/sh\n# customized\n')
        (self.root / 'docs/quality-checks.md').unlink()
        (self.root / 'my-own-file.md').write_text('mine\n')
        _document, result = inventory.status(self.root)
        self.assertEqual(result['modified'], ['check.sh'])
        self.assertEqual(result['missing'], ['docs/quality-checks.md'])
        self.assertNotIn('my-own-file.md', sum(result.values(), []))

    def test_install_is_recorded_once(self):
        self.install()
        with self.assertRaisesRegex(ValueError, 'already exists'):
            inventory.create(self.root)


class UnknownVersionTests(InventoryTest):
    def test_unknown_inventory_format_blocks_commands_and_check(self):
        self.install()
        document = self.document()
        document['format_version'] = 99
        self.save(document)
        result = self.bootstrap('profile')
        self.assertEqual(result.returncode, 1)
        self.assertIn('unsupported inventory format_version 99', result.stderr)
        self.assertIn('supports 1', result.stderr)
        check = subprocess.run([str(self.root / 'check.sh'), '--no-color', '--spec-only'], text=True,
                               capture_output=True, env=clean_env(), cwd=str(self.root))
        self.assertEqual(check.returncode, 1)
        self.assertIn('Unsupported format version', check.stdout)
        self.assertEqual(self.bootstrap('version').returncode, 1)

    def test_unknown_manifest_format_is_refused_before_rendering(self):
        self.install()
        path = self.root / '.agents/agentic.json'
        manifest = json.loads(path.read_text())
        manifest['version'] = 2
        path.write_text(json.dumps(manifest))
        result = self.bootstrap('opencode')
        self.assertEqual(result.returncode, 1)
        self.assertIn('unsupported manifest format_version 2', result.stderr)
        self.assertFalse((self.root / 'opencode.json').exists())

    def test_manifest_without_a_version_is_read_as_format_one(self):
        self.install()
        path = self.root / '.agents/agentic.json'
        manifest = json.loads(path.read_text())
        del manifest['version']
        path.write_text(json.dumps(manifest))
        self.assertEqual(inventory.check_manifest(self.root), 1)

    def test_inventory_from_a_newer_framework_is_refused(self):
        self.install()
        document = self.document()
        document['framework_version'] = '99.0.0'
        self.save(document)
        with self.assertRaisesRegex(ValueError, 'newer than this framework'):
            inventory.load(self.root)

    def test_malformed_inventory_paths_are_refused(self):
        self.install()
        for bad in ('../outside', '/etc/passwd', 'a/./b', ''):
            document = self.document()
            document['files'] = {bad: {'sha256': 'a' * 64, 'ownership': 'framework'}}
            self.save(document)
            with self.assertRaises(ValueError, msg=bad):
                inventory.load(self.root)
        document = self.document()
        document['files'] = {'check.sh': {'sha256': 'short', 'ownership': 'framework'}}
        self.save(document)
        with self.assertRaisesRegex(ValueError, 'malformed'):
            inventory.load(self.root)


class LegacyAdoptionTests(InventoryTest):
    def legacy(self):
        self.install()
        (self.root / inventory.INVENTORY).unlink()
        (self.root / '.harness').rmdir()

    def test_adoption_owns_matching_files_and_marks_changed_ones_uncertain(self):
        self.legacy()
        (self.root / 'check.sh').write_text('#!/bin/sh\n# older or customized\n')
        (self.root / 'docs/quality-checks.md').unlink()
        (self.root / 'project-only.md').write_text('mine\n')
        result = self.bootstrap('inventory-adopt', str(self.exported))
        self.assertEqual(result.returncode, 0, result.stderr)
        document = self.document()
        self.assertEqual(document['framework_version'], 'legacy')
        self.assertIsNone(document['files']['check.sh']['sha256'])
        self.assertEqual(document['files']['AGENTS.md']['sha256'],
                         inventory.digest(self.root / 'AGENTS.md'))
        self.assertNotIn('docs/quality-checks.md', document['files'])
        self.assertNotIn('project-only.md', document['files'])
        self.assertEqual(document['adopted']['uncertain'], 1)
        _document, status = inventory.status(self.root)
        self.assertEqual(status['uncertain'], ['check.sh'])
        self.assertEqual((self.root / 'check.sh').read_text(), '#!/bin/sh\n# older or customized\n')

    def test_adoption_needs_a_release_tree_and_never_replaces_an_inventory(self):
        self.legacy()
        with self.assertRaisesRegex(ValueError, 'has no .harness/installed.json'):
            inventory.adopt(self.root, ROOT)
        inventory.adopt(self.root, self.exported)
        with self.assertRaisesRegex(ValueError, 'already exists'):
            inventory.adopt(self.root, self.exported)

    def test_adoption_of_an_unrelated_directory_is_refused(self):
        self.root.mkdir(parents=True)
        (self.root / 'unrelated.txt').write_text('x')
        with self.assertRaisesRegex(ValueError, 'no file of this project matches'):
            inventory.adopt(self.root, self.exported)


if __name__ == '__main__':
    unittest.main()
