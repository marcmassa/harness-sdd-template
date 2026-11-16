import json
from pathlib import Path
import re
import shutil
import sys

from m1_support import ROOT, RepositoryTest


class BootstrapTests(RepositoryTest):
    def test_profile_fresh_partial_initialized_and_path_quoting(self):
        root = self.export()
        quoted = self.root / "consumer ' quoted"
        root.rename(quoted)
        root = quoted
        # ROOT_DIR is deliberately outside the source executable's own directory.
        env = dict(self.env, ROOT_DIR=str(root))
        fresh = self.command(ROOT / '.agents/bootstrap.sh', 'profile', env=env)
        self.assertIn('Steering: 0 active, 2 scaffold(s)', fresh.stdout)
        manifest = self.initialize(root)
        partial = self.command(ROOT / '.agents/bootstrap.sh', 'profile', env=env)
        self.assertIn('fixture-engineer', partial.stdout)
        # Quoting in other legacy commands is out of scope for profile regression.
        for key in list(manifest):
            if key.startswith('_template_'):
                del manifest[key]
        self.save_manifest(root, manifest)
        final = self.command(ROOT / '.agents/bootstrap.sh', 'profile', env=env)
        self.assertIn('Steering: 0 active, 0 scaffold(s)', final.stdout)

    def test_exported_gitignore_keeps_consumer_specs_committable(self):
        root = self.export()
        self.command('git', 'init', '-q', cwd=root)
        spec = root / 'specs/consumer-feature/requirements.md'
        spec.parent.mkdir(parents=True)
        spec.write_text('### R1\n')
        for relative in ('specs/consumer-feature/requirements.md', 'specs/README.md'):
            ignored = self.command('git', 'check-ignore', '-q', relative, cwd=root, ok=False)
            self.assertEqual(ignored.returncode, 1, relative + ' is ignored in the export')
        lock = self.command('git', 'check-ignore', '-q', 'progress/work/.workflow.lock',
                            cwd=root, ok=False)
        self.assertEqual(lock.returncode, 0)

    def test_detection_failure_is_not_silent_empty_stack(self):
        script = (ROOT / 'tests/test_cli_adapter_parity.sh').read_text()
        snippet = re.search(r'DETECTED_STACK=\$\(python3 -c "(.*?)"\)', script, re.S).group(1)
        (self.root / '.agents/adapters/_common').mkdir(parents=True)
        (self.root / '.agents/adapters/_common/render.py').write_text(
            'def detect_stack(*args):\n    raise RuntimeError("injected detector failure")\n')
        self.save_manifest(self.root, {})
        result = self.command(sys.executable, '-c', snippet.replace('\\"', '"'), ok=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('injected detector failure', result.stderr)
        self.assertNotIn('2>/dev/null ||', script[script.index('DETECTED_STACK='):script.index('if [ -n "$DETECTED_STACK"')])

    def test_export_init_render_check_clean_lifecycle(self):
        root = self.export()
        boot = root / '.agents/bootstrap.sh'
        self.command('git', 'init', '-q', cwd=root)
        self.command(boot, 'profile', cwd=root)
        self.command(boot, 'codex', cwd=root)
        self.initialize(root)
        self.command(boot, 'remove-examples', '--yes', cwd=root)
        self.command(boot, 'init', '--validate', cwd=root)
        user_file = root / '.cursor/commands/user-command.md'
        user_file.parent.mkdir(parents=True, exist_ok=True)
        user_file.write_text('User-maintained command\n')
        self.command(boot, '--all', '--yes', cwd=root)
        paths = sorted(p for p in (root / '.cursor').rglob('*') if p.is_file())
        before = {p.relative_to(root).as_posix(): p.read_bytes() for p in paths}
        self.command(boot, '--all', '--yes', cwd=root)
        after = {p.relative_to(root).as_posix(): p.read_bytes() for p in paths}
        self.assertEqual(before, after)
        self.command(boot, '--check', cwd=root)
        self.command(root / 'check.sh', cwd=root)
        self.command(boot, 'clean', '--all', cwd=root)
        self.assertEqual(user_file.read_text(), 'User-maintained command\n')
        self.assertFalse((root / '.cursor/rules/harness-sdd.mdc').exists())
        self.assertTrue((root / '.agents/agentic.json').exists())
