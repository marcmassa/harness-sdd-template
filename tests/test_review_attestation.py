"""R15: local repository mode is pending until trusted CI; local identity is never authentication.

GitHub-shaped dictionaries are captured-format fixtures, not live provider data.
"""
import copy
import hashlib
import hmac
import json

from workflow_support import WorkflowTest, ops
import approval
import provider_review
import workflow

REVISION = 'c' * 40
DIGEST = 'd' * 64
REPOSITORY = 'example-org/example-repo'


def forged_attestation():
    """The shape and self-signature the draft implementation accepted."""
    payload = {'provider': 'github', 'repository': REPOSITORY, 'reviewed_revision': REVISION,
               'spec_digest': DIGEST, 'reviewer': 'Dana Reviewer', 'reviewer_role': 'maintainer',
               'decision': 'approved', 'attested_by': 'trusted-ci', 'verification_result': 'passed'}
    canonical = json.dumps(payload, sort_keys=True, separators=(',', ':')).encode()
    payload['signature'] = 'sha256=' + hmac.new(b'k' * 32, canonical, hashlib.sha256).hexdigest()
    return payload


class RepositoryModeTests(WorkflowTest):
    def use_repository_mode(self):
        self.policy['review_mode'] = 'repository'
        self.policy['repository_review'] = {'provider': 'github', 'repository': REPOSITORY,
                                            'base_branch': 'main', 'allowed_reviewers': ['dana']}
        self.write_json('.agents/team-policy.json', self.policy)

    def local_approval_then_repository_mode(self):
        self.ready()
        self.use_repository_mode()

    def active_feature(self):
        return {'id': 'FEAT-A', 'name': 'feat-a', 'status': 'in_progress', 'sdd': True}

    def context(self, **extra):
        return dict({'root': self.root, 'feature_data': self.read_json('feature_list.json')}, **extra)

    def test_local_approval_cannot_satisfy_required_repository_mode(self):
        self.local_approval_then_repository_mode()
        self.assert_rejected('does not satisfy configured policy', workflow.validate_transition,
                             self.active_feature(), 'in_progress', self.record(), [], self.policy, self.context())

    def test_repository_approval_must_name_pull_request_and_allowed_login(self):
        self.use_repository_mode()
        self.init_record()
        self.assert_rejected('--pull-request', self.approve)
        self.assert_rejected('allowed provider login', ops.record_approval, self.root, 'FEAT-A',
                             'Dana Reviewer', 'maintainer', 'pull/7', 7)
        self.assert_rejected('cannot authorize', ops.record_approval, self.root, 'FEAT-A',
                             'dana', 'implementing-agent', 'pull/7', 7)
        result = ops.record_approval(self.root, 'FEAT-A', 'dana', 'maintainer', 'pull/7', 7)
        self.assertEqual(result['assurance'], approval.PENDING)
        self.assertEqual(self.record()['approval']['pull_request'], 7)

    def test_pull_request_option_refused_in_local_mode(self):
        self.init_record()
        self.assert_rejected('only to repository', ops.record_approval, self.root, 'FEAT-A',
                             'Dana Reviewer', 'maintainer', 'chat-ref', 3)

    def repository_shaped_record(self):
        self.use_repository_mode()
        self.init_record()
        ops.record_approval(self.root, 'FEAT-A', 'dana', 'maintainer', 'pull/7', 7)
        ops.mutate_transition(self.root, 'FEAT-A', 'in_progress')
        return self.record()

    def test_local_validation_is_pending_never_provider_verified(self):
        record = self.repository_shaped_record()
        result = workflow.validate_transition(self.active_feature(), 'in_progress', record, [], self.policy,
                                              self.context())
        self.assertEqual(result['approval']['assurance'], 'pending-trusted-verification')
        self.assertIn('pending-trusted-verification', ops.check_repository(self.root))
        cli = self.bootstrap('workflow-validate', '--feature-id', 'FEAT-A', '--target', 'in_progress')
        self.assertEqual(cli.returncode, 0, cli.stderr)
        self.assertNotIn('provider-verified', cli.stdout)

    def test_hand_edited_repository_record_without_pull_request_rejected(self):
        record = self.repository_shaped_record()
        del record['approval']['pull_request']
        self.save_record(record)
        self.assert_rejected('pull_request number', ops.check_repository, self.root)

    def test_forged_self_signed_workspace_metadata_rejected(self):
        record = self.repository_shaped_record()
        self.write_json('progress/trusted-review.json', forged_attestation())
        self.assert_rejected('required repository review unavailable', workflow.validate_transition,
                             self.active_feature(), 'in_progress', record, [], self.policy,
                             self.context(trusted_review=forged_attestation()))

    def test_cli_exposes_no_way_to_supply_review_metadata(self):
        self.repository_shaped_record()
        self.write_json('progress/trusted-review.json', forged_attestation())
        for option in ('--trusted-review', '--attestation-env', '--record', '--policy', '--api-url'):
            result = self.bootstrap('workflow-validate', '--feature-id', 'FEAT-A', '--target', 'in_progress',
                                    option, 'progress/trusted-review.json')
            self.assertEqual(result.returncode, 2, option)
            self.assertIn('unrecognized arguments', result.stderr)

    def test_policy_without_complete_repository_binding_rejected(self):
        for field in ('repository', 'base_branch', 'allowed_reviewers', 'provider'):
            self.use_repository_mode()
            del self.policy['repository_review'][field]
            with self.subTest(field):
                self.write_json('.agents/team-policy.json', self.policy)
                self.assert_rejected('repository', ops.check_repository, self.root)

    def test_local_mode_reports_declared_assurance(self):
        self.ready()
        result = workflow.validate_transition(self.active_feature(), 'in_progress', self.record(), [], self.policy,
                                              self.context())
        self.assertEqual(result['approval']['assurance'], 'declared-local-decision')

    def contract_record(self):
        return {'approval': {'spec_digest': DIGEST, 'task_digest': 't', 'review_mode': 'repository',
                             'reviewer': 'dana', 'role': 'maintainer', 'evidence_ref': 'pr-1',
                             'pull_request': 1}}

    def test_repository_contract_binds_every_field(self):
        """Only an in-memory verifier result upgrades the label; every field is bound."""
        record = self.contract_record()
        self.use_repository_mode()
        make = provider_review.TrustedRepositoryReview
        good = make('github', REPOSITORY, REVISION, DIGEST, 'dana', 1)
        result = approval.verify_approval(record, DIGEST, self.policy, good, None, REVISION)
        self.assertEqual(result['assurance'], 'provider-verified')
        for bad, expected in ((make('gitlab', REPOSITORY, REVISION, DIGEST, 'dana'), 'provider'),
                              (make('github', 'attacker/fork', REVISION, DIGEST, 'dana'), 'repository'),
                              (make('github', REPOSITORY, 'e' * 40, DIGEST, 'dana'), 'candidate'),
                              (make('github', REPOSITORY, REVISION, 'f' * 64, 'dana'), 'stale'),
                              (make('github', REPOSITORY, REVISION, DIGEST, 'eve'), 'does not match')):
            self.assert_rejected(expected, approval.verify_approval, record, DIGEST, self.policy, bad, None, REVISION)
        self.assert_rejected('candidate', approval.verify_approval, record, DIGEST, self.policy, good, None, None)

    def test_repository_contract_requires_declared_config(self):
        self.policy['review_mode'] = 'repository'
        good = provider_review.TrustedRepositoryReview('github', REPOSITORY, REVISION, DIGEST, 'dana')
        self.assert_rejected('repository_review', approval.verify_approval, self.contract_record(), DIGEST,
                             self.policy, good, None, REVISION)


class CapturedGitHubMetadataTests(WorkflowTest):
    """Pure evaluation of the documented REST shapes; authenticates nothing."""

    def fixtures(self):
        pull = {'user': {'login': 'author'}, 'head': {'sha': REVISION},
                'base': {'repo': {'full_name': REPOSITORY}}}
        reviews = [{'user': {'login': 'dana', 'type': 'User'}, 'state': 'APPROVED', 'commit_id': REVISION,
                    'submitted_at': '2026-11-09T10:00:00Z'}]
        expected = {'repository': REPOSITORY, 'revision': REVISION, 'spec_digest': DIGEST,
                    'reviewer': 'dana', 'allowed_reviewers': ['dana', 'lee']}
        return pull, reviews, expected

    def test_valid_review_produces_in_memory_result(self):
        result = provider_review.evaluate_github_review(*self.fixtures())
        self.assertIsInstance(result, provider_review.TrustedRepositoryReview)
        self.assertEqual((result.revision, result.spec_digest, result.reviewer), (REVISION, DIGEST, 'dana'))

    def rejects(self, pattern, mutate):
        pull, reviews, expected = copy.deepcopy(self.fixtures())
        mutate(pull, reviews, expected)
        self.assert_rejected(pattern, provider_review.evaluate_github_review, pull, reviews, expected)

    def test_wrong_repository(self):
        self.rejects('expected repository', lambda p, r, e: p['base']['repo'].update(full_name='other/repo'))

    def test_head_moved_after_review(self):
        self.rejects('head does not match', lambda p, r, e: p['head'].update(sha='e' * 40))

    def test_review_on_older_commit(self):
        self.rejects('stale revision', lambda p, r, e: r[0].update(commit_id='e' * 40))

    def test_reviewer_not_allowed(self):
        self.rejects('allowed human reviewer', lambda p, r, e: e.update(allowed_reviewers=['lee']))

    def test_author_cannot_self_approve(self):
        self.rejects('author cannot', lambda p, r, e: p['user'].update(login='dana'))

    def test_bot_account_rejected(self):
        self.rejects('human account', lambda p, r, e: r[0]['user'].update(type='Bot'))

    def test_no_approval(self):
        self.rejects('no current approval', lambda p, r, e: r.clear())

    def test_later_dismissal_revokes_approval(self):
        self.rejects('no current approval', lambda p, r, e: r.append(
            {'user': {'login': 'dana', 'type': 'User'}, 'state': 'DISMISSED', 'commit_id': REVISION,
             'submitted_at': '2026-11-09T11:00:00Z'}))

    def test_outstanding_changes_requested_blocks(self):
        self.rejects('requested changes', lambda p, r, e: r.append(
            {'user': {'login': 'lee', 'type': 'User'}, 'state': 'CHANGES_REQUESTED', 'commit_id': REVISION,
             'submitted_at': '2026-11-09T11:00:00Z'}))

    def test_comment_does_not_change_decision(self):
        pull, reviews, expected = self.fixtures()
        reviews.append({'user': {'login': 'dana', 'type': 'User'}, 'state': 'COMMENTED', 'commit_id': REVISION,
                        'submitted_at': '2026-11-09T12:00:00Z'})
        self.assertEqual(provider_review.evaluate_github_review(pull, reviews, expected).reviewer, 'dana')

    def test_review_order_uses_submission_time_not_array_order(self):
        pull, reviews, expected = self.fixtures()
        reviews.insert(0, {'user': {'login': 'dana', 'type': 'User'}, 'state': 'CHANGES_REQUESTED',
                           'commit_id': REVISION, 'submitted_at': '2026-11-09T09:00:00Z'})
        reviews.reverse()
        self.assertEqual(provider_review.evaluate_github_review(pull, reviews, expected).reviewer, 'dana')

    def test_malformed_metadata_fails(self):
        self.rejects('missing', lambda p, r, e: p.pop('head'))


if __name__ == '__main__':
    import unittest
    unittest.main()
