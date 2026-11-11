"""Session brief, quiet gateway, and context-budget regressions."""
import datetime
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.agents/lib'))

import session_brief  # noqa: E402

TASKS = ('# Tasks\n\n- [x] **T1** — Done already _(R1)_\n- [ ] **T2** — Build the thing _(R2)_\n'
         '- [ ] **T3** — Later _(R2)_\n')


class BriefTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='harness-brief-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def write(self, relative, content):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding='utf-8')
        return path

    def features(self, done=0):
        items = [{'id': 'F-{}'.format(n), 'name': 'old-{}'.format(n), 'status': 'done',
                  'description': 'x' * 400} for n in range(done)]
        items += [{'id': 'F-A', 'name': 'feat-a', 'status': 'in_progress', 'title': 'Active work'},
                  {'id': 'F-B', 'name': 'feat-b', 'status': 'spec_ready'},
                  {'id': 'F-C', 'name': 'feat-c', 'status': 'pending'},
                  {'id': 'F-D', 'name': 'feat-d', 'status': 'cancelled'}]
        self.write('feature_list.json', json.dumps({'features': items}))
        self.write('specs/feat-a/tasks.md', TASKS)


class BriefContentTests(BriefTest):
    def test_reports_active_feature_next_task_and_queues(self):
        self.features()
        self.write('progress/current.md', '# Current\nNext: finish T2\n')
        text = session_brief.brief(self.root)
        self.assertIn('active: F-A feat-a [in_progress, sdd] — Active work', text)
        self.assertIn('tasks 1/3 · next: T2 — Build the thing', text)
        self.assertIn('awaiting human approval: F-B feat-b', text)
        self.assertIn('next pending: F-C feat-c', text)
        self.assertIn('cancelled 1', text)
        self.assertIn('Next: finish T2', text)

    def test_size_does_not_grow_with_closed_features(self):
        self.features()
        small = len(session_brief.brief(self.root))
        self.features(done=300)
        self.assertGreater((self.root / 'feature_list.json').stat().st_size, 100000)
        self.assertLess(len(session_brief.brief(self.root)) - small, 40)

    def test_long_current_state_is_truncated_and_flagged(self):
        self.features()
        self.write('progress/current.md', 'state line\n' * 600)
        text = session_brief.brief(self.root)
        self.assertIn('[truncated: 2000 of', text)
        self.assertIn('progress/current.md is 6.6 KB (budget 3 KB, loaded every session)', text)
        self.assertLess(len(text), 3500)

    def test_fresh_manifest_points_to_init(self):
        self.features()
        self.write('.agents/agentic.json', json.dumps(
            {'subagents': [], '_template_subagents_examples': [{'name': 'x'}]}))
        self.assertIn('init: FRESH', session_brief.brief(self.root))

    def test_budget_is_configurable_in_the_manifest(self):
        self.features()
        self.write('.agents/agentic.json', json.dumps(
            {'subagents': [{'name': 'a'}], 'context_budget': {'AGENTS.md': 100}}))
        self.write('AGENTS.md', 'x' * 500)
        self.assertIn('AGENTS.md is 0.5 KB (budget 0 KB', session_brief.brief(self.root))

    def test_missing_or_invalid_state_is_reported_not_crashed(self):
        self.assertIn('feature_list.json not found', session_brief.brief(self.root))
        self.write('feature_list.json', '{not json')
        self.assertEqual(session_brief.main(['--root', str(self.root)]), 1)


class ArchiveTests(BriefTest):
    def test_archive_moves_log_and_leaves_a_stub(self):
        self.write('progress/handoff.md', '# Handoff\n' + 'entry\n' * 3000)
        day = datetime.date(2026, 1, 2)
        archived = session_brief.archive(self.root, 'progress/handoff.md', day)
        self.assertEqual(archived, 'progress/archive/handoff-20260102.md')
        self.assertIn('entry', (self.root / archived).read_text())
        stub = (self.root / 'progress/handoff.md').read_text()
        self.assertTrue(stub.startswith('# Handoff\n'))
        self.assertIn(archived, stub)
        self.assertLess(len(stub), 200)
        self.write('progress/handoff.md', '# Handoff\nmore\n')
        self.assertEqual(session_brief.archive(self.root, 'progress/handoff.md', day),
                         'progress/archive/handoff-20260102-2.md')

    def test_archive_refuses_paths_outside_progress_and_symlinks(self):
        self.write('progress/log.md', 'x')
        self.write('secret.md', 'x')
        for relative in ('secret.md', '../secret.md', 'progress/work/a.md', 'progress/log.txt',
                         str(self.root / 'progress/log.md')):
            with self.assertRaises(ValueError):
                session_brief.archive(self.root, relative)
        (self.root / 'progress/link.md').symlink_to(self.root / 'secret.md')
        with self.assertRaises(ValueError):
            session_brief.archive(self.root, 'progress/link.md')
        self.assertEqual((self.root / 'secret.md').read_text(), 'x')


class RepositoryContractTests(unittest.TestCase):
    """The shipped session path stays small; these are the budgets agents pay every session."""

    def test_session_files_fit_their_budgets(self):
        for relative, limit in (('AGENTS.md', 8000), ('.agents/commands/init.md', 8000),
                                ('.agents/adapters/claude-code/CLAUDE.md.tmpl', 4000)):
            self.assertLessEqual((ROOT / relative).stat().st_size, limit, relative)

    def test_entry_points_use_the_brief_instead_of_full_reads(self):
        for relative in ('AGENTS.md', '.agents/adapters/claude-code/CLAUDE.md.tmpl',
                         '.agents/adapters/gemini-cli/GEMINI.md.tmpl', '.agents/commands/status.md'):
            text = (ROOT / relative).read_text(encoding='utf-8')
            self.assertIn('bootstrap.sh brief', text, relative)
            self.assertNotIn('Read `feature_list.json`', text, relative)

    def test_bootstrap_dispatches_brief(self):
        result = subprocess.run([str(ROOT / '.agents/bootstrap.sh'), 'brief'], text=True,
                                capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(result.stdout.startswith('Harness SDD brief\nfeatures: '))

    def test_quiet_gateway_filters_passing_detail_and_keeps_exit_code(self):
        script = (ROOT / 'check.sh').read_text(encoding='utf-8')
        self.assertIn('--quiet)     QUIET=true', script)
        with tempfile.TemporaryDirectory(prefix='harness-quiet-') as temp:
            for name, code in (('ok', 0), ('bad', 3)):
                fake = Path(temp) / name
                head = script.split('ROOT_DIR="$(cd', 1)[0]
                fake.write_text(head + 'echo "  [PASS] one"; echo "  [WARN] two"; exit {}\n'.format(code))
                fake.chmod(0o755)
                result = subprocess.run([str(fake), '--quiet'], text=True, capture_output=True)
                self.assertEqual(result.returncode, code)
                self.assertIn('[WARN] two', result.stdout)
                self.assertEqual('[PASS] one' in result.stdout, code != 0)
            self.assertIn('check.sh: PASS (1 checks passed)', subprocess.run(
                [str(Path(temp) / 'ok'), '--quiet'], text=True, capture_output=True).stdout)


if __name__ == '__main__':
    unittest.main()
