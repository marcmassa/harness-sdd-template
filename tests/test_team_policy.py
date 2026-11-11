"""Synthetic policy scenarios; these are not human scenario approvals."""
import copy
import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('team_policy', ROOT / '.agents/lib/team_policy.py')
policy_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(policy_module)


class TeamPolicyTests(unittest.TestCase):
    def setUp(self):
        self.policy = json.loads((ROOT / 'docs/team-policy/example.json').read_text())
        self.work = {
            'author': 'implementing-agent', 'risk': 'lightweight',
            'scope': 'A bounded typo fix', 'risk_rationale': 'No behavioral change',
            'acceptance_evidence': 'synthetic test fixture',
            'closing_reviewer': 'human-reviewer',
            'risk_flags': {key: False for key in policy_module.HIGH_RISK},
        }

    def test_policy_and_lightweight_work(self):
        policy_module.validate_policy(self.policy)
        policy_module.validate_work(self.policy, self.work)

    def test_agent_cannot_approve_scope_merge_or_publication(self):
        for action in policy_module.HUMAN_ONLY:
            with self.assertRaises(ValueError):
                policy_module.authorize(self.policy, action, 'implementing-agent')
            tampered = copy.deepcopy(self.policy)
            tampered['authority'][action].append('implementing-agent')
            with self.assertRaises(ValueError):
                policy_module.validate_policy(tampered)

    def test_lightweight_missing_fields_risk_or_self_review_rejected(self):
        for field in ('scope', 'risk_rationale', 'acceptance_evidence', 'closing_reviewer', 'risk_flags'):
            broken = copy.deepcopy(self.work)
            del broken[field]
            with self.assertRaises(ValueError):
                policy_module.validate_work(self.policy, broken)
        for flag in policy_module.HIGH_RISK:
            broken = copy.deepcopy(self.work)
            broken['risk_flags'][flag] = True
            with self.assertRaises(ValueError):
                policy_module.validate_work(self.policy, broken)
        self.work['author'] = self.work['closing_reviewer']
        with self.assertRaises(ValueError):
            policy_module.validate_work(self.policy, self.work)

    def test_full_sdd_requires_human_spec_approval_and_human_review(self):
        self.work['risk'] = 'full'
        with self.assertRaises(ValueError):
            policy_module.validate_work(self.policy, self.work)
        self.work['approval'] = {'role': 'maintainer', 'evidence_ref': 'synthetic fixture only'}
        policy_module.validate_work(self.policy, self.work)
        self.work['closing_reviewer'] = 'reviewing-agent'
        with self.assertRaises(ValueError):
            policy_module.validate_work(self.policy, self.work)

    def test_exception_must_be_complete_and_human_authorized(self):
        exception = {'reason': 'Synthetic emergency fixture', 'human_authorizer': 'maintainer',
                     'affected_controls': ['review-order'], 'reapproval_decision': 'required'}
        policy_module.validate_exception(self.policy, exception)
        for field in exception:
            broken = dict(exception)
            del broken[field]
            with self.assertRaises(ValueError):
                policy_module.validate_exception(self.policy, broken)
        exception['human_authorizer'] = 'implementing-agent'
        with self.assertRaises(ValueError):
            policy_module.validate_exception(self.policy, exception)

    def test_external_source_cannot_redefine_trust(self):
        self.policy['trust_order'] = ['external_data', 'project_policy', 'approved_spec', 'unapproved_proposal']
        with self.assertRaises(ValueError):
            policy_module.validate_policy(self.policy)

    def test_real_scenarios_are_accepted_and_synthetic_missing_reviews_fail(self):
        scenarios = json.loads((ROOT / 'docs/team-policy/scenarios.json').read_text())
        self.assertTrue(all((s.get('human_review') or {}).get('accepted') is True for s in scenarios))
        policy_module.validate_reviewed_scenarios(self.policy, scenarios)
        synthetic = copy.deepcopy(scenarios)
        for scenario in synthetic:
            scenario['human_review'] = None
        with self.assertRaises(ValueError):
            policy_module.validate_reviewed_scenarios(self.policy, synthetic)
        for scenario in synthetic:
            scenario['human_review'] = {'role': 'maintainer', 'accepted': True,
                                        'evidence_ref': 'SYNTHETIC TEST FIXTURE, NOT REAL APPROVAL'}
        policy_module.validate_reviewed_scenarios(self.policy, synthetic)
        synthetic[0]['human_review']['role'] = 'implementing-agent'
        with self.assertRaises(ValueError):
            policy_module.validate_reviewed_scenarios(self.policy, synthetic)


if __name__ == '__main__':
    unittest.main()
