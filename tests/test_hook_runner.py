"""Lifecycle hook runner: injection, containment, fail-closed, and timeout regressions."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / 'hooks/run-hooks.sh'
CANONICAL = ROOT / '.agents/lib/hook-runner.sh'


class RunnerTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='harness-hooks-')
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name).resolve()
        self.root = self.base / 'repo'
        (self.root / 'hooks').mkdir(parents=True)
        (self.root / '.agents').mkdir()
        runner = self.root / 'hooks/run-hooks.sh'
        runner.write_text(RUNNER.read_text(encoding='utf-8'), encoding='utf-8')
        runner.chmod(0o755)

    def script(self, relative, body, mode=0o755, base=None):
        path = (base or self.root) / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('#!/bin/bash\n' + body, encoding='utf-8')
        path.chmod(mode)
        return path

    def manifest(self, *hooks):
        (self.root / '.agents/agentic.json').write_text(json.dumps({'hooks': list(hooks)}))

    def hook(self, script, on_failure='error', event='on_test', **extra):
        return dict({'event': event, 'script': script, 'on_failure': on_failure,
                     'description': 'fixture | with a pipe'}, **extra)

    def run_event(self, event='on_test', *args, env=None):
        environment = {key: value for key, value in os.environ.items() if key != 'ROOT_DIR'}
        environment.update(env or {})
        return subprocess.run([str(self.root / 'hooks/run-hooks.sh'), event] + list(args),
                              text=True, capture_output=True, env=environment, cwd=str(self.root))


class RunnerBehaviorTests(RunnerTest):
    def test_installed_runner_is_the_canonical_copy(self):
        self.assertEqual(RUNNER.read_bytes(), CANONICAL.read_bytes())
        content = (ROOT / '.agents/lib/bootstrap-content.sh').read_text(encoding='utf-8')
        self.assertIn('hook-runner.sh', content)
        self.assertNotIn("<<'RUNNER'", content)

    def test_passing_hook_receives_context_and_description_with_pipe(self):
        self.script('hooks/ok.sh', 'echo "$HOOK_EVENT $FEATURE_ID $FEATURE_NAME" > "$ROOT_DIR/seen.txt"\n')
        self.manifest(self.hook('hooks/ok.sh'))
        result = self.run_event('on_test', '--feature-id', 'F-1', '--feature-name', 'feat')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('PASSED', result.stdout)
        self.assertEqual((self.root / 'seen.txt').read_text().strip(), 'on_test F-1 feat')

    def test_failure_policies(self):
        self.script('hooks/bad.sh', 'exit 7\n')
        self.script('hooks/after.sh', 'touch "$ROOT_DIR/after.txt"\n')
        for policy, code, later in (('error', 7, False), ('warn', 1, True), ('ignore', 0, True),
                                    ('typo-policy', 7, False)):
            marker = self.root / 'after.txt'
            if marker.exists():
                marker.unlink()
            self.manifest(self.hook('hooks/bad.sh', policy), self.hook('hooks/after.sh', 'ignore'))
            result = self.run_event()
            self.assertEqual(result.returncode, code, policy)
            self.assertEqual(marker.exists(), later, policy)

    def test_event_text_is_never_executed(self):
        self.manifest(self.hook('hooks/ok.sh'))
        marker = self.base / 'injected.txt'
        payload = "x' or __import__('pathlib').Path('{}').write_text('1') or '".format(marker)
        result = self.run_event(payload)
        self.assertEqual(result.returncode, 1)
        self.assertIn('invalid hook event name', result.stderr)
        self.assertFalse(marker.exists())

    def test_unreadable_manifest_fails_closed(self):
        (self.root / '.agents/agentic.json').write_text('{broken')
        self.assertEqual(self.run_event().returncode, 1)
        (self.root / '.agents/agentic.json').write_text(json.dumps({'hooks': ['not-an-object']}))
        self.assertEqual(self.run_event().returncode, 1)
        (self.root / '.agents/agentic.json').unlink()
        self.assertEqual(self.run_event().returncode, 0)

    def test_script_outside_the_repository_is_refused(self):
        marker = self.base / 'outside-ran.txt'
        outside = self.script('outside.sh', 'touch "{}"\n'.format(marker), base=self.base)
        (self.root / 'hooks/link.sh').symlink_to(outside)
        for script in ('../outside.sh', str(outside), 'hooks/link.sh', 'hooks/../../outside.sh'):
            self.manifest(self.hook(script))
            result = self.run_event()
            self.assertEqual(result.returncode, 1, script)
            self.assertIn('FAILED (aborting)', result.stdout, script)
            self.assertFalse(marker.exists(), script)

    def test_missing_or_non_executable_required_hook_does_not_pass(self):
        self.script('hooks/plain.sh', 'exit 0\n', mode=0o644)
        for script, reason in (('hooks/plain.sh', 'not executable'), ('hooks/none.sh', 'not found'),
                               (None, 'no script declared')):
            self.manifest(self.hook(script))
            result = self.run_event()
            self.assertEqual(result.returncode, 1, reason)
            self.assertIn(reason, result.stdout)
        self.manifest(self.hook('hooks/none.sh', 'ignore'))
        self.assertEqual(self.run_event().returncode, 0)

    def test_hanging_hook_times_out_and_follows_its_policy(self):
        self.script('hooks/hang.sh', 'sleep 30\n')
        self.manifest(self.hook('hooks/hang.sh', timeout_seconds=1))
        started = time.monotonic()
        result = self.run_event()
        self.assertLess(time.monotonic() - started, 15)
        self.assertEqual(result.returncode, 124)
        self.assertIn('timed out after 1s', result.stdout)
        self.manifest(self.hook('hooks/hang.sh', 'warn'))
        result = self.run_event(env={'HOOK_TIMEOUT_SECONDS': '1'})
        self.assertEqual(result.returncode, 1)
        self.assertIn('FAILED (warn): timed out', result.stdout)


class SkillSyncTests(unittest.TestCase):
    """sync-skills.sh installs only a validated, optionally pinned, registry commit."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='harness-skills-')
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name).resolve()
        self.registry = self.base / 'registry'
        self.project = self.base / 'project'
        skills = self.project / '.agents/skills'
        skills.mkdir(parents=True)
        script = skills / 'sync-skills.sh'
        script.write_text((ROOT / '.agents/skills/sync-skills.sh').read_text(encoding='utf-8'))
        script.chmod(0o755)
        (skills / 'README.md').write_text('local readme\n')
        (skills / 'existing').mkdir()
        (skills / 'existing/SKILL.md').write_text('existing skill\n')
        self.registry.mkdir()
        self.git('init', '-q')
        self.first = self.publish('alpha', 'alpha v1\n')

    def git(self, *args):
        result = subprocess.run(['git', '-C', str(self.registry), '-c', 'user.name=Fixture',
                                 '-c', 'user.email=fixture@example.invalid',
                                 '-c', 'commit.gpgsign=false'] + list(args),
                                text=True, capture_output=True,
                                env={k: v for k, v in os.environ.items() if not k.startswith('GIT_')})
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout.strip()

    def publish(self, name, text):
        path = self.registry / 'skills' / name / 'SKILL.md'
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
        self.git('add', '-A')
        self.git('commit', '-q', '-m', 'publish ' + name)
        return self.git('rev-parse', 'HEAD')

    def sync(self, ref=None, manifest=None):
        environment = {k: v for k, v in os.environ.items()
                       if not k.startswith('GIT_') and not k.startswith('SKILLS_REGISTRY_')}
        if manifest is not None:
            (self.project / '.agents/agentic.json').write_text(json.dumps(manifest))
        else:
            environment['SKILLS_REGISTRY_URL'] = self.registry.as_uri()
            if ref:
                environment['SKILLS_REGISTRY_REF'] = ref
        return subprocess.run([str(self.project / '.agents/skills/sync-skills.sh')], text=True,
                              capture_output=True, env=environment, cwd=str(self.base))

    def skill(self, name):
        path = self.project / '.agents/skills' / name / 'SKILL.md'
        return path.read_text() if path.exists() else None

    def test_pinned_commit_is_installed_even_after_the_registry_moves(self):
        self.publish('alpha', 'alpha v2 with new instructions\n')
        result = self.sync(manifest={'skills': {'registry': {'url': self.registry.as_uri(),
                                                              'ref': self.first}}})
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(self.skill('alpha'), 'alpha v1\n')
        self.assertIsNone(self.skill('existing'))
        self.assertEqual((self.project / '.agents/skills/README.md').read_text(), 'local readme\n')
        self.assertNotIn('WARNING', result.stderr)

    def test_unpinned_sync_warns_and_names_the_commit_to_pin(self):
        result = self.sync()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(self.skill('alpha'), 'alpha v1\n')
        self.assertIn('not pinned', result.stderr)
        self.assertIn(self.first, result.stderr)

    def test_failed_sync_keeps_the_current_skills(self):
        cases = [('f' * 40, 'not in the registry'), ('main', '40-character')]
        for ref, message in cases:
            result = self.sync(ref=ref)
            self.assertNotEqual(result.returncode, 0, ref)
            self.assertIn(message, result.stderr)
            self.assertEqual(self.skill('existing'), 'existing skill\n')
        self.git('rm', '-rq', 'skills')
        self.git('commit', '-q', '-m', 'drop skills')
        result = self.sync()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('no skills/ directory', result.stderr)
        self.assertEqual(self.skill('existing'), 'existing skill\n')

    def test_symlinks_in_the_registry_are_refused(self):
        (self.registry / 'skills/alpha/leak').symlink_to('/etc/hosts')
        self.git('add', '-A')
        self.git('commit', '-q', '-m', 'add link')
        result = self.sync()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('symbolic links', result.stderr)
        self.assertEqual(self.skill('existing'), 'existing skill\n')


if __name__ == '__main__':
    unittest.main()
