"""Disposable Git repositories for M3 tests. All approvals here are synthetic."""
import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
LIB = ROOT / '.agents/lib'
sys.path.insert(0, str(LIB))

import team_policy  # noqa: E402
import workflow_ops as ops  # noqa: E402

BOOTSTRAP = ROOT / '.agents/bootstrap.sh'
REQUIREMENTS = '# Requirements\n\n### R1 — First\nWHEN x, the system SHALL y.\n\n### R2 — Second\nWHEN a, the system SHALL b.\n'
TASKS = '# Tasks\n\n- [ ] **T1** — Build it _(R1)_\n- [ ] **T2** — Test it _(R2)_\n'
TEST_SOURCE = ('import unittest\n\n\nclass Sample(unittest.TestCase):\n    def test_one(self):\n        pass\n\n'
               '    def helper(self):\n        pass\n\n\ndef test_two():\n    pass\n\n\ndef helper():\n    pass\n')
ACTIVE_POLICY = '.agents/team-policy.json'
SCENARIO_PATH = 'docs/team-policy/scenarios.json'
DECISION_PATH = 'progress/fixture-scenario-decision.json'


def clean_env():
    env = {key: value for key, value in os.environ.items() if not key.startswith('GIT_')}
    env.pop('ROOT_DIR', None)
    return env


class WorkflowTest(unittest.TestCase):
    """A policy-enabled repository with feature FEAT-A in spec_ready."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='harness-m3-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve() / 'repo'
        self.root.mkdir()
        self.policy = json.loads((ROOT / 'docs/team-policy/example.json').read_text())
        self.build()
        self.git('init', '-q')
        self.commit('initial')

    # --- primitive helpers -------------------------------------------------
    def git(self, *args):
        base = ['git', '-C', str(self.root), '-c', 'user.name=Fixture',
                '-c', 'user.email=fixture@example.invalid', '-c', 'commit.gpgsign=false',
                '-c', 'core.hooksPath=/dev/null']
        result = subprocess.run(base + list(args), env=clean_env(), text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return result.stdout.strip()

    def commit(self, message='change'):
        self.git('add', '-A')
        self.git('commit', '-q', '--allow-empty', '-m', message)
        return self.head()

    def head(self):
        return self.git('rev-parse', 'HEAD')

    def write(self, relative, content):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding='utf-8')
        return path

    def write_json(self, relative, value):
        return self.write(relative, json.dumps(value, indent=2) + '\n')

    def read_json(self, relative):
        return json.loads((self.root / relative).read_text(encoding='utf-8'))

    # --- fixture content ---------------------------------------------------
    def feature(self, identifier, name, status, sdd=True):
        return {'id': identifier, 'name': name, 'status': status, 'sdd': sdd}

    def build(self):
        self.write_json('.agents/agentic.json', {'team_policy': ACTIVE_POLICY,
                                                 'team_policy_scenarios': SCENARIO_PATH})
        self.write_json(ACTIVE_POLICY, self.policy)
        self.write_json('feature_list.json', {'rules': {'maxConcurrent': 1}, 'features': [
            self.feature('FEAT-A', 'feat-a', 'spec_ready'),
            self.feature('FEAT-B', 'feat-b', 'pending')]})
        for name in ('feat-a', 'feat-b'):
            self.write('specs/{}/requirements.md'.format(name), REQUIREMENTS)
            self.write('specs/{}/design.md'.format(name), '# Design for {}\n'.format(name))
            self.write('specs/{}/tasks.md'.format(name), TASKS)
        self.write('tests/test_sample.py', TEST_SOURCE)
        self.write('check.sh', '#!/bin/sh\nexit 0\n').chmod(0o755)
        self.write_scenarios()

    def write_scenarios(self):
        scenarios = json.loads((ROOT / SCENARIO_PATH).read_text())
        for scenario in scenarios:
            scenario['human_review'] = {'role': 'maintainer', 'accepted': True,
                                        'evidence_ref': DECISION_PATH}
        self.write_json(SCENARIO_PATH, scenarios)
        self.write_json(DECISION_PATH, {
            'feature_id': 'FEAT-A', 'scenario_ids': [s['id'] for s in scenarios],
            'accepted_decisions_sha256': team_policy.scenario_decisions_digest(scenarios),
            'assurance': 'SYNTHETIC FIXTURE, not provider-authenticated'})

    # --- workflow helpers --------------------------------------------------
    def init_record(self, feature='FEAT-A'):
        return ops.create_record(self.root, feature, 'agent-session', 'feat/a', None)

    def approve(self, feature='FEAT-A'):
        return ops.record_approval(self.root, feature, 'Dana Reviewer', 'maintainer', 'chat-ref')

    def ready(self):
        """Advance FEAT-A to in_progress through the real operations."""
        self.init_record()
        self.approve()
        ops.mutate_transition(self.root, 'FEAT-A', 'in_progress')

    def record(self, name='feat-a'):
        return self.read_json('progress/work/{}.json'.format(name))

    def save_record(self, record, name='feat-a'):
        self.write_json('progress/work/{}.json'.format(name), record)

    def finish_tasks(self, name='feat-a'):
        path = self.root / 'specs/{}/tasks.md'.format(name)
        path.write_text(path.read_text().replace('- [ ]', '- [x]'), encoding='utf-8')

    def ready_for_closure(self):
        """Reach a state where only the done transition remains."""
        self.ready()
        self.finish_tasks()
        self.commit('complete candidate')
        for requirement, symbol in (('R1', 'Sample::test_one'), ('R2', 'test_two')):
            ops.add_evidence(self.root, 'FEAT-A', {
                'requirement_id': requirement, 'kind': 'automated',
                'source': 'tests/test_sample.py::' + symbol, 'result': 'passed',
                'check_command': 'python3 -m unittest'})
        ops.run_checks(self.root, 'FEAT-A')
        ops.record_review(self.root, 'FEAT-A', 'Dana Reviewer', 'human-reviewer', 'approved', 'review-ref')

    def assert_rejected(self, pattern, function, *args, **kwargs):
        with self.assertRaisesRegex(ValueError, pattern):
            function(*args, **kwargs)

    def bootstrap(self, *args, root=None):
        env = dict(clean_env(), ROOT_DIR=str(root or self.root))
        return subprocess.run([str(BOOTSTRAP)] + [str(arg) for arg in args], env=env, text=True,
                              capture_output=True)

    def copy_record(self, **changes):
        record = copy.deepcopy(self.record())
        record.update(changes)
        return record

    def snapshot(self):
        return {relative: (self.root / relative).read_bytes()
                for relative in ('feature_list.json', 'progress/work/feat-a.json')
                if (self.root / relative).exists()}
