"""R15/T13: read-only provider client, transport hardening, and workflow trust boundary.

HTTP is mocked or served from 127.0.0.1; no request reaches GitHub.
"""
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
from pathlib import Path
import re
import sys
import threading
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.agents/lib'))

import github_api  # noqa: E402

TOKEN = 'ghs_secret_value_123'
BASE = 'https://api.github.com/repos/example-org/example-repo'


class FakeTransport(object):
    def __init__(self, responses):
        self.responses, self.requests = list(responses), []

    def get(self, url, headers, secret_headers):
        self.requests.append((url, headers, secret_headers))
        status, body, extra = self.responses.pop(0)
        return status, dict(extra), body if isinstance(body, bytes) else json.dumps(body).encode()


def client(*responses):
    transport = FakeTransport(responses)
    return github_api.GitHubClient(TOKEN, 'example-org/example-repo', transport), transport


class ClientTests(unittest.TestCase):
    def test_fixed_endpoint_headers_and_secret_header(self):
        api, transport = client((200, {'number': 5}, {}))
        self.assertEqual(api.pull(5)['number'], 5)
        url, headers, secret = transport.requests[0]
        self.assertEqual(url, BASE + '/pulls/5')
        self.assertEqual(headers['X-GitHub-Api-Version'], github_api.API_VERSION)
        self.assertEqual(headers['Accept'], 'application/vnd.github+json')
        self.assertEqual(secret, {'Authorization': 'Bearer ' + TOKEN})
        self.assertNotIn(TOKEN, repr(api))

    def test_reviews_follow_link_pagination(self):
        page2 = BASE + '/pulls/5/reviews?per_page=100&page=2'
        api, transport = client((200, [{'id': 1}], {'link': '<{}>; rel="next", <{}>; rel="last"'.format(page2, page2)}),
                                (200, [{'id': 2}], {'link': '<{}>; rel="prev"'.format(page2)}))
        self.assertEqual([item['id'] for item in api.reviews(5)], [1, 2])
        self.assertEqual(transport.requests[0][0], BASE + '/pulls/5/reviews?per_page=100')
        self.assertEqual(transport.requests[1][0], page2)

    def test_repository_id_style_next_link_on_same_origin_is_followed(self):
        api, _ = client((200, [{'id': 1}], {'link': '<https://api.github.com/repositories/9/pulls/5/reviews?page=2>; rel="next"'}),
                        (200, [], {}))
        self.assertEqual(len(api.reviews(5)), 1)

    def test_next_link_to_another_origin_is_refused(self):
        for target in ('https://evil.example/steal', 'http://api.github.com/x', 'https://user@api.github.com/x'):
            with self.subTest(target):
                api, transport = client((200, [{'id': 1}], {'link': '<{}>; rel="next"'.format(target)}))
                with self.assertRaisesRegex(github_api.ProviderError, 'another origin'):
                    api.reviews(5)
                self.assertEqual(len(transport.requests), 1)

    def test_pagination_is_bounded(self):
        link = {'link': '<{}/pulls/5/reviews?page=2>; rel="next"'.format(BASE)}
        api, _ = client(*[(200, [], link)] * github_api.MAX_PAGES)
        with self.assertRaisesRegex(github_api.ProviderError, 'pagination exceeded'):
            api.reviews(5)

    def test_status_codes_map_to_fail_closed_errors(self):
        cases = ((401, {'message': 'Bad credentials'}, {}, github_api.ProviderAuthError, 'rejected the token'),
                 (403, {'message': 'Resource not accessible by integration'}, {}, github_api.ProviderAuthError,
                  'lacks read permission'),
                 (403, {'message': 'API rate limit exceeded'}, {'x-ratelimit-remaining': '0'},
                  github_api.ProviderUnavailable, 'rate limit'),
                 (429, {}, {}, github_api.ProviderUnavailable, 'rate limit'),
                 (404, {'message': 'Not Found'}, {}, github_api.ProviderUnavailable, 'not visible'),
                 (502, b'<html>', {}, github_api.ProviderUnavailable, 'unavailable'),
                 (302, {}, {}, github_api.ProviderError, 'unexpected'))
        for status, body, headers, error, pattern in cases:
            with self.subTest(status=status, pattern=pattern):
                api, _ = client((status, body, headers))
                with self.assertRaisesRegex(error, pattern):
                    api.pull(5)

    def test_token_never_appears_in_errors(self):
        api, _ = client((401, {'message': 'token {} is bad'.format(TOKEN)}, {}))
        with self.assertRaises(github_api.ProviderAuthError) as raised:
            api.pull(5)
        self.assertNotIn(TOKEN, str(raised.exception))
        self.assertIn('[redacted]', str(raised.exception))

    def test_invalid_or_wrong_shape_json(self):
        for response, pattern in (((200, b'{not json', {}), 'invalid JSON'), ((200, [1], {}), 'non-object')):
            api, _ = client(response)
            with self.subTest(pattern), self.assertRaisesRegex(github_api.ProviderError, pattern):
                api.pull(5)
        api, _ = client((200, {'a': 1}, {}))
        with self.assertRaisesRegex(github_api.ProviderError, 'non-array'):
            api.reviews(5)

    def test_missing_or_malformed_token_and_repository(self):
        for token in ('', '  ', 'a b', None, 'x\ny'):
            with self.subTest(token=token), self.assertRaises(github_api.ProviderAuthError):
                github_api.GitHubClient(token, 'o/r', FakeTransport([]))
        for repository in ('o', 'o/r/x', '../x', 'o/r?x', None):
            with self.subTest(repository=repository), self.assertRaises(github_api.ProviderError):
                github_api.GitHubClient(TOKEN, repository, FakeTransport([]))


class _Handler(BaseHTTPRequestHandler):
    seen = []

    def do_GET(self):
        _Handler.seen.append((self.path, self.headers.get('Authorization')))
        if self.path == '/redirect':
            self.send_response(302)
            self.send_header('Location', '/landing')
            self.end_headers()
            return
        body = b'x' * (github_api.MAX_BYTES + 10) if self.path == '/large' else b'{"ok": true}'
        self.send_response(200)
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


class TransportTests(unittest.TestCase):
    """Exercises urllib behavior over loopback HTTP; the client itself only allows https."""

    @classmethod
    def setUpClass(cls):
        cls.server = HTTPServer(('127.0.0.1', 0), _Handler)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.url = 'http://127.0.0.1:{}'.format(cls.server.server_address[1])

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def setUp(self):
        _Handler.seen = []
        self.transport = github_api.UrllibTransport(timeout=5)
        self.transport.opener = github_api.urllib.request.build_opener(github_api._RefuseRedirect())

    def test_redirect_is_refused_and_target_never_contacted(self):
        with self.assertRaisesRegex(github_api.ProviderError, 'redirect refused'):
            self.transport.get(self.url + '/redirect', {}, {'Authorization': 'Bearer ' + TOKEN})
        self.assertEqual([path for path, _ in _Handler.seen], ['/redirect'])

    def test_secret_header_is_sent_once(self):
        status, _headers, body = self.transport.get(self.url + '/ok', {}, {'Authorization': 'Bearer ' + TOKEN})
        self.assertEqual((status, json.loads(body)), (200, {'ok': True}))
        self.assertEqual(_Handler.seen, [('/ok', 'Bearer ' + TOKEN)])

    def test_oversized_response_refused(self):
        with self.assertRaisesRegex(github_api.ProviderError, 'exceeds'):
            self.transport.get(self.url + '/large', {}, {})

    def test_connection_failure_is_unavailable_without_detail_leak(self):
        port = self.server.server_address[1]
        closed = HTTPServer(('127.0.0.1', 0), _Handler)
        dead = 'http://127.0.0.1:{}/x'.format(closed.server_address[1])
        closed.server_close()
        with self.assertRaises(github_api.ProviderUnavailable) as raised:
            self.transport.get(dead, {}, {'Authorization': 'Bearer ' + TOKEN})
        self.assertNotIn(TOKEN, str(raised.exception))
        self.assertNotEqual(port, None)


class WorkflowConfigurationTests(unittest.TestCase):
    """Static trust-boundary checks of the deployed workflow definition."""

    def setUp(self):
        self.text = (ROOT / '.github/workflows/trusted-review.yml').read_text()
        self.body = '\n'.join(line for line in self.text.splitlines() if not line.lstrip().startswith('#'))

    def test_trigger_runs_default_branch_definition_only(self):
        triggers = re.search(r'^on:\n((?:  .*\n)+)', self.body, re.MULTILINE).group(1)
        self.assertRegex(triggers, r'^  pull_request_target:', 'trusted trigger')
        self.assertEqual(re.findall(r'^  (\w+):', triggers, re.MULTILINE), ['pull_request_target'])

    def test_least_privilege_token(self):
        self.assertIn('\npermissions: {}\n', self.body)
        job = re.search(r'    permissions:\n((?:      .*\n)+)', self.body).group(1)
        self.assertEqual(sorted(line.strip() for line in job.splitlines()),
                         ['contents: read', 'pull-requests: read'])
        self.assertNotIn('secrets.', self.body)
        self.assertNotRegex(self.body, r'write')

    def test_never_checks_out_or_runs_pull_request_code(self):
        self.assertNotRegex(self.body, r'github\.event\.pull_request\.(head|merge)')
        self.assertNotIn('refs/pull', self.body)
        self.assertIn('ref: ${{ github.sha }}', self.body)
        self.assertIn('persist-credentials: false', self.body)
        runs = re.findall(r'run: (.*)', self.body)
        self.assertEqual(runs, ['python3 -E -s -B .agents/lib/trusted_verify.py --trusted-ci'])
        self.assertNotRegex(' '.join(runs), r'\$\{\{')

    def test_job_has_no_skip_condition(self):
        self.assertNotRegex(self.body, r'^\s+if:', 'a conditionally skipped job reports success')


if __name__ == '__main__':
    unittest.main()
