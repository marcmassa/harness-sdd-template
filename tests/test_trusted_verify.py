"""R15/T13: trusted verifier against a real Git fixture, a mocked provider, and mocked CI.

Provider data is synthetic and shaped like the GitHub REST pull request and
review resources. Nothing here contacts GitHub or runs a workflow.
"""
import contextlib
import copy
import io
import json
from pathlib import Path
import tempfile

from workflow_support import WorkflowTest, ops
import git_state
import github_api
import trusted_verify

REPOSITORY = 'example-org/example-repo'


class FakeClient(object):
    """Stands in for GitHubClient; records which pull requests were requested."""

    def __init__(self, pulls, reviews, error=None):
        self.pulls, self._reviews, self.error, self.calls = pulls, reviews, error, []

    def pull(self, number):
        self.calls.append(('pull', number))
        if self.error:
            raise self.error
        return copy.deepcopy(self.pulls[number])

    def reviews(self, number):
        self.calls.append(('reviews', number))
        return copy.deepcopy(self._reviews.get(number, []))


class TrustedVerifierTest(WorkflowTest):
    def setUp(self):
        super().setUp()
        self.git('branch', '-M', 'main')
        self.policy['review_mode'] = 'repository'
        self.policy['repository_review'] = {'provider': 'github', 'repository': REPOSITORY,
                                            'base_branch': 'main', 'allowed_reviewers': ['dana', 'lee']}
        self.write_json('.agents/team-policy.json', self.policy)
        self.init_record()
        self.base = self.commit('adopt repository review')
        self.git('checkout', '-q', '-b', 'pr-5')
        ops.record_approval(self.root, 'FEAT-A', 'dana', 'maintainer', 'pull/5', 5)
        ops.mutate_transition(self.root, 'FEAT-A', 'in_progress')
        self.head_sha = self.commit('approve and start')
        self.fetched = {5: 'pr-5'}
        self.events = tempfile.TemporaryDirectory(prefix='harness-event-')
        self.addCleanup(self.events.cleanup)

    # --- fixture plumbing ----------------------------------------------------
    def back_to_base(self):
        self.git('checkout', '-q', 'main')

    def pull(self, number=5, head=None, **changes):
        value = {'number': number, 'state': 'open', 'merged': False,
                 'user': {'login': 'author', 'type': 'User'},
                 'head': {'sha': head or self.head_sha, 'ref': 'pr-5', 'repo': {'full_name': 'fork/repo'}},
                 'base': {'ref': 'main', 'sha': self.base, 'repo': {'full_name': REPOSITORY}}}
        value.update(changes)
        return value

    def review(self, login='dana', commit=None, state='APPROVED', when='2026-11-10T10:00:00Z', kind='User'):
        return {'user': {'login': login, 'type': kind}, 'state': state,
                'commit_id': commit or self.head_sha, 'submitted_at': when}

    def environ(self, **changes):
        event = {'pull_request': {'number': 5, 'head': {'sha': self.head_sha}},
                 'repository': {'full_name': REPOSITORY, 'default_branch': 'main'}}
        path = Path(self.events.name) / 'event.json'
        path.write_text(json.dumps(changes.pop('event', event)))
        value = {'GITHUB_ACTIONS': 'true', 'GITHUB_EVENT_NAME': 'pull_request_target',
                 'GITHUB_REPOSITORY': REPOSITORY, 'GITHUB_TOKEN': 'ghs_fixture_token_value',
                 'GITHUB_EVENT_PATH': str(path), 'GITHUB_SHA': self.base, 'GITHUB_REF': 'refs/heads/main'}
        value.update(changes)
        return {key: item for key, item in value.items() if item is not None}

    def fetcher(self, root, repository, number, token):
        self.assertEqual((repository, token), (REPOSITORY, 'ghs_fixture_token_value'))
        sha = self.git('rev-parse', self.fetched[number])
        self.git('update-ref', 'refs/harness-review/pull/{}'.format(number), sha)
        return sha

    def run_verifier(self, pulls=None, reviews=None, environ=None, client=None):
        self.back_to_base()
        client = client or FakeClient(pulls or {5: self.pull()},
                                      {5: [self.review()]} if reviews is None else reviews)
        return trusted_verify.verify(self.root, environ or self.environ(),
                                     lambda token, repository: client, self.fetcher)

    def assert_verified(self, **kwargs):
        code, result = self.run_verifier(**kwargs)
        self.assertEqual((code, result['result']), (0, 'verified'), result)
        return result

    def assert_rejected_result(self, pattern, expected_code=1, **kwargs):
        code, result = self.run_verifier(**kwargs)
        self.assertEqual(code, expected_code, result)
        self.assertRegex(result.get('error', ''), pattern)
        return result

    def amend_pr(self, change, message='pr change'):
        self.git('checkout', '-q', 'pr-5')
        change()
        self.head_sha = self.commit(message)


class TrustedPathTests(TrustedVerifierTest):
    def test_valid_review_produces_provider_verified_result_bound_to_head(self):
        result = self.assert_verified()
        self.assertEqual(result['candidate'], self.head_sha)
        self.assertEqual(result['assurance'], 'provider-verified')
        feature = result['features'][0]
        self.assertEqual((feature['feature'], feature['gate'], feature['reviewer']),
                         ('FEAT-A', 'spec-approval', 'dana'))
        self.assertEqual(feature['assurance'], 'provider-verified')

    def test_task_marker_update_keeps_approval(self):
        self.amend_pr(lambda: self.finish_tasks())
        self.assert_verified(reviews={5: [self.review()]})

    def test_spec_approval_from_an_earlier_pull_request_with_same_digest(self):
        approved_commit = self.head_sha
        self.amend_pr(lambda: self.write('src/feature.py', 'x = 1\n'), 'implementation')
        record = self.record()
        record['approval']['pull_request'] = 3
        self.amend_pr(lambda: self.save_record(record), 'approval came from PR 3')
        self.fetched[3] = approved_commit
        pulls = {5: self.pull(), 3: self.pull(3, head=approved_commit, state='closed', merged=True)}
        result = self.assert_verified(pulls=pulls, reviews={5: [self.review('lee')],
                                                            3: [self.review(commit=approved_commit)]})
        self.assertEqual(result['features'][0]['approval_pull_request'], 3)

    def test_policy_in_local_mode_reports_not_required(self):
        self.back_to_base()
        self.policy['review_mode'] = 'local'
        self.write_json('.agents/team-policy.json', self.policy)
        self.commit('local mode on base')
        code, result = trusted_verify.verify(self.root, self.environ(GITHUB_SHA=self.head()),
                                             lambda *a: self.fail('no provider call'), self.fetcher)
        self.assertEqual((code, result['result']), (0, 'not-required'))


class MissingTrustedContextTests(TrustedVerifierTest):
    def test_each_missing_or_wrong_context_fails_closed(self):
        workspace_event = self.root / 'event.json'
        cases = {'GITHUB_ACTIONS': None, 'GITHUB_EVENT_NAME': 'pull_request', 'GITHUB_TOKEN': None,
                 'GITHUB_EVENT_PATH': str(workspace_event), 'GITHUB_REPOSITORY': 'other/repo',
                 'GITHUB_SHA': self.head_sha}
        for name, value in cases.items():
            with self.subTest(name):
                workspace_event.write_text(json.dumps({'pull_request': {'number': 5}}))
                code, result = self.run_verifier(environ=self.environ(**{name: value}))
                workspace_event.unlink()
                self.assertEqual((code, result['result']), (2, 'missing-trusted-context'), result)

    def test_job_not_running_from_policy_base_branch(self):
        self.assert_rejected_result('base branch', 2, environ=self.environ(GITHUB_REF='refs/heads/pr-5'))

    def test_default_branch_must_be_policy_base_branch(self):
        event = {'pull_request': {'number': 5, 'head': {'sha': self.head_sha}},
                 'repository': {'full_name': REPOSITORY, 'default_branch': 'develop'}}
        self.assert_rejected_result('default branch', 2, environ=self.environ(event=event))

    def test_modified_trusted_checkout_refused(self):
        self.back_to_base()
        self.write('.agents/lib/injected.py', 'print(1)\n')
        code, result = trusted_verify.verify(self.root, self.environ(), lambda *a: None, self.fetcher)
        self.assertEqual(code, 2)
        self.assertIn('local modifications', result['error'])

    def test_cli_requires_explicit_entry_point_and_accepts_no_overrides(self):
        for argv in ([], ['--trusted-ci', '--api-url', 'https://evil.example'], ['--trusted-ci', '--key', 'k'],
                     ['--trusted-ci', '--result', 'progress/x.json']):
            with self.subTest(argv), self.assertRaises(SystemExit) as raised, \
                    contextlib.redirect_stderr(io.StringIO()):
                trusted_verify.main(argv, environ={}, root=self.root)
            self.assertEqual(raised.exception.code, 2)
        self.back_to_base()
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.assertEqual(trusted_verify.main(['--trusted-ci'], environ={}, root=self.root), 2)
        self.assertEqual(json.loads(output.getvalue())['result'], 'missing-trusted-context')


class PullRequestBindingTests(TrustedVerifierTest):
    def test_closed_or_merged_pull_request(self):
        self.assert_rejected_result('not open', pulls={5: self.pull(state='closed')})
        self.assert_rejected_result('not open', pulls={5: self.pull(merged=True)})

    def test_wrong_base_branch_or_repository(self):
        pull = self.pull()
        pull['base']['ref'] = 'release'
        self.assert_rejected_result('protected base branch', pulls={5: pull})
        pull = self.pull()
        pull['base']['repo']['full_name'] = 'attacker/repo'
        self.assert_rejected_result('expected repository', pulls={5: pull})

    def test_head_moved_after_event(self):
        self.assert_rejected_result('head moved', pulls={5: self.pull(head='e' * 40)})

    def test_fetched_objects_must_match_api_head(self):
        self.fetched[5] = 'main'
        self.assert_rejected_result('head moved during verification')

    def test_provider_returned_another_pull_request(self):
        self.assert_rejected_result('different pull request', pulls={5: self.pull(number=6)})

    def test_provider_failure_fails_closed(self):
        for error in (github_api.ProviderUnavailable('provider transport error: timeout'),
                      github_api.ProviderAuthError('provider rejected the token (HTTP 401)')):
            with self.subTest(type(error).__name__):
                client = FakeClient({}, {}, error)
                code, result = self.run_verifier(client=client)
                self.assertEqual((code, result['result']), (1, 'provider-unavailable'))


class ReviewStateTests(TrustedVerifierTest):
    def test_no_review(self):
        self.assert_rejected_result('no allowed human reviewer', reviews={5: []})

    def test_author_bot_unlisted_and_ghost_reviews_do_not_count(self):
        ghost = self.review()
        ghost['user'] = None
        for review in (self.review('author'), self.review(kind='Bot'), self.review('mallory'), ghost):
            with self.subTest(review['user']):
                pulls = {5: self.pull(user={'login': 'dana', 'type': 'User'})} \
                    if review['user'] and review['user']['login'] == 'author' else None
                self.assert_rejected_result('no allowed human reviewer', reviews={5: [review]},
                                            pulls=pulls or {5: self.pull()})

    def test_approval_of_older_commit_is_stale(self):
        self.assert_rejected_result('no allowed human reviewer', reviews={5: [self.review(commit=self.base)]})

    def test_dismissed_approval_does_not_count(self):
        dismissed = self.review(state='DISMISSED')
        self.assert_rejected_result('no allowed human reviewer', reviews={5: [dismissed]})
        self.assert_rejected_result('no allowed human reviewer', reviews={5: [
            self.review(when='2026-11-10T09:00:00Z'), self.review(state='DISMISSED')]})

    def test_outstanding_requested_changes_block(self):
        self.assert_rejected_result('requested changes', reviews={5: [
            self.review(), self.review('lee', state='CHANGES_REQUESTED', when='2026-11-10T11:00:00Z')]})

    def test_comment_after_approval_keeps_decision(self):
        self.assert_verified(reviews={5: [self.review(), self.review(state='COMMENTED',
                                                                     when='2026-11-10T12:00:00Z')]})

    def test_recorded_reviewer_must_be_the_provider_approver(self):
        self.assert_rejected_result('dana has no current provider approval', reviews={5: [self.review('lee')]})

    def test_forged_workspace_attestation_in_candidate_is_ignored(self):
        forged = {'provider': 'github', 'reviewer': 'dana', 'verification_result': 'passed'}
        self.amend_pr(lambda: self.write_json('progress/trusted-review.json', forged))
        self.assert_rejected_result('no allowed human reviewer', reviews={5: []})


class CandidateContentTests(TrustedVerifierTest):
    def test_changed_requirements_need_reapproval(self):
        self.amend_pr(lambda: self.write('specs/feat-a/requirements.md',
                                         self.root.joinpath('specs/feat-a/requirements.md').read_text() + '\n'))
        self.assert_rejected_result('digest is stale', reviews={5: [self.review()]})

    def test_changed_task_text_needs_scope_change(self):
        self.amend_pr(lambda: self.write('specs/feat-a/tasks.md', '# Tasks\n\n- [ ] **T1** — Different\n'))
        self.assert_rejected_result('scope change', reviews={5: [self.review()]})

    def test_local_approval_in_candidate_rejected(self):
        record = self.record()
        record['approval']['review_mode'] = 'local'
        self.amend_pr(lambda: self.save_record(record))
        self.assert_rejected_result('repository approval record', reviews={5: [self.review()]})

    def test_symlinked_spec_artifact_in_candidate_rejected(self):
        def link():
            path = self.root / 'specs/feat-a/design.md'
            path.unlink()
            path.symlink_to('requirements.md')
        self.amend_pr(link)
        self.assert_rejected_result('not a regular file', reviews={5: [self.review()]})

    def test_approval_pr_review_on_commit_with_other_digest_rejected(self):
        record = self.record()
        record['approval']['pull_request'] = 3
        self.amend_pr(lambda: self.save_record(record))
        self.fetched[3] = 'main'
        pulls = {5: self.pull(), 3: self.pull(3, head=self.base, state='closed', merged=True)}
        self.git('checkout', '-q', '-b', 'pr-3', 'main')
        self.write('specs/feat-a/design.md', '# other design\n')
        other = self.commit('other digest')
        self.assert_rejected_result('no current provider approval on PR #3', pulls=pulls, reviews={
            5: [self.review('lee')], 3: [self.review(commit=other)]})


class ClosureTests(TrustedVerifierTest):
    def close_in_pr(self, after_closure=None):
        self.git('checkout', '-q', 'pr-5')
        self.finish_tasks()
        self.commit('complete candidate')
        for requirement, symbol in (('R1', 'Sample::test_one'), ('R2', 'test_two')):
            ops.add_evidence(self.root, 'FEAT-A', {
                'requirement_id': requirement, 'kind': 'automated',
                'source': 'tests/test_sample.py::' + symbol, 'result': 'passed',
                'check_command': 'python3 -m unittest'})
        ops.run_checks(self.root, 'FEAT-A')
        ops.record_review(self.root, 'FEAT-A', 'Dana Reviewer', 'human-reviewer', 'approved', 'pull/5')
        ops.mutate_transition(self.root, 'FEAT-A', 'done')
        if after_closure:
            after_closure()
        self.head_sha = self.commit('close')

    def test_closure_is_verified_against_its_recorded_revision(self):
        self.close_in_pr()
        result = self.assert_verified(reviews={5: [self.review()]})
        self.assertEqual(result['features'][0]['gate'], 'spec-approval-and-closure')

    def test_code_changed_after_closure_evidence_rejected(self):
        self.close_in_pr(lambda: self.write('src/late.py', 'x = 2\n'))
        self.assert_rejected_result('outside workflow state', reviews={5: [self.review()]})

    def test_evidence_naming_missing_test_rejected(self):
        def forge():
            record = self.record()
            record['evidence'][0]['source'] = 'tests/test_sample.py::test_missing'
            self.save_record(record)
        self.close_in_pr(forge)
        self.assert_rejected_result('not found', reviews={5: [self.review()]})

    def test_done_without_record_rejected(self):
        self.close_in_pr(lambda: (self.root / 'progress/work/feat-a.json').unlink())
        self.assert_rejected_result('no work record', reviews={5: [self.review()]})


if __name__ == '__main__':
    import unittest
    unittest.main()
