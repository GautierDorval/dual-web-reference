"""Synthetic tests for temporal and evidence boundaries; no network access."""
import gzip
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest

SPEC = importlib.util.spec_from_file_location('cc_annex', Path(__file__).resolve().parents[1]/'scripts/common_crawl_annex.py')
cc = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(cc)
WINDOWS = {'M1':{'start':'2026-09-15T00:00:00Z','end_exclusive':'2026-10-15T00:00:00Z'},
           'M2':{'start':'2026-10-15T00:00:00Z','end_exclusive':'2026-11-15T00:00:00Z'}}
URL = 'https://example.org/llms.txt'
CDX = {'url':URL,'timestamp':'20261015000000','status':'200','digest':'SOURCE_DIGEST'}


def warc(body=b'hello\r\n', kind='response', extra='', status=200, url=URL, date='2026-10-15T00:00:00Z'):
    http = (f'HTTP/1.1 {status} OK\r\nContent-Type: text/plain; charset=utf-8\r\nContent-Length: {len(body)}\r\n\r\n').encode()+body
    head = (f'WARC/1.0\r\nWARC-Type: {kind}\r\nWARC-Target-URI: {url}\r\nWARC-Date: {date}\r\nContent-Length: {len(http)}\r\n'+extra+'\r\n').encode()
    return gzip.compress(head+http+b'\r\n\r\n')


class ArchiveEvidenceTests(unittest.TestCase):
    def test_utc_half_open_windows(self):
        for value, expected in [('20260914235959','outside'),('20260915000000','M1'),
                                ('20261014235959','M1'),('20261015000000','M2'),
                                ('20261114235959','M2'),('20261115000000','outside'),
                                ('2026-10-14T20:00:00-04:00','M2')]:
            with self.subTest(value=value):
                self.assertEqual(cc.window_of(value,WINDOWS),expected)
        with self.assertRaises(ValueError):
            cc.instant('2026-10-15T00:00:00')

    def test_absence_is_not_error_or_empty_body(self):
        self.assertEqual(cc.parse_cdx(404,b'{"message":"No Captures found for: example.org"}',URL),([],True,'no_capture'))
        for status, body in [(404,b'<html>proxy error</html>'),(503,b'Unavailable'),(200,b''),(200,b'not json')]:
            with self.subTest(status=status,body=body):
                self.assertFalse(cc.parse_cdx(status,body,URL)[1])
        rows, complete, _ = cc.parse_cdx(200,json.dumps(CDX).encode(),URL)
        self.assertTrue(complete)
        self.assertEqual(rows,[CDX])
        self.assertFalse(cc.parse_cdx(200,json.dumps(CDX).encode(),URL,False)[1])

    def test_exact_original_url_and_incomplete_limit(self):
        variant = dict(CDX,url='http://example.org/llms.txt')
        self.assertEqual(cc.parse_cdx(200,json.dumps(variant).encode(),URL)[0],[])
        data = ('\n'.join(json.dumps(CDX) for _ in range(cc.LIMIT))).encode()
        self.assertFalse(cc.parse_cdx(200,data,URL)[1])

    def test_complete_response_preserves_bytes_and_normalization(self):
        result, artifacts = cc.inspect_warc(warc(),CDX,WINDOWS)
        self.assertEqual(result['state'],'content_retrieved_comparable')
        self.assertEqual(result['window'],'M2')
        self.assertEqual(artifacts['payload.bin'],b'hello\r\n')
        self.assertEqual(artifacts['normalized.txt'],b'hello\n')
        self.assertEqual(result['decoded_sha256'],cc.digest(b'hello\r\n'))

    def test_repeated_protocol_is_legal_but_duplicate_length_is_not(self):
        raw=warc(extra='WARC-Protocol: h2\r\nWARC-Protocol: tls/1.3\r\n')
        result,_=cc.inspect_warc(raw,CDX,WINDOWS)
        self.assertEqual(result['state'],'content_retrieved_comparable')
        self.assertEqual(result['warc']['warc-protocol'],['h2','tls/1.3'])
        result,_=cc.inspect_warc(warc(extra='Content-Length: 1\r\n'),CDX,WINDOWS)
        self.assertEqual(result['state'],'content_partial_redirect_or_revisit')
        self.assertIn('ambiguous_duplicate_header',result['issues'])

    def test_truncation_revisit_redirect_are_not_comparable(self):
        for raw, issue in [(warc(extra='WARC-Truncated: length\r\n'),'warc_truncated:length'),
                           (warc(kind='revisit'),'revisit_requires_resolution'),
                           (warc(status=301),'http_redirect_not_followed')]:
            with self.subTest(issue=issue):
                result,_ = cc.inspect_warc(raw,CDX,WINDOWS)
                self.assertEqual(result['state'],'content_partial_redirect_or_revisit')
                self.assertIn(issue,result['issues'])

    def test_url_time_mismatch_and_damaged_gzip(self):
        for raw in [warc(url='https://example.org/other'),warc(date='2026-10-14T23:59:59Z'),warc()[:-8]]:
            result,_ = cc.inspect_warc(raw,CDX,WINDOWS)
            self.assertNotEqual(result['state'],'content_retrieved_comparable')
            self.assertTrue(result['issues'])

    def test_expansion_limit(self):
        with self.assertRaisesRegex(ValueError,'expanded_record_limit'):
            cc.bounded_gunzip(gzip.compress(b'x'*(cc.MAX_EXPANDED+1)))

    def test_all_six_states_and_incomplete_coverage_are_separate(self):
        self.assertEqual(cc.window_state([],True,'M2'),'no_capture_in_queried_indexes')
        self.assertEqual(cc.window_state([],False,'M2'),'query_failed_or_incomplete')
        outside={'window':'M1','state':'content_retrieved_comparable'}
        self.assertEqual(cc.window_state([outside],False,'M2'),'capture_only_outside_window')
        for state in ['capture_content_not_retrieved','content_partial_redirect_or_revisit','content_retrieved_comparable']:
            self.assertEqual(cc.window_state([{'window':'M2','state':state}],False,'M2'),state)

    def test_original_source_digests(self):
        self.assertTrue(cc.source_digest_matches(b'abc','sha1:VGMT4NSHA2AWVOR6EVYXQUGCNSONBWE5'))
        self.assertFalse(cc.source_digest_matches(b'changed','sha1:VGMT4NSHA2AWVOR6EVYXQUGCNSONBWE5'))
        self.assertIsNone(cc.source_digest_matches(b'abc',None))

    def test_no_redirects(self):
        self.assertIsNone(cc.NoRedirect().redirect_request(None,None,302,'',{},'https://example.org/'))


class FakeResponse(io.BytesIO):
    def __init__(self,status=200,data=b'ok',headers=None):
        super().__init__(data)
        self.code = status
        self.headers = headers or {}


class FakeOpener:
    def __init__(self,status=200,data=b'ok',headers=None):
        self.status,self.data,self.headers = status,data,headers
        self.calls = 0
    def open(self,*args,**kwargs):
        self.calls += 1
        return FakeResponse(self.status,self.data,self.headers)


class TransportBudgetTests(unittest.TestCase):
    def transport(self,folder,opener,**overrides):
        (folder/'raw').mkdir()
        budget = {'max_index_requests':30,'max_warc_records':20,'max_download_bytes':104857600,'interval_seconds':5}
        budget.update(overrides)
        return cc.Transport(folder,budget,opener=opener,sleeper=lambda _:None)

    def test_rate_limit_stops_without_retry(self):
        for status in (403,429,503):
            with self.subTest(status=status), tempfile.TemporaryDirectory() as temp:
                opener=FakeOpener(status,b'blocked',{'Retry-After':'120'})
                transport=self.transport(Path(temp),opener)
                meta,_=transport.get('https://index.commoncrawl.org/test','index',100)
                self.assertEqual(meta['retry_after'],'120')
                self.assertIsNone(transport.get('https://index.commoncrawl.org/test','index',100))
                self.assertEqual(opener.calls,1)

    def test_request_and_bytes_budgets_stop(self):
        with tempfile.TemporaryDirectory() as temp:
            opener=FakeOpener(data=b'0123456789')
            transport=self.transport(Path(temp),opener,max_download_bytes=5)
            meta,body=transport.get('https://index.commoncrawl.org/test','index',100)
            self.assertEqual(len(body),5)
            self.assertFalse(meta['complete'])
            self.assertEqual(transport.bytes,5)
            self.assertIsNone(transport.get('https://index.commoncrawl.org/test','index',100))
        with tempfile.TemporaryDirectory() as temp:
            transport=self.transport(Path(temp),FakeOpener(),max_index_requests=1)
            transport.get('https://index.commoncrawl.org/test','index',100)
            self.assertIsNone(transport.get('https://index.commoncrawl.org/test','index',100))
            self.assertEqual(transport.index_requests,1)

    def test_source_host_refused_and_whole_warc_not_downloaded(self):
        with tempfile.TemporaryDirectory() as temp:
            opener=FakeOpener(data=b'whole archive')
            transport=self.transport(Path(temp),opener)
            with self.assertRaises(ValueError):
                transport.get('https://example.org/','index',100)
            self.assertEqual(opener.calls,0)
            meta,body=transport.get('https://data.commoncrawl.org/test','warc',100,'bytes=0-99')
            self.assertEqual(body,b'')
            self.assertEqual(meta['error'],'range_ignored_body_not_read')

    def test_manifest_detects_changed_and_extra_artifact(self):
        with tempfile.TemporaryDirectory() as temp:
            folder=Path(temp)
            (folder/'one').write_bytes(b'evidence')
            cc.seal(folder)
            cc.verify(folder)
            (folder/'two').write_bytes(b'extra')
            with self.assertRaisesRegex(ValueError,'artifact set mismatch'):
                cc.verify(folder)
            (folder/'one').write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError,'artifact mismatch'):
                cc.verify(folder)


if __name__ == '__main__':
    unittest.main()
