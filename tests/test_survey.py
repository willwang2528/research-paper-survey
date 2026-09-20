"""Contract tests: evidence gates, conservative merging, API boundaries, secret handling."""
import copy
import importlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import HTTPError

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / 'skills/research-paper-survey/scripts'
sys.path.insert(0, str(SCRIPTS))


class SurveyTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue((SCRIPTS / 'survey_core.py').exists(), 'Survey implementation not created yet')
        self.core = importlib.import_module('survey_core')
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.run = Path(self.tmp.name) / 'run'
        self.core.init_run(self.run, 'LLM agent failure diagnosis', '2025-01-01', '2026-09-20')

    def paper(self, **changes):
        p = {'title': 'A controlled study', 'ids': {'doi': '10.1234/a'},
             'authors': ['Author A'], 'year': 2025, 'url': 'https://example.org/paper',
             'provenance': [{'source': 'fixture'}], 'observations': []}
        p.update(changes)
        return p

    def review(self, work_id):
        ev = {'source_url': 'https://example.org/paper', 'locator': 'Section 3',
              'evidence': 'We study tool-using LLM agents and attribute failures.',
              'rationale': 'The evaluated system is an LLM agent.', 'verdict': 'yes'}
        return {'work_id': work_id, 'decision': 'core', 'reason': 'Direct match',
                'scope_fingerprint': self.core.scope_fingerprint(self.core.read_json(self.run / 'protocol.json')),
                'reviewer': 'fixture-reviewer', 'reviewed_at': '2026-09-20',
                'identity': {'verified': True, 'source_url': 'https://example.org/paper'},
                'fulltext': {'reviewed': True, 'source_url': 'https://example.org/paper', 'version': 'v1'},
                'date_evidence': {'basis': 'first_public', 'date': '2025-06-01',
                                  'source_url': 'https://example.org/paper', 'locator': 'History'},
                'requirements': {'R1': ev}, 'claims': [dict(ev, text='Studies agent failures')],
                'limitations': ['Synthetic evidence fixture, not a real paper']}

    def seed(self):
        papers = self.core.merge_records([self.paper()])
        self.core.write_jsonl(self.run / 'papers.jsonl', papers)
        return papers[0]['work_id']

    def test_init_refuses_overwrite(self):
        with self.assertRaises(ValueError):
            self.core.init_run(self.run, 'Other', '2025-01-01', '2026-01-01')

    def test_invalid_date_window_is_rejected(self):
        with self.assertRaises(ValueError):
            self.core.init_run(Path(self.tmp.name) / 'invalid', 'Other', '2026-01-01', '2025-01-01')

    def test_dedupe_unifies_doi_arxiv_bridge_but_not_same_title(self):
        a = self.paper(ids={'doi': 'https://doi.org/10.1234/A'})
        b = self.paper(ids={'arxiv': '2501.00001v2'})
        bridge = self.paper(ids={'doi': '10.1234/a', 'arxiv': '2501.00001v1'})
        other = self.paper(ids={'doi': '10.1234/other'})
        got = self.core.merge_records([a, b, bridge, other])
        self.assertEqual(len(got), 2)
        self.assertEqual(len(got[0]['provenance']), 3)
        self.assertEqual(got[0]['ids']['arxiv'], '2501.00001')

    def test_core_without_fulltext_is_blocked(self):
        wid = self.seed()
        review = self.review(wid)
        review['fulltext']['reviewed'] = False
        self.core.write_jsonl(self.run / 'reviews.jsonl', [review])
        result = self.core.audit_run(self.run)
        self.assertTrue(any('fulltext' in e for e in result['errors']))

    def test_unknown_requirement_and_missing_claim_evidence_are_blocked(self):
        wid = self.seed()
        r = self.review(wid)
        r['requirements']['R1']['verdict'] = 'unclear'
        r['claims'][0]['evidence'] = ''
        self.core.write_jsonl(self.run / 'reviews.jsonl', [r])
        errors = self.core.audit_run(self.run)['errors']
        self.assertTrue(any('R1' in e for e in errors))
        self.assertTrue(any('claim' in e for e in errors))

    def test_out_of_window_and_duplicate_reviews_are_blocked(self):
        wid = self.seed()
        r = self.review(wid)
        r['date_evidence']['date'] = '2024-12-31'
        self.core.write_jsonl(self.run / 'reviews.jsonl', [r, r])
        errors = self.core.audit_run(self.run)['errors']
        self.assertTrue(any('date' in e for e in errors))
        self.assertTrue(any('duplicate' in e for e in errors))

    def test_coverage_and_unreviewed_papers_prevent_ready_status(self):
        self.seed()
        result = self.core.audit_run(self.run)
        self.assertFalse(result['ready'])
        self.assertTrue(any('unreviewed' in e for e in result['errors']))
        self.assertTrue(any('coverage' in e for e in result['errors']))

    def test_structurally_complete_review_can_pass_without_claiming_truth(self):
        wid = self.seed()
        self.core.write_jsonl(self.run / 'reviews.jsonl', [self.review(wid)])
        cov = self.core.read_json(self.run / 'coverage.json')
        for check in cov['checks']:
            check.update(status='done', evidence='fixture inspection record')
        self.core.write_json(self.run / 'coverage.json', cov)
        audit = self.core.audit_run(self.run)
        self.assertTrue(audit['ready'], audit['errors'])
        self.assertFalse(audit['semantic_truth_verified_by_script'])

    def test_report_discloses_pending_records(self):
        self.seed()
        self.core.render_report(self.run)
        text = (self.run / 'report.md').read_text()
        self.assertIn('DRAFT', text)
        self.assertIn('A controlled study', text)
        self.assertIn('pending', text)

    def test_null_and_nonstring_evidence_cannot_pass(self):
        wid = self.seed()
        for invalid in (None, False, [], {}, 123):
            r = self.review(wid)
            r['requirements']['R1']['evidence'] = invalid
            r['claims'][0]['locator'] = invalid
            self.core.write_jsonl(self.run / 'reviews.jsonl', [r])
            errors = self.core.audit_run(self.run)['errors']
            self.assertTrue(any('R1' in e for e in errors), invalid)
            self.assertTrue(any('claim' in e for e in errors), invalid)

    def test_scope_change_invalidates_old_review_and_coverage(self):
        wid = self.seed()
        self.core.write_jsonl(self.run / 'reviews.jsonl', [self.review(wid)])
        p = self.core.read_json(self.run / 'protocol.json')
        p['requirements'][0]['description'] = 'Actually only randomized clinical trials'
        self.core.write_json(self.run / 'protocol.json', p)
        errors = self.core.audit_run(self.run)['errors']
        self.assertTrue(any('scope fingerprint' in e for e in errors))
        self.assertTrue(any('coverage: protocol fingerprint' in e for e in errors))

    def test_unexecuted_planned_query_blocks_audit(self):
        p = self.core.read_json(self.run / 'protocol.json')
        p['queries'] = [{'id': 'never-run', 'provider': 's2', 'query': 'agents', 'limit': 1}]
        self.core.write_json(self.run / 'protocol.json', p)
        errors = self.core.audit_run(self.run)['errors']
        self.assertTrue(any('never-run' in e for e in errors))

    def test_latest_failure_is_retried_after_historical_success(self):
        p = self.core.read_json(self.run / 'protocol.json')
        p['queries'] = [{'id': 'Q1', 'provider': 's2', 'query': 'agents', 'limit': 1}]
        self.core.write_json(self.run / 'protocol.json', p)
        good = ([self.paper()], {'status': 'ok', 'truncated': False})
        bad = ([], {'status': 'failed', 'truncated': True, 'error': 'fixture failure'})
        with patch.object(self.core, 'search_s2', side_effect=[good, bad, good]):
            self.core.search_run(self.run, {})
            self.core.search_run(self.run, {}, refresh=True)
            result = self.core.search_run(self.run, {})
        self.assertEqual(result['searched'], 1)
        self.assertEqual(result['failed'], 0)

    def test_prepare_does_not_overwrite_existing_reviews(self):
        wid = self.seed()
        review = self.review(wid)
        self.core.write_jsonl(self.run / 'reviews.jsonl', [review])
        before = (self.run / 'reviews.jsonl').read_bytes()
        data = self.core.prepare_run(self.run)
        self.assertEqual((self.run / 'reviews.jsonl').read_bytes(), before)
        self.assertEqual(data['unreviewed'], 0)
        self.assertTrue((self.run / 'coverage_template.json').exists())

    def test_env_file_is_data_not_shell_and_environment_wins(self):
        path = Path(self.tmp.name) / 'keys.env'
        marker = Path(self.tmp.name) / 'should-not-exist'
        path.write_text('SEMANTIC_SCHOLAR_API_KEY="from-file"\nOTHER=$(touch ' + str(marker) + ')\n')
        with patch.dict(os.environ, {'SEMANTIC_SCHOLAR_API_KEY': 'from-env'}, clear=True):
            self.assertEqual(self.core.load_credentials(path)['s2'], 'from-env')
        self.assertFalse(marker.exists())

    def test_import_creates_unreviewed_records_and_provenance(self):
        inp = Path(self.tmp.name) / 'records.json'
        inp.write_text(json.dumps([self.paper()]))
        self.core.import_records(self.run, inp, 'official-proceedings')
        records = self.core.read_jsonl(self.run / 'papers.jsonl')
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]['provenance'][-1]['source'], 'official-proceedings')
        self.assertEqual(self.core.read_jsonl(self.run / 'reviews.jsonl'), [])


class ProviderTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue((SCRIPTS / 'providers.py').exists(), 'Providers implementation not created yet')
        self.p = importlib.import_module('providers')

    def test_relevance_rejects_boolean_syntax(self):
        with self.assertRaises(ValueError):
            self.p.search_s2(None, {'query': 'agent AND failure', 'mode': 'relevance', 'limit': 10}, 2025, 2026)

    def test_s2_pagination_obeys_limit_and_reports_truncation(self):
        class FixtureHTTP:
            def __init__(self): self.calls = []
            def get(self, url, params, provider):
                self.calls.append(dict(params))
                if len(self.calls) == 1:
                    return {'total': 5, 'next': 2, 'data': [{'paperId': 'p1', 'title': 'One'}, {'paperId': 'p2', 'title': 'Two'}]}
                return {'total': 5, 'next': 4, 'data': [{'paperId': 'p3', 'title': 'Three'}, {'paperId': 'p4', 'title': 'Four'}]}
        http = FixtureHTTP()
        rows, meta = self.p.search_s2(http, {'query': 'agent failure', 'limit': 3}, 2025, 2026)
        self.assertEqual(len(rows), 3)
        self.assertEqual(http.calls[1]['offset'], 2)
        self.assertTrue(meta['truncated'])
        self.assertEqual(meta['retrieved_count'], 4)

    def test_bulk_uses_token_and_its_own_query_syntax(self):
        class FixtureHTTP:
            def __init__(self): self.calls = []
            def get(self, url, params, provider):
                self.calls.append((url, dict(params)))
                return {'total': 2, 'data': [{'paperId': 'p' + str(len(self.calls)), 'title': 'T'}],
                        **({'token': 'next-page'} if len(self.calls) == 1 else {})}
        h = FixtureHTTP()
        rows, meta = self.p.search_s2(h, {'query': 'agent + (failure | debugging)', 'mode': 'bulk', 'limit': 10}, 2025, 2026)
        self.assertEqual(len(rows), 2)
        self.assertEqual(h.calls[1][1]['token'], 'next-page')
        self.assertNotIn('limit', h.calls[0][1])
        self.assertFalse(meta['truncated'])

    def test_malformed_later_page_preserves_previous_records(self):
        class FixtureHTTP:
            def __init__(self): self.n = 0
            def get(self, url, params, provider):
                self.n += 1
                return {'total': 2, 'next': 1, 'data': [{'paperId': 'valid', 'title': 'Retain me'}]} if self.n == 1 else {'total': 2, 'data': [None]}
        rows, meta = self.p.search_s2(FixtureHTTP(), {'query': 'agents', 'limit': 5}, 2025, 2026)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['title'], 'Retain me')
        self.assertEqual(meta['status'], 'partial')

    def test_arxiv_retains_first_public_and_version_date(self):
        xml = b'''<feed xmlns="http://www.w3.org/2005/Atom" xmlns:o="http://a9.com/-/spec/opensearch/1.1/">
        <o:totalResults>1</o:totalResults><entry><id>http://arxiv.org/abs/2501.00001v2</id>
        <title>Agent failures</title><published>2025-01-01T00:00:00Z</published><updated>2026-01-02T00:00:00Z</updated>
        <summary>Study</summary><author><name>A</name></author><link title="pdf" href="https://arxiv.org/pdf/2501.00001v2"/></entry></feed>'''
        class FixtureHTTP:
            def get(self, url, params, provider):
                self.params = params
                return xml
        h = FixtureHTTP()
        rows, _ = self.p.search_arxiv(h, {'query': 'ti:agent AND abs:failure', 'limit': 10}, 2025, 2026)
        self.assertEqual(rows[0]['first_public_date'], '2025-01-01')
        self.assertEqual(rows[0]['updated_date'], '2026-01-02')
        self.assertIn('v2', rows[0]['url'])
        self.assertIn('ti:agent AND abs:failure', h.params['search_query'])

    def test_http_does_not_leak_key_in_failure_or_log(self):
        with tempfile.TemporaryDirectory() as t:
            secret = 'fixture-very-secret-key'
            err = HTTPError('https://api.semanticscholar.org/x', 401, secret, {}, io.BytesIO(secret.encode()))
            http = self.p.HTTPClient(Path(t), {'s2': secret}, retries=0, interval=0)
            with patch('urllib.request.OpenerDirector.open', side_effect=err):
                with self.assertRaises(self.p.ProviderError) as raised:
                    http.get('https://api.semanticscholar.org/graph/v1/paper/search', {'query': 'agents'}, 's2')
            self.assertNotIn(secret, str(raised.exception))
            for f in Path(t).rglob('*'):
                if f.is_file(): self.assertNotIn(secret, f.read_text(errors='replace'))

    def test_openalex_bad_second_page_keeps_first_page(self):
        class FixtureHTTP:
            def __init__(self): self.n = 0
            def get(self, url, params, provider):
                self.n += 1
                return {'meta': {'count': 2, 'next_cursor': 'next'}, 'results': [{'id': 'https://openalex.org/W1', 'title': 'Keep this'}]} if self.n == 1 else {'meta': {'count': 2}, 'results': [None]}
        rows, meta = self.p.search_openalex(FixtureHTTP(), {'query': 'agents', 'limit': 5}, 2025, 2026)
        self.assertEqual(len(rows), 1)
        self.assertEqual(meta['status'], 'partial')

    def test_arxiv_invalid_total_is_failed_not_zero_results(self):
        class FixtureHTTP:
            def get(self, url, params, provider):
                return b'<feed xmlns="http://www.w3.org/2005/Atom" xmlns:o="http://a9.com/-/spec/opensearch/1.1/"><o:totalResults>bad</o:totalResults></feed>'
        _, meta = self.p.search_arxiv(FixtureHTTP(), {'query': 'agent', 'limit': 1}, 2025, 2026)
        self.assertEqual(meta['status'], 'failed')

    def test_retry_429_then_success(self):
        class Response:
            def __enter__(self): return self
            def __exit__(self, *a): pass
            def read(self): return b'{"data": []}'
        with tempfile.TemporaryDirectory() as t:
            http = self.p.HTTPClient(Path(t), {}, retries=1, interval=0)
            err = HTTPError('https://api.semanticscholar.org/x', 429, 'limited', {'Retry-After': '0'}, None)
            with patch('urllib.request.OpenerDirector.open', side_effect=[err, Response()]), patch('time.sleep'):
                self.assertEqual(http.get('https://api.semanticscholar.org/graph/v1/paper/search', {}, 's2'), {'data': []})


if __name__ == '__main__':
    unittest.main()
