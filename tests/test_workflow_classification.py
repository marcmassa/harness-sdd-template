"""R8/R9/R16/R17 regressions from the M3 review: exemptions, classification, evidence."""
from workflow_support import WorkflowTest, ops
import evidence


class HistoricalExemptionTests(WorkflowTest):
    """historical_features covers only work already done before team_policy existed."""

    def setUp(self):
        super().setUp()
        manifest = self.read_json('.agents/agentic.json')
        self.write_json('.agents/agentic.json', {})
        data = self.read_json('feature_list.json')
        data['features'].append(self.feature('OLD-1', 'old-1', 'done', sdd=False))
        data['features'].append(self.feature('OLD-2', 'old-2', 'in_progress', sdd=False))
        self.write_json('feature_list.json', data)
        self.baseline = self.commit('before adoption')
        self.write_json('.agents/agentic.json', manifest)
        data['features'][-1]['status'] = 'pending'
        self.write_json('feature_list.json', data)
        self.commit('adopt team policy')

    def historical(self, features, revision=None):
        self.policy['historical_features'] = features
        self.policy['adoption_revision'] = revision or self.baseline
        self.write_json('.agents/team-policy.json', self.policy)

    def test_pre_adoption_done_feature_is_exempt(self):
        self.historical(['OLD-1'])
        self.assertIn('[PASS]', ops.check_repository(self.root))

    def test_codex_probe_historical_feature_in_progress_rejected(self):
        self.historical(['OLD-1'])
        data = self.read_json('feature_list.json')
        data['features'][2]['status'] = 'in_progress'
        self.write_json('feature_list.json', data)
        self.assert_rejected('not done', ops.check_repository, self.root)

    def test_feature_not_done_at_adoption_rejected(self):
        self.historical(['OLD-2'])
        data = self.read_json('feature_list.json')
        data['features'][3]['status'] = 'done'
        self.write_json('feature_list.json', data)
        self.assert_rejected('not done at adoption_revision', ops.check_repository, self.root)

    def test_adoption_revision_after_activation_rejected(self):
        self.historical(['OLD-1'], self.head())
        self.assert_rejected('predate team_policy', ops.check_repository, self.root)

    def test_adoption_revision_must_be_real_ancestor(self):
        self.historical(['OLD-1'], 'a' * 40)
        self.assert_rejected('not a commit', ops.check_repository, self.root)

    def test_historical_listing_requires_adoption_revision(self):
        self.policy['historical_features'] = ['OLD-1']
        self.write_json('.agents/team-policy.json', self.policy)
        self.assert_rejected('adoption_revision', ops.check_repository, self.root)


class LightweightClassificationTests(WorkflowTest):
    def lightweight(self, **changes):
        details = {'scope': 'Typo', 'risk_rationale': 'Docs only', 'author_role': 'implementing-agent',
                   'classified_by': 'maintainer', 'classification_ref': 'decision-1'}
        details.update(changes)
        return details

    def add_fix(self, status='pending', sdd=False):
        data = self.read_json('feature_list.json')
        data['features'].append(self.feature('FIX-1', 'fix-1', status, sdd=sdd))
        self.write_json('feature_list.json', data)
        self.commit('add fix')

    def test_classification_is_a_recorded_human_decision(self):
        self.add_fix()
        ops.create_record(self.root, 'FIX-1', 'agent', 'fix/1', None, (), self.lightweight())
        decision = self.read_json('progress/work/fix-1.json')['lightweight']['classification']
        self.assertEqual((decision['authorized_by'], decision['evidence_ref']), ('maintainer', 'decision-1'))

    def test_agent_or_missing_classifier_rejected(self):
        self.add_fix()
        for changes, pattern in (({'classified_by': 'implementing-agent'}, 'cannot authorize'),
                                 ({'classified_by': None}, 'cannot authorize'),
                                 ({'classification_ref': ''}, 'evidence reference')):
            with self.subTest(changes):
                self.assert_rejected(pattern, ops.create_record, self.root, 'FIX-1', 'a', 'b', None, (),
                                     self.lightweight(**changes))

    def test_retrospective_lightweight_intake_rejected(self):
        self.add_fix(status='in_progress')
        self.assert_rejected('before work starts', ops.create_record, self.root, 'FIX-1', 'a', 'b', None, (),
                             self.lightweight())

    def test_codex_probe_downgrade_of_active_sdd_feature_rejected(self):
        self.ready()
        self.commit('FEAT-A in progress with its record')
        data = self.read_json('feature_list.json')
        data['features'][0].update(sdd=False)
        self.write_json('feature_list.json', data)
        (self.root / 'progress/work/feat-a.json').unlink()
        self.assert_rejected('before work starts|committed work record', ops.create_record, self.root,
                             'FEAT-A', 'a', 'b', None, (), self.lightweight())
        data['features'][0].update(status='pending')
        self.write_json('feature_list.json', data)
        self.assert_rejected('had a committed work record', ops.create_record, self.root, 'FEAT-A', 'a', 'b',
                             None, (), self.lightweight())
        self.assert_rejected('no work record|work record', ops.check_repository, self.root)

    def test_feature_with_spec_artifacts_cannot_be_lightweight(self):
        data = self.read_json('feature_list.json')
        data['features'][1].update(sdd=False)
        self.write_json('feature_list.json', data)
        self.assert_rejected('spec artifacts', ops.create_record, self.root, 'FEAT-B', 'a', 'b', None, (),
                             self.lightweight())

    def test_feature_once_committed_as_sdd_cannot_be_downgraded(self):
        self.add_fix(sdd=True)
        data = self.read_json('feature_list.json')
        data['features'][-1]['sdd'] = False
        self.write_json('feature_list.json', data)
        self.commit('downgrade attempt')
        self.assert_rejected('downgrade to lightweight is refused', ops.create_record, self.root, 'FIX-1',
                             'a', 'b', None, (), self.lightweight())

    def test_hand_written_lightweight_record_without_classification_blocks(self):
        self.add_fix()
        ops.create_record(self.root, 'FIX-1', 'agent', 'fix/1', None, (), self.lightweight())
        record = self.read_json('progress/work/fix-1.json')
        del record['lightweight']['classification']
        self.write_json('progress/work/fix-1.json', record)
        self.assert_rejected('classification decision', ops.mutate_transition, self.root, 'FIX-1', 'in_progress')

    def test_full_record_cannot_be_registered_after_implementation_started(self):
        data = self.read_json('feature_list.json')
        data['features'][0]['status'] = 'in_progress'
        self.write_json('feature_list.json', data)
        self.assert_rejected('before implementation', self.init_record)


class EvidenceSourceTests(WorkflowTest):
    def automated(self, source, revision):
        return {'requirement_id': 'R1', 'kind': 'automated', 'source': source, 'result': 'passed',
                'revision': revision, 'check_command': 'python3 -m unittest'}

    def test_review_probes_are_not_test_sources(self):
        self.write('docs/latest.md', 'test_one passed\n')
        self.write('tests/README.md', 'passed\n')
        self.write('tests/fixtures/x.json', '{"ok": true}\n')
        self.write('tests/sample.spec.js', 'it("ok")\n')
        self.write('tests/helpers.py', 'def test_x():\n    pass\n')
        head = self.commit('non-test sources')
        for source in ('docs/latest.md::test_one', 'tests/README.md::passed', 'tests/fixtures/x.json::ok',
                       'tests/sample.spec.js::ok', 'tests/helpers.py::test_x'):
            with self.subTest(source), self.assertRaisesRegex(ValueError, 'supported test file'):
                evidence.validate_evidence_item(self.automated(source, head), ['R1'], head, self.root)

    def test_supported_sources_and_symbols(self):
        self.write('pkg/thing_test.py', 'def test_thing():\n    pass\n')
        self.write('tests/test_flow.sh', 'test_flow() { true; }\nhelper() { true; }\n')
        head = self.commit('supported sources')
        for source in ('pkg/thing_test.py::test_thing', 'tests/test_flow.sh::test_flow'):
            evidence.validate_evidence_item(self.automated(source, head), ['R1'], head, self.root)
        with self.assertRaisesRegex(ValueError, 'not found'):
            evidence.validate_evidence_item(self.automated('tests/test_flow.sh::helper', head), ['R1'], head,
                                            self.root)

    def test_stale_and_renamed_evidence_is_superseded_not_stuck(self):
        self.ready()
        self.finish_tasks()
        self.commit('candidate')
        old = {'requirement_id': 'R1', 'kind': 'automated', 'source': 'tests/test_sample.py::Sample::test_one',
               'result': 'passed', 'check_command': 'python3 -m unittest'}
        ops.add_evidence(self.root, 'FEAT-A', old)
        path = self.root / 'tests/test_sample.py'
        path.write_text(path.read_text().replace('def test_one', 'def test_renamed'))
        self.commit('rename test')
        renamed = dict(old, source='tests/test_sample.py::Sample::test_renamed')
        self.assertEqual(ops.add_evidence(self.root, 'FEAT-A', renamed)['superseded'], 1)
        record = self.record()
        self.assertEqual([item['source'] for item in record['evidence']], [renamed['source']])
        self.assertEqual(record['superseded_evidence'][0]['source'], old['source'])

    def test_wrong_entry_can_be_removed_with_a_reason(self):
        self.ready()
        self.finish_tasks()
        self.commit('candidate')
        item = {'requirement_id': 'R2', 'kind': 'automated', 'source': 'tests/test_sample.py::test_two',
                'result': 'passed', 'check_command': 'python3 -m unittest'}
        ops.add_evidence(self.root, 'FEAT-A', item)
        self.assert_rejected('reason', ops.remove_evidence, self.root, 'FEAT-A', 'R2', item['source'], '')
        self.assert_rejected('no evidence entry', ops.remove_evidence, self.root, 'FEAT-A', 'R1', 'x', 'why')
        ops.remove_evidence(self.root, 'FEAT-A', 'R2', item['source'], 'wrong requirement')
        record = self.record()
        self.assertEqual(record['evidence'], [])
        self.assertEqual(record['superseded_evidence'][0]['superseded_reason'], 'wrong requirement')


class HiddenTaskTests(WorkflowTest):
    def test_review_probes_block(self):
        for text, pattern in (('- [x] T1 done\n> - [ ] T2 quoted\n', 'unfinished required tasks: T2'),
                              ('- [x] T1 done\n<!-- - [ ] T2 hidden -->\n', 'HTML comments'),
                              ('- [x] T1 done\n<!--\n- [ ] T2\n-->\n', 'HTML comments'),
                              ('- [x] T1 done\n1. T2 do it\n', 'no checkbox'),
                              ('- [x] T1 done\nT2 do it\n', 'no checkbox')):
            with self.subTest(text), self.assertRaisesRegex(ValueError, pattern):
                evidence.validate_tasks(text)

    def test_quoted_finished_tasks_and_plain_comments_pass(self):
        evidence.validate_tasks('- [x] T1 done\n> - [x] T2 quoted\n<!-- editorial note -->\n')


if __name__ == '__main__':
    import unittest
    unittest.main()
