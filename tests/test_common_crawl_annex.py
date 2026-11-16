"""Synthetic tests for temporal and evidence boundaries; no network access."""
import base64
import gzip
import hashlib
import http.client
from contextlib import contextmanager
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from urllib.parse import parse_qs

SPEC = importlib.util.spec_from_file_location('cc_annex', Path(__file__).resolve().parents[1]/'scripts/common_crawl_annex.py')
cc = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(cc)
WINDOWS = {'M1':{'start':'2026-09-15T00:00:00Z','end_exclusive':'2026-10-15T00:00:00Z'},
           'M2':{'start':'2026-10-15T00:00:00Z','end_exclusive':'2026-11-15T00:00:00Z'}}
URL = 'https://example.org/llms.txt'
CDX = {'url':URL,'timestamp':'20261015000000','status':'200','digest':base64.b32encode(hashlib.sha1(b'hello\r\n').digest()).decode()}


def warc(body=b'hello\r\n', kind='response', extra='', status=200, url=URL, date='2026-10-15T00:00:00Z', http_extra=''):
    http = (f'HTTP/1.1 {status} OK\r\nContent-Type: text/plain; charset=utf-8\r\nContent-Length: {len(body)}\r\n'+http_extra+'\r\n').encode()+body
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



class ReviewRegressionTests(unittest.TestCase):
    def collect_fixture(self, *, warc_status=206, bad_digest=False, expanded_limit=None, replay=False):
        selection=json.loads((cc.ROOT/'annexes/common-crawl-20261116/selection.json').read_text(encoding='utf-8'))
        selection['sample']=selection['sample'][:5]
        selection['indexes']=selection['indexes'][:1]
        if expanded_limit is not None:
            selection['budget']['max_record_uncompressed_bytes']=expanded_limit
        url=selection['sample'][0]['url']
        raw=warc(url=url)
        row=dict(CDX,url=url,offset='0',length=str(len(raw)),
                 filename=f"crawl-data/{selection['indexes'][0]['id']}/segments/fixture/fixture.warc.gz")
        if bad_digest:
            row['digest']='A'*32
        calls=[]

        class FixtureOpener:
            def open(self, request, **kwargs):
                calls.append(request.full_url)
                if request.full_url.endswith('/collinfo.json'):
                    return FakeResponse(200,b'[]')
                if request.get_header('Range'):
                    return FakeResponse(warc_status,raw,{'Content-Range':f'bytes 0-{len(raw)-1}/{len(raw)}'})
                query_url=parse_qs(cc.urlsplit(request.full_url).query)['url'][0]
                if query_url==url:
                    return FakeResponse(200,json.dumps(row).encode())
                return FakeResponse(404,json.dumps({'message':'No Captures found for: '+query_url}).encode())

        original_transport=cc.Transport
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            selection_path=root/'selection.json'
            cc.write_json(selection_path,selection)
            output=root/'run'
            with patch.object(cc,'Transport',lambda folder,budget: original_transport(folder,budget,FixtureOpener(),lambda _:None)):
                code=cc.collect(selection_path,output)
            cc.verify(output)
            capture=json.loads((output/'captures.json').read_text(encoding='utf-8'))[0]
            summary=json.loads((output/'summary.json').read_text(encoding='utf-8'))
            if replay:
                replay_parent=root/'separate-parent'
                replay_parent.mkdir()
                replay_output=replay_parent/'analysis'
                cc.analyze_cached(output,replay_output)
                replay_capture=json.loads((replay_output/'captures.json').read_text(encoding='utf-8'))[0]
                compressed=(replay_output/replay_capture['compressed_artifact']).resolve()
                self.assertEqual(compressed,(output/'raw/007.bin').resolve())
                self.assertEqual(compressed.read_bytes(),raw)
                self.assertEqual(replay_capture['source_digest_checks'],capture['source_digest_checks'])
        self.assertEqual(len(calls),7)
        self.assertEqual(summary['queries_complete'],5)
        return code,capture,summary

    def test_collect_usable_capture_succeeds(self):
        code,capture,summary=self.collect_fixture()
        self.assertEqual(code,0)
        self.assertEqual(capture['state'],'content_retrieved_comparable')
        self.assertEqual(summary['comparable_captures'],1)

    def test_offline_replay_keeps_compressed_artifact_resolvable(self):
        self.collect_fixture(replay=True)

    def test_collect_missing_warc_is_incomplete(self):
        code,capture,summary=self.collect_fixture(warc_status=502)
        self.assertEqual(capture['state'],'capture_content_not_retrieved')
        self.assertEqual(summary['comparable_captures'],0)
        self.assertEqual(code,2)

    def test_collect_source_digest_mismatch_is_incomplete(self):
        code,capture,summary=self.collect_fixture(bad_digest=True)
        self.assertEqual(code,2)
        self.assertFalse(capture['source_digest_checks']['cdx_payload'])
        self.assertEqual(capture['state'],'content_partial_redirect_or_revisit')
        self.assertEqual(summary['comparable_captures'],0)

    def test_each_source_digest_mismatch_is_not_comparable(self):
        for extra,row,check in [('',dict(CDX,digest='A'*32),'cdx_payload'),
                ('WARC-Payload-Digest: sha1:'+'A'*32+'\r\n',CDX,'warc_payload'),
                ('WARC-Block-Digest: sha1:'+'A'*32+'\r\n',CDX,'warc_block')]:
            with self.subTest(check=check):
                result,_=cc.inspect_warc(warc(extra=extra),row,WINDOWS)
                self.assertEqual(result['state'],'content_partial_redirect_or_revisit')
                self.assertFalse(result['source_digest_checks'][check])
                self.assertIn('source_digest_mismatch',result['issues'])

    def test_configured_expansion_limit_applies_to_collection(self):
        code,capture,_=self.collect_fixture(expanded_limit=64)
        self.assertEqual(code,2)
        self.assertIn('expanded_record_limit',capture['issues'])

    def test_invalid_deflate_is_recorded_as_partial(self):
        raw=bytearray(warc())
        raw[10]=(raw[10]&0xf8)|7  # Reserved DEFLATE block type, inside a valid gzip header.
        result,_=cc.inspect_warc(bytes(raw),CDX,WINDOWS)
        self.assertEqual(result['state'],'content_partial_redirect_or_revisit')
        self.assertTrue(result['issues'])

    def test_nested_manifest_is_covered(self):
        with tempfile.TemporaryDirectory() as temp:
            folder=Path(temp)
            (folder/'nested').mkdir()
            nested=folder/'nested'/'manifest.json'
            nested.write_bytes(b'{"proof":"original"}')
            cc.seal(folder)
            cc.verify(folder)
            entries=json.loads((folder/'manifest.json').read_text(encoding='utf-8'))['artifacts']
            self.assertEqual([item['path'] for item in entries],['nested/manifest.json'])
            nested.write_bytes(b'{"proof":"modified"}')
            with self.assertRaisesRegex(ValueError,'artifact mismatch'):
                cc.verify(folder)



class AuditRegressionTests(unittest.TestCase):
    @contextmanager
    def collection(self, mode='valid', ows=' \t'):
        selection=json.loads((cc.ROOT/'annexes/common-crawl-20261116/selection.json').read_text(encoding='utf-8'))
        selection['sample']=selection['sample'][:5]
        selection['indexes']=selection['indexes'][:1]
        url=selection['sample'][0]['url']
        raw=warc(url=url)
        row=dict(CDX,url=url,offset='0',length=str(len(raw)),
                 filename=f"crawl-data/{selection['indexes'][0]['id']}/segments/fixture/fixture.warc.gz")
        calls=[]

        class LocalSocket:
            def __init__(self, wire): self.wire=wire
            def makefile(self, *args, **kwargs): return io.BytesIO(self.wire)

        def framed(body, declared=None, chunked=False):
            framing='Transfer-Encoding: chunked' if chunked else f'Content-Length: {len(body) if declared is None else declared}'
            response=http.client.HTTPResponse(LocalSocket(f'HTTP/1.1 200 OK\r\n{framing}\r\n\r\n'.encode()+body))
            response.begin()
            response.code=response.status
            return response

        class Opener:
            def open(self, request, **kwargs):
                calls.append(request.full_url)
                if request.full_url.endswith('/collinfo.json'):
                    if mode=='catalog_interrupt': raise KeyboardInterrupt('synthetic interruption')
                    return FakeResponse(200,b'[]')
                if request.get_header('Range'):
                    total=1 if mode in {'bad_range_total','range_ows_invalid_total'} else len(raw)
                    suffix=ows if mode.startswith('range_ows') else ''
                    return FakeResponse(206,raw,{'Content-Range':f'bytes 0-{len(raw)-1}/{total}'+suffix})
                query_url=parse_qs(cc.urlsplit(request.full_url).query)['url'][0]
                if query_url!=url:
                    return FakeResponse(404,json.dumps({'message':'No Captures found for: '+query_url}).encode())
                if mode=='bad_status': raise http.client.BadStatusLine('synthetic malformed status')
                if mode=='chunked_cut': return framed(b'3\r\nabc\r\n8\r\ncut',chunked=True)
                record=dict(row,url=url+'?variant') if mode=='short_variant' else row
                body=json.dumps(record).encode()+b'\n'
                declared=len(body)+80 if mode.startswith('short_') else len(body)
                if mode in {'length_ows','short_ows'}: declared=f'{declared}{ows}'
                return framed(body,declared)

        transport=cc.Transport
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            selection_path=root/'selection.json'
            cc.write_json(selection_path,selection)
            output=root/'run'
            code=None;exception=None
            try:
                with patch.object(cc,'Transport',lambda folder,budget: transport(folder,budget,Opener(),lambda _:None)), \
                     patch('socket.socket',side_effect=AssertionError('network is disabled')):
                    code=cc.collect(selection_path,output)
            except BaseException as exc:
                exception=type(exc).__name__
            cc.verify(output)
            requests_path=output/'requests.json'
            yield {'root':root,'run':output,'code':code,'exception':exception,'calls':len(calls),
                   'summary':json.loads((output/'summary.json').read_text(encoding='utf-8')),
                   'queries':json.loads((output/'queries.json').read_text(encoding='utf-8')),
                   'captures':json.loads((output/'captures.json').read_text(encoding='utf-8')),
                   'requests':json.loads(requests_path.read_text(encoding='utf-8')) if requests_path.exists() else []}

    def test_truncated_cdx_cannot_become_absence_or_complete(self):
        for mode in ['short_exact','short_variant']:
            with self.subTest(mode=mode), self.collection(mode) as result:
                self.assertEqual(result['code'],2)
                self.assertIsNone(result['exception'])
                self.assertFalse(result['queries'][0]['complete'])
                self.assertEqual(result['queries'][0]['state'],'query_failed_or_incomplete')
                self.assertEqual(result['summary']['queries_complete'],4)
                self.assertEqual(result['captures'],[])

    def test_framed_complete_response_preserves_success(self):
        with self.collection() as result:
            self.assertEqual(result['code'],0)
            self.assertIsNone(result['exception'])
            self.assertEqual(result['summary']['queries_complete'],5)
            self.assertEqual(result['captures'][0]['state'],'content_retrieved_comparable')
            self.assertEqual(result['calls'],len(result['requests']))

    def test_incomplete_chunk_keeps_attempt_and_exposed_bytes(self):
        with self.collection('chunked_cut') as result:
            self.assertEqual(result['code'],2)
            self.assertIsNone(result['exception'])
            self.assertEqual(result['calls'],2)
            self.assertEqual(len(result['requests']),2)
            self.assertEqual(result['summary']['stop_reason'],'transport_failure')
            receipt=result['requests'][-1]
            self.assertIn('IncompleteRead',receipt['error'])
            self.assertEqual((result['run']/receipt['body_path']).read_bytes(),b'abc')
            self.assertFalse(receipt['complete'])
            self.assertFalse(result['summary']['download_bytes_exact'])

    def test_catalog_interrupt_is_journaled_and_propagated(self):
        with self.collection('catalog_interrupt') as result:
            self.assertEqual(result['exception'],'KeyboardInterrupt')
            self.assertIsNone(result['code'])
            self.assertEqual(result['calls'],1)
            self.assertEqual(len(result['requests']),1)
            self.assertEqual(result['summary']['catalog_requests'],1)
            self.assertEqual(result['summary']['stop_reason'],'interrupted')
            self.assertIn('KeyboardInterrupt',result['requests'][0]['error'])

    def test_http_protocol_exception_stops_with_receipt(self):
        with self.collection('bad_status') as result:
            self.assertEqual(result['code'],2)
            self.assertIsNone(result['exception'])
            self.assertEqual(result['calls'],len(result['requests']))
            self.assertEqual(result['summary']['stop_reason'],'transport_failure')
            self.assertIn('BadStatusLine',result['requests'][-1]['error'])

    def test_replay_refuses_output_under_either_input_root(self):
        with self.collection() as result:
            run=result['run'];before=(run/'manifest.json').read_bytes()
            for output in [run,run/'analysis']:
                with self.subTest(output=output.name), self.assertRaises(ValueError):
                    cc.analyze_cached(run,output)
                self.assertEqual((run/'manifest.json').read_bytes(),before)
                cc.verify(run)
            self.assertFalse((run/'analysis').exists())
            snapshot=result['root']/'snapshot-input';snapshot.mkdir()
            with self.assertRaises(ValueError):
                cc.analyze_cached(run,snapshot/'analysis',snapshot)
            self.assertEqual(list(snapshot.iterdir()),[])
            cc.verify(run)

    def test_http_lists_preserved_without_relaxing_framing(self):
        repeated='Cache-Control: public\r\nCache-Control: max-age=300\r\nVary: Accept-Encoding\r\nVary: Accept-Language\r\n'
        result,artifacts=cc.inspect_warc(warc(http_extra=repeated),CDX,WINDOWS)
        self.assertEqual(result['state'],'content_retrieved_comparable')
        self.assertEqual(artifacts['payload.bin'],b'hello\r\n')
        self.assertEqual(result['http_headers']['cache-control'],['public','max-age=300'])
        self.assertEqual(result['http_headers']['vary'],['Accept-Encoding','Accept-Language'])
        for field in ['Content-Length: 7','Content-Type: text/plain']:
            result,_=cc.inspect_warc(warc(http_extra=field+'\r\n'),CDX,WINDOWS)
            self.assertEqual(result['state'],'content_partial_redirect_or_revisit')
            self.assertIn('ambiguous_duplicate_header',result['issues'])

    def test_content_length_optional_whitespace_preserves_length_check(self):
        for ows in [' ', '\t', ' \t']:
            with self.subTest(ows=repr(ows)), self.collection('length_ows',ows) as result:
                self.assertEqual(result['code'],0)
                receipt=result['requests'][1]
                self.assertTrue(receipt['complete'])
                self.assertTrue(receipt['headers']['Content-Length'].endswith(ows))
            with self.subTest(truncated_ows=repr(ows)), self.collection('short_ows',ows) as result:
                self.assertEqual(result['code'],2)
                self.assertEqual(result['queries'][0]['state'],'query_failed_or_incomplete')
                self.assertEqual(result['requests'][1]['error'],'content_length_mismatch')

    def test_content_range_optional_whitespace_preserves_bounds_check(self):
        for ows in [' ', '\t', ' \t']:
            with self.subTest(ows=repr(ows)), self.collection('range_ows',ows) as result:
                self.assertEqual(result['code'],0)
                self.assertTrue(result['requests'][-1]['headers']['Content-Range'].endswith(ows))
                replay=result['root']/'analysis'
                cc.analyze_cached(result['run'],replay)
                self.assertEqual(json.loads((replay/'captures.json').read_text(encoding='utf-8'))[0]['state'],'content_retrieved_comparable')
            with self.subTest(invalid_total_ows=repr(ows)), self.collection('range_ows_invalid_total',ows) as result:
                self.assertEqual(result['code'],2)
                self.assertEqual(result['captures'][0]['state'],'capture_content_not_retrieved')
        meta={'status':206,'complete':True,'headers':{'Content-Range':'bytes 9-11/1 2'}}
        self.assertFalse(cc.range_valid(meta,b'abc',{'offset':'9','length':'3'}))

    def test_invalid_range_total_refused_in_collect_and_replay(self):
        with self.collection('bad_range_total') as result:
            self.assertEqual(result['code'],2)
            self.assertEqual(result['captures'][0]['state'],'capture_content_not_retrieved')
            replay=result['root']/'analysis'
            cc.analyze_cached(result['run'],replay)
            capture=json.loads((replay/'captures.json').read_text(encoding='utf-8'))[0]
            self.assertEqual(capture['state'],'capture_content_not_retrieved')
            self.assertEqual(capture['retrieval_issue'],'invalid_or_incomplete_range_response')
        for total,expected in [(0,False),(11,False),(12,True)]:
            meta={'status':206,'complete':True,'headers':{'Content-Range':f'bytes 9-11/{total}'}}
            self.assertEqual(cc.range_valid(meta,b'abc',{'offset':'9','length':'3'}),expected)


if __name__ == '__main__':
    unittest.main()
