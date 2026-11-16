"""Pilot report validation and offline release readiness (T25)."""
import copy
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
import release  # noqa: E402

EXAMPLE = json.loads((ROOT / 'docs/pilots/example-synthetic.json').read_text())
TASKS = ''.join('- [x] **T{}** — task {}\n'.format(n, n) for n in range(1, 28)) + '- [ ] **T28** — later\n'


def fixture_pilot(identifier, context, summary):
    """Fixture data for the validator. Made inside a temporary directory, never shipped."""
    report = copy.deepcopy(EXAMPLE)
    report.update(id=identifier, kind='real', context=context, work_summary=summary)
    if context == 'team':
        report['participants'] = [
            {'role': 'maintainer', 'kind': 'human', 'cli': 'claude-code', 'consent': True},
            {'role': 'developer', 'kind': 'human', 'cli': 'cursor', 'consent': True},
            {'role': 'implementer', 'kind': 'agent', 'cli': 'cursor'}]
    return report


class PilotReportTests(unittest.TestCase):
    def invalid(self, message, **changes):
        report = copy.deepcopy(EXAMPLE)
        for key, value in changes.items():
            target = report
            parts = key.split('__')
            for part in parts[:-1]:
                target = target[part]
            if value is None:
                target.pop(parts[-1], None)
            else:
                target[parts[-1]] = value
        with self.assertRaisesRegex(ValueError, message):
            release.validate_pilot(report)

    def test_shipped_example_is_valid_and_labeled_synthetic(self):
        self.assertEqual(release.validate_pilot(copy.deepcopy(EXAMPLE))['kind'], 'synthetic')
        self.assertIn('SYNTHETIC', EXAMPLE['work_summary'])
        reports = release.pilot_reports(ROOT)
        self.assertTrue(reports)
        self.assertEqual([name for name, report, _error in reports if report and report['kind'] == 'real'],
                         [], 'a real pilot report must come from a real pilot, reviewed by its participants')

    def test_missing_or_invalid_fields_are_rejected(self):
        self.invalid('kind must be', kind='pilot')
        self.invalid('context must be', context='solo')
        self.invalid('YYYY-MM-DD', date_range__from='yesterday')
        self.invalid('ends before it starts', date_range__to='2020-01-01')
        self.invalid('framework_version', framework_version='latest')
        self.invalid('work_summary is required', work_summary=' ')
        self.invalid('baseline is required', baseline=None)
        self.invalid('exercise handoff was not carried out', exercises__handoff__done=False)
        self.invalid('exercise recovery was not carried out', exercises__recovery=None)
        self.invalid('exercise upgrade notes', exercises__upgrade__notes='')
        self.invalid('metric false_blocks', metrics__false_blocks=None)
        self.invalid('metric rework_count', metrics__rework_count=-1)
        self.invalid('unresolved_issues must be a list', unresolved_issues=None)
        self.invalid('needs a severity', unresolved_issues=[{'summary': 'x', 'severity': 'tiny'}])
        self.invalid('not been reviewed by a human', human_review__reviewed=False)
        self.invalid('evidence_ref', human_review__evidence_ref='')

    def test_participants_must_fit_the_context_and_consent(self):
        human = {'role': 'maintainer', 'kind': 'human', 'cli': 'claude-code', 'consent': True}
        agent = {'role': 'implementer', 'kind': 'agent', 'cli': 'claude-code'}
        self.invalid('at least one human and one agent', participants=[human])
        self.invalid('must have given consent', participants=[dict(human, consent=False), agent])
        self.invalid('unknown CLI', participants=[dict(human, cli='notepad'), agent])
        self.invalid('two humans and two supported CLIs', context='team', participants=[human, agent])
        self.invalid('two humans and two supported CLIs', context='team',
                     participants=[human, dict(human, role='developer'), agent])
        release.validate_pilot(fixture_pilot('team-ok', 'team', 'x'))


class ReadinessTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='harness-release-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve() / 'repo'
        self.write(release.SPEC_TASKS, TASKS)
        self.write(capabilities.DOCUMENT, capabilities.render())
        self.write('src/app.py', 'print(1)\n')
        self.git('init', '-q')
        self.code = self.commit('candidate code')
        self.write_json('docs/pilots/small.json', fixture_pilot('small-one', 'small-team', 'Importer feature.'))
        self.write_json('docs/pilots/team.json', fixture_pilot('team-one', 'team', 'Billing migration.'))
        self.ci(self.code)
        self.commit('evidence')

    def git(self, *args):
        env = {k: v for k, v in os.environ.items() if not k.startswith('GIT_')}
        result = subprocess.run(['git', '-C', str(self.root), '-c', 'user.name=Fixture',
                                 '-c', 'user.email=fixture@example.invalid', '-c', 'commit.gpgsign=false',
                                 '-c', 'core.hooksPath=/dev/null'] + list(args), env=env, text=True,
                                capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout.strip()

    def commit(self, message):
        self.git('add', '-A')
        self.git('commit', '-q', '-m', message)
        return self.git('rev-parse', 'HEAD')

    def write(self, relative, text):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)

    def write_json(self, relative, value):
        self.write(relative, json.dumps(value, indent=2) + '\n')

    def ci(self, revision, **results):
        matrix = {name: 'success' for name in release.schema()['release']['ci_matrix']}
        matrix.update(results)
        self.write_json('releases/1.0.0/ci.json', {'revision': revision, 'results': matrix,
                                                   'run_reference': 'fixture run'})

    def missing(self):
        return release.readiness(self.root, '1.0.0')['missing']

    def assert_gap(self, text):
        self.assertTrue(any(text in item for item in self.missing()), self.missing())


class ReadinessTests(ReadinessTest):
    def test_complete_evidence_is_ready_and_nothing_is_published(self):
        report = release.readiness(self.root, '1.0.0')
        self.assertEqual((report['status'], report['missing']), ('ready', []))
        self.assertIn('explicit authorization', report['publication'])
        self.assertEqual(self.git('tag'), '')
        code = release.main(['--root', str(self.root), 'readiness', '1.0.0', '--write'])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads((self.root / 'releases/1.0.0/readiness.json').read_text())['status'], 'ready')
        self.assertEqual(self.git('tag'), '')
        self.assertEqual(release.readiness(self.root, '1.0.0')['status'], 'ready')

    def test_missing_pilots_leave_a_release_candidate_with_the_gaps_named(self):
        (self.root / 'docs/pilots/team.json').unlink()
        report = release.readiness(self.root, '1.0.0')
        self.assertEqual(report['status'], 'release-candidate')
        self.assert_gap('no reviewed real pilot report for the team context')
        self.assertEqual(release.main(['--root', str(self.root), 'readiness', '1.0.0']), 1)

    def test_synthetic_and_invalid_reports_never_count(self):
        self.write_json('docs/pilots/team.json', dict(fixture_pilot('team-one', 'team', 'x'), kind='synthetic'))
        self.assert_gap('no reviewed real pilot report for the team context')
        broken = fixture_pilot('team-one', 'team', 'x')
        broken['human_review']['reviewed'] = False
        self.write_json('docs/pilots/team.json', broken)
        self.assert_gap('team.json is invalid: the report has not been reviewed by a human')
        self.write('docs/pilots/team.json', '{not json')
        self.assert_gap('team.json is invalid')

    def test_two_pilots_must_describe_distinct_work(self):
        self.write_json('docs/pilots/team.json', fixture_pilot('team-one', 'team', 'Importer feature.'))
        self.assert_gap('distinct work')

    def test_unchecked_milestone_task_blocks(self):
        self.write(release.SPEC_TASKS, TASKS.replace('- [x] **T19**', '- [ ] **T19**'))
        self.assert_gap('milestone tasks not checked: T19')

    def test_ci_must_be_green_on_every_combination_for_the_candidate(self):
        self.ci(self.code, **{'macos-latest/3.10': 'failure'})
        self.assert_gap('CI did not succeed on macos-latest/3.10')
        (self.root / 'releases/1.0.0/ci.json').unlink()
        self.assert_gap('ci.json not found')
        self.ci('0' * 40)
        self.assert_gap('CI evidence')
        self.ci(self.code)
        self.write('src/app.py', 'print(2)\n')
        self.commit('code changed after CI')
        self.assert_gap('code changed after the CI run')

    def test_stale_matrix_and_uncommitted_code_block(self):
        self.write(capabilities.DOCUMENT, 'stale\n')
        self.assert_gap('compatibility matrix document is out of date')
        self.write('src/new.py', 'x = 1\n')
        self.assert_gap('uncommitted changes outside evidence paths')
        self.assert_gap('src/new.py')

    def test_open_blocker_is_not_waived_by_its_severity_label(self):
        defect = {'id': 'D-1', 'summary': 'update overwrote a user file', 'category': 'data-loss',
                  'status': 'open', 'severity': 'minor'}
        self.write_json('releases/1.0.0/defects.json', [defect])
        report = release.readiness(self.root, '1.0.0')
        self.assertEqual(report['unresolved_blockers'], 1)
        self.assert_gap('unresolved release blocker: update overwrote a user file (data-loss)')
        self.write_json('releases/1.0.0/defects.json', [dict(defect, status='resolved')])
        self.assert_gap('resolved defect without a disposition')
        self.write_json('releases/1.0.0/defects.json',
                        [dict(defect, status='resolved', disposition='fixed in abc123, test added')])
        self.assertEqual(self.missing(), [])
        self.write_json('releases/1.0.0/defects.json', [{'summary': 'x', 'status': 'unknown'}])
        self.assert_gap('malformed entry')

    def test_pilot_blocker_issue_blocks(self):
        report = fixture_pilot('team-one', 'team', 'Billing migration.')
        report['unresolved_issues'] = [{'summary': 'rollback left a stale file', 'severity': 'blocker'}]
        self.write_json('docs/pilots/team.json', report)
        self.assert_gap('unresolved release blocker: pilot team-one: rollback left a stale file')


class RepositoryStateTests(unittest.TestCase):
    def test_this_repository_is_a_release_candidate_and_says_why(self):
        report = release.readiness(ROOT, '1.0.0')
        self.assertEqual(report['status'], 'release-candidate')
        self.assertTrue(any('no reviewed real pilot report' in item for item in report['missing']))

    def test_commands_are_dispatched(self):
        env = {k: v for k, v in os.environ.items() if not k.startswith('GIT_') and k != 'ROOT_DIR'}
        ok = subprocess.run([str(ROOT / '.agents/bootstrap.sh'), 'pilot-validate',
                             'docs/pilots/example-synthetic.json'], text=True, capture_output=True,
                            env=env, cwd=str(ROOT))
        self.assertEqual(ok.returncode, 0, ok.stderr)
        self.assertIn('never counts as a real pilot', ok.stdout)
        ready = subprocess.run([str(ROOT / '.agents/bootstrap.sh'), 'release-readiness', '1.0.0'],
                               text=True, capture_output=True, env=env, cwd=str(ROOT))
        self.assertEqual(ready.returncode, 1)
        self.assertIn('release-candidate', ready.stdout)


if __name__ == '__main__':
    unittest.main()
