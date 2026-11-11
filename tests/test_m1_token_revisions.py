"""Immutable-revision checks share exactly the hook's authored-file policy."""
import subprocess
import sys

import test_token_limit as hook_tests

HOOK = hook_tests.HOOK


class RevisionTokenTests(hook_tests.TokenLimitTests):
    def commit(self):
        self.git('-c', 'core.hooksPath=/dev/null', '-c', 'commit.gpgsign=false',
                 'commit', '-qm', 'fixture')
        return self.git('rev-parse', 'HEAD').decode().strip()

    def revision_check(self, base=None, candidate='HEAD', initial=False):
        command = [sys.executable, str(HOOK), '--candidate', candidate]
        command += ['--initial'] if initial else ['--base', base]
        return subprocess.run(command, cwd=self.root, env=self.env,
                              capture_output=True, text=True)

    def test_revision_attributes_not_working_tree(self):
        self.write('baseline.md', b'small')
        base = self.commit()
        self.write('oversized.py', b'x' * 20001)
        candidate = self.commit()
        self.write('.gitattributes', b'oversized.py generated=true\n')
        result = self.revision_check(base, candidate)
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn('oversized.py', result.stderr)
        approved_candidate = self.commit()
        self.write('.gitattributes', b'', stage=False)
        self.assertEqual(self.revision_check(base, approved_candidate).returncode, 0)

    def test_unchanged_legacy_large_file_is_not_scanned(self):
        self.write('legacy.txt', b'x' * 20001)
        base = self.commit()
        self.write('small.txt', b'ok')
        candidate = self.commit()
        self.assertEqual(self.revision_check(base, candidate).returncode, 0)
        self.assertEqual(self.revision_check(candidate=candidate, initial=True).returncode, 1)

    def test_invalid_or_missing_revision_is_failure(self):
        self.write('small.txt', b'ok')
        base = self.commit()
        for candidate in ('not-a-revision', '0' * 40):
            self.assertNotEqual(self.revision_check(base, candidate).returncode, 0)
        self.assertNotEqual(self.revision_check('absent-base').returncode, 0)
        self.assertNotEqual(self.revision_check('').returncode, 0)

    def test_renamed_large_file_and_deleted_file(self):
        self.write('old.txt', b'x' * 20001)
        base = self.commit()
        self.git('mv', 'old.txt', 'renamed\nfile.txt')
        candidate = self.commit()
        self.assertEqual(self.revision_check(base, candidate).returncode, 1)
        self.git('rm', 'renamed\nfile.txt')
        deleted = self.commit()
        self.assertEqual(self.revision_check(candidate, deleted).returncode, 0)
