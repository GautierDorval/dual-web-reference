"""Bounded, one-off Common Crawl annex. Stdlib only; never visits source sites.

Raw third-party material stays outside this repository. No edition pipeline import,
no scheduling, no retries, no redirects, no automatic revisit resolution.
"""
from __future__ import annotations

import argparse
import base64
import csv
from datetime import UTC, datetime
from email.message import Message
import gzip
import hashlib
import io
import json
from pathlib import Path
import platform
import re
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

VERSION = '1.0.1'
ROOT = Path(__file__).resolve().parents[1]
MAX_BYTES = 100 * 1024 * 1024
MAX_EXPANDED = 16 * 1024 * 1024
LIMIT = 1001
STATES = ('no_capture_in_queried_indexes', 'capture_only_outside_window',
          'query_failed_or_incomplete', 'capture_content_not_retrieved',
          'content_partial_redirect_or_revisit', 'content_retrieved_comparable')


def utcnow():
    return datetime.now(UTC).isoformat().replace('+00:00', 'Z')


def digest(data):
    return hashlib.sha256(data).hexdigest()


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')


def instant(value):
    if re.fullmatch(r'\d{14}', value):
        return datetime.strptime(value, '%Y%m%d%H%M%S').replace(tzinfo=UTC)
    dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if dt.utcoffset() is None:
        raise ValueError('timezone required')
    return dt.astimezone(UTC)


def window_of(timestamp, windows):
    dt = instant(timestamp)
    for name, bounds in windows.items():
        if instant(bounds['start']) <= dt < instant(bounds['end_exclusive']):
            return name
    return 'outside'


def parse_cdx(status, body, exact_url, complete=True):
    """Only the provider's explicit no-captures response is an empty result."""
    if status == 404 and complete:
        try:
            error = json.loads(body).get('message', '')
        except (ValueError, AttributeError):
            error = ''
        if error.startswith('No Captures found for:'):
            return [], True, 'no_capture'
    if status != 200 or not complete:
        return [], False, 'http_error_or_clipped'
    try:
        records = [json.loads(line) for line in body.decode('utf-8').splitlines() if line.strip()]
        # With no explicit empty-result response, an empty 200 is inconclusive.
        if not records or len(records) >= LIMIT:
            return [], False, 'empty_or_row_limit'
        for row in records:
            if not isinstance(row, dict) or not isinstance(row.get('url'), str):
                raise ValueError('invalid CDX shape')
            instant(row['timestamp'])
        return [r for r in records if r['url'] == exact_url], True, 'complete_exact_original_url_filter'
    except (ValueError, TypeError, KeyError, UnicodeError):
        return [], False, 'invalid_cdx'


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class Transport:
    def __init__(self, output, budget, opener=None, sleeper=time.sleep):
        self.output, self.budget = output, budget
        self.opener = opener or build_opener(NoRedirect())
        self.sleep = sleeper
        self.last_request = None
        self.requests = []
        self.bytes = 0
        self.index_requests = 0
        self.warc_requests = 0
        self.stop_reason = None

    def get(self, url, kind, cap, range_header=None):
        parts = urlsplit(url)
        if (parts.scheme != 'https' or parts.hostname not in {'index.commoncrawl.org', 'data.commoncrawl.org'}
                or parts.username or parts.password or parts.port or parts.fragment):
            raise ValueError('unapproved endpoint')
        if self.stop_reason:
            return None
        if kind == 'index' and self.index_requests >= self.budget['max_index_requests']:
            self.stop_reason = 'index_budget_exhausted'
            return None
        if kind == 'warc' and self.warc_requests >= self.budget['max_warc_records']:
            self.stop_reason = 'warc_budget_exhausted'
            return None
        if self.bytes >= self.budget['max_download_bytes']:
            self.stop_reason = 'download_budget_exhausted'
            return None
        if self.last_request is not None:
            self.sleep(max(0, self.budget['interval_seconds'] - (time.monotonic() - self.last_request)))
        self.last_request = time.monotonic()
        self.index_requests += kind == 'index'
        self.warc_requests += kind == 'warc'
        number = len(self.requests) + 1
        meta = {'request_id':f'R{number:03d}', 'kind':kind, 'url':url,
                'started_at_utc':utcnow(), 'range':range_header, 'status':None,
                'complete':False, 'headers':{}, 'error':None}
        headers = {'User-Agent':f'DWR-Archive-Annex/{VERSION} (+https://github.com/GautierDorval/dual-web-reference)',
                   'Accept-Encoding':'identity'}
        if range_header:
            headers['Range'] = range_header
        body = b''
        response = None
        try:
            try:
                response = self.opener.open(Request(url, headers=headers), timeout=30)
            except HTTPError as exc:
                response = exc
            with response:
                meta['status'] = response.code
                meta['headers'] = dict(response.headers.items())
                if kind == 'warc' and response.code == 200:
                    meta['error'] = 'range_ignored_body_not_read'
                    self.stop_reason = 'range_ignored'
                else:
                    allowance = min(cap + 1, self.budget['max_download_bytes'] - self.bytes)
                    body = response.read(allowance)
                    # A cap-sized unknown-length response is conservatively incomplete.
                    meta['complete'] = len(body) < allowance and len(body) <= cap
        except (URLError, OSError, TimeoutError) as exc:
            meta['error'] = type(exc).__name__ + ': ' + str(exc)
            # No transport fallback or retry after a connection failure.
            self.stop_reason = 'transport_failure'
        self.bytes += len(body)
        meta.update({'finished_at_utc':utcnow(), 'bytes':len(body), 'sha256':digest(body)})
        meta['body_path'] = f'raw/{number:03d}.bin'
        (self.output / meta['body_path']).write_bytes(body)
        if meta['status'] in (403, 429, 503):
            self.stop_reason = f'provider_stop_http_{meta["status"]}'
            meta['retry_after'] = next((v for k,v in meta['headers'].items() if k.lower() == 'retry-after'), None)
            # Stopping, with no retry, honors Retry-After without assuming a shorter delay.
        if self.bytes >= self.budget['max_download_bytes']:
            self.stop_reason = 'download_budget_exhausted'
        self.requests.append(meta)
        write_json(self.output/'requests.json', self.requests)
        print(f'{meta["request_id"]} {kind} status={meta["status"]} bytes={len(body)} stop={self.stop_reason}', flush=True)
        return meta, body


def split_headers(data):
    raw, separator, body = data.partition(b'\r\n\r\n')
    if not separator or len(raw) > 65536:
        raise ValueError('missing_or_oversize_headers')
    lines = raw.decode('iso-8859-1').split('\r\n')
    headers = {}
    for line in lines[1:]:
        name, sep, value = line.partition(':')
        key = name.lower()
        if not sep:
            raise ValueError('invalid_header')
        if key in headers:
            # Common Crawl repeats WARC-Protocol (HTTP/TLS); WARC allows concurrent-to.
            # Repeated HTTP list fields/cookies are also legal; framing fields stay strict.
            if key not in {'warc-protocol', 'warc-concurrent-to', 'set-cookie', 'link', 'warning', 'via', 'server-timing'}:
                raise ValueError('ambiguous_duplicate_header')
            prior = headers[key]
            headers[key] = (prior if isinstance(prior, list) else [prior]) + [value.strip()]
        else:
            headers[key] = value.strip()
    return lines[0], headers, body


def bounded_gunzip(data):
    with gzip.GzipFile(fileobj=io.BytesIO(data)) as stream:
        expanded = stream.read(MAX_EXPANDED + 1)
    if len(expanded) > MAX_EXPANDED:
        raise ValueError('expanded_record_limit')
    return expanded


def inspect_warc(data, cdx, windows):
    """Preserve raw bytes and report unsupported encodings instead of guessing."""
    result = {'state':'content_partial_redirect_or_revisit', 'issues':[], 'body_available':False}
    artifacts = {}
    try:
        raw = bounded_gunzip(data)
        artifacts['record.warc'] = raw
        version, warc, block = split_headers(raw)
        result['warc'] = warc
        if version not in ('WARC/1.0', 'WARC/1.1'):
            raise ValueError('invalid_warc_version')
        length = int(warc['content-length'])
        if length < 0 or len(block) < length or block[length:].strip(b'\r\n'):
            raise ValueError('warc_length_or_multiple_records')
        block = block[:length]
        result['record_type'] = warc.get('warc-type')
        result['original_url'] = warc.get('warc-target-uri')
        result['captured_at_utc'] = warc.get('warc-date')
        result['window'] = window_of(warc['warc-date'], windows)
        result['source_payload_digest'] = warc.get('warc-payload-digest')
        result['source_block_digest'] = warc.get('warc-block-digest')
        result['cdx_digest'] = {'algorithm':'SHA-1 (Common Crawl CDX)', 'value':cdx.get('digest')}
        if warc.get('warc-target-uri') != cdx['url']:
            result['issues'].append('warc_cdx_url_mismatch')
        if instant(warc['warc-date']) != instant(cdx['timestamp']):
            result['issues'].append('warc_cdx_time_mismatch')
        if warc.get('warc-truncated'):
            result['issues'].append('warc_truncated:' + warc['warc-truncated'])
        if warc.get('warc-type') != 'response':
            result['issues'].append('revisit_requires_resolution' if warc.get('warc-type') == 'revisit' else 'not_response')
            return result, artifacts
        artifacts['http-message.bin'] = block
        status_line, http, payload = split_headers(block)
        match = re.fullmatch(r'HTTP/\d(?:\.\d)? (\d{3})(?: .*)?', status_line)
        if not match:
            raise ValueError('invalid_http_status')
        status = int(match[1])
        result.update({'http_status':status, 'http_headers':http, 'content_type':http.get('content-type'),
                       'location':http.get('location'), 'body_available':bool(payload)})
        artifacts['payload.bin'] = payload
        if str(status) != str(cdx.get('status')):
            result['issues'].append('warc_cdx_status_mismatch')
        if 300 <= status < 400:
            result['issues'].append('http_redirect_not_followed')
        elif status != 200:
            result['issues'].append('http_non_200')
        if not payload:
            result['issues'].append('empty_body')
        if 'content-length' in http and int(http['content-length']) != len(payload):
            result['issues'].append('http_length_mismatch')
        if http.get('transfer-encoding', '').lower() not in ('', 'identity'):
            result['issues'].append('transfer_encoding_not_decoded')
            return result, artifacts
        encoding = http.get('content-encoding', 'identity').lower()
        if encoding == 'gzip':
            decoded = bounded_gunzip(payload)
        elif encoding in ('identity', ''):
            decoded = payload
        else:
            result['issues'].append('content_encoding_not_decoded:' + encoding)
            return result, artifacts
        artifacts['decoded.bin'] = decoded
        result['decoded_sha256'] = digest(decoded)
        mime = Message()
        mime['content-type'] = http.get('content-type', 'application/octet-stream')
        charset = mime.get_content_charset() or 'utf-8'
        result['charset_used'] = charset
        try:
            normalized = decoded.decode(charset).replace('\r\n', '\n').replace('\r', '\n').encode('utf-8')
            artifacts['normalized.txt'] = normalized
            result['normalization'] = 'strict declared charset (UTF-8 if absent), UTF-8 output, CRLF/CR to LF only; no JS or HTML rendering'
        except (UnicodeError, LookupError):
            result['normalization'] = 'unavailable; binary byte comparison only'
        if not result['issues']:
            result['state'] = 'content_retrieved_comparable'
    except (ValueError, KeyError, OSError, EOFError) as exc:
        result['issues'].append(str(exc))
    return result, artifacts


def validate_selection(selection):
    sample, indexes, budget = selection['sample'], selection['indexes'], selection['budget']
    if not 5 <= len(sample) <= 10 or len({x['url'] for x in sample}) != len(sample):
        raise ValueError('sample must contain 5-10 unique exact URLs')
    if not 1 <= len(indexes) <= 3 or len({x['id'] for x in indexes}) != len(indexes):
        raise ValueError('invalid index count')
    for index in indexes:
        if not re.fullmatch(r'CC-MAIN-\d{4}-\d{2}', index['id']):
            raise ValueError('invalid index id')
    for item in sample:
        url = urlsplit(item['url'])
        if (url.scheme != 'https' or url.hostname not in {'gautierdorval.com','pagup.com','better-robots.com'}
                or url.port or url.username or url.password or url.query or url.fragment or '*' in item['url']):
            raise ValueError('invalid sample URL')
    for name, maximum in [('max_urls',10),('max_indexes',3),('max_index_requests',30),('max_warc_records',20),('max_download_bytes',MAX_BYTES),('max_index_response_bytes',2*1024*1024),('max_record_uncompressed_bytes',MAX_EXPANDED)]:
        if not isinstance(budget[name], int) or not 1 <= budget[name] <= maximum:
            raise ValueError('invalid budget:' + name)
    if len(sample) > budget['max_urls'] or len(indexes) > budget['max_indexes'] or budget['interval_seconds'] < 5:
        raise ValueError('invalid count or pacing')
    for bounds in selection['windows'].values():
        if instant(bounds['start']) >= instant(bounds['end_exclusive']):
            raise ValueError('invalid window')


def collect(selection_path, output):
    selection_bytes = selection_path.read_bytes()
    selection = json.loads(selection_bytes)
    validate_selection(selection)
    output = output.resolve()
    if output == ROOT or ROOT in output.parents:
        raise ValueError('raw output must be outside repository')
    # No overwrite/resume: preserve every failed/partial attempt.
    output.mkdir(parents=False, exist_ok=False)
    (output/'raw').mkdir()
    (output/'selection.json').write_bytes(selection_bytes)
    write_json(output/'run-start.json', {'started_at_utc':utcnow(),'selection_sha256':digest(selection_bytes),
               'tool_version':VERSION,'python':platform.python_version(),'script_sha256':digest(Path(__file__).read_bytes())})
    transport = Transport(output, selection['budget'])
    queries, captures = [], []
    try:
        # Published periods are pinned in selection; discovery does not invent a new crawl.
        transport.get('https://index.commoncrawl.org/collinfo.json', 'catalog', 2*1024*1024)
        for index in selection['indexes']:
            for item in selection['sample']:
                query = {'sample_id':item['sample_id'],'url':item['url'],'index':index['id'],
                         'complete':False,'state':'query_failed_or_incomplete','captures':[]}
                url = 'https://index.commoncrawl.org/' + index['id'] + '-index?' + urlencode({'url':item['url'],'output':'json','matchType':'exact','limit':LIMIT})
                query['request_url'] = url
                response = transport.get(url, 'index', selection['budget']['max_index_response_bytes'])
                if response is not None:
                    meta, body = response
                    query['request_id'] = meta['request_id']
                    rows, complete, reason = parse_cdx(meta['status'], body, item['url'], meta['complete'])
                    query.update({'complete':complete,'reason':reason,'state':'no_capture_in_queried_indexes' if complete and not rows else 'query_failed_or_incomplete'})
                    for row in rows:
                        cid = f'C{len(captures)+1:03d}'
                        capture = {'capture_id':cid,'sample_id':item['sample_id'],'index':index['id'],'cdx':row,
                                   'window':window_of(row['timestamp'],selection['windows']),
                                   'state':'capture_content_not_retrieved','query_complete':complete}
                        captures.append(capture)
                        query['captures'].append(cid)
                    if rows:
                        query['state'] = 'capture_content_not_retrieved'
                else:
                    query['reason'] = transport.stop_reason
                queries.append(query)
                write_json(output/'queries.json', queries)
        order = {'M2':0,'M1':1,'outside':2}
        for capture in sorted(captures, key=lambda x:(order[x['window']],-int(x['cdx']['timestamp']),x['sample_id'])):
            row = capture['cdx']
            try:
                filename = row['filename']
                if (not re.fullmatch(r'crawl-data/CC-MAIN-\d{4}-\d{2}/[A-Za-z0-9_./-]+\.warc\.gz',filename)
                        or '..' in filename.split('/') or '/'+capture['index']+'/' not in filename):
                    raise ValueError('unapproved_warc_path')
                offset, length = int(row['offset']), int(row['length'])
                if offset < 0 or not 0 < length <= MAX_EXPANDED:
                    raise ValueError('invalid_range')
                if length > selection['budget']['max_download_bytes'] - transport.bytes:
                    raise ValueError('insufficient_byte_budget')
                response = transport.get('https://data.commoncrawl.org/'+filename,'warc',length,
                                         f'bytes={offset}-{offset+length-1}')
                if response is None:
                    capture['retrieval_issue'] = transport.stop_reason
                    continue
                meta, data = response
                capture['request_id'] = meta['request_id']
                content_range = next((v for k,v in meta['headers'].items() if k.lower()=='content-range'),'')
                if (meta['status'] != 206 or not meta['complete'] or len(data) != length
                        or not re.fullmatch(rf'bytes {offset}-{offset+length-1}/\d+', content_range)):
                    capture['retrieval_issue'] = 'invalid_or_incomplete_range_response'
                    continue
                inspection, artifacts = inspect_warc(data, row, selection['windows'])
                capture.update(inspection)
                folder = output/'captures'/capture['capture_id']
                folder.mkdir(parents=True)
                capture['artifact_paths'] = []
                for name, value in artifacts.items():
                    path = folder/name
                    path.write_bytes(value)
                    capture['artifact_paths'].append(path.relative_to(output).as_posix())
                item = next(x for x in selection['sample'] if x['sample_id']==capture['sample_id'])
                capture['documentary_snapshot_digest_equal'] = inspection.get('decoded_sha256') == item['documentary_snapshot_sha256'] if inspection.get('decoded_sha256') else None
                capture['deployment_at_capture'] = 'not established; digest equality would not establish deployment time'
            except (ValueError, KeyError, TypeError) as exc:
                capture['retrieval_issue'] = str(exc)
    finally:
        write_json(output/'queries.json', queries)
        write_json(output/'captures.json', captures)
        write_json(output/'summary.json', {'finished_at_utc':utcnow(),'urls':len(selection['sample']),
                   'indexes_selected':len(selection['indexes']),'queries_planned':len(selection['sample'])*len(selection['indexes']),
                   'index_requests':transport.index_requests,'catalog_requests':sum(r['kind']=='catalog' for r in transport.requests),
                   'warc_requests':transport.warc_requests,'download_bytes':transport.bytes,
                   'queries_complete':sum(q['complete'] for q in queries),'captures':len(captures),
                   'comparable_captures':sum(c['state']=='content_retrieved_comparable' for c in captures),
                   'stop_reason':transport.stop_reason,'selection_sha256':digest(selection_bytes)})
        seal(output)
    return 0 if transport.stop_reason is None and all(q['complete'] for q in queries) else 2


def seal(folder):
    artifacts = [{'path':p.relative_to(folder).as_posix(),'bytes':p.stat().st_size,'sha256':digest(p.read_bytes())}
                 for p in sorted(folder.rglob('*')) if p.is_file() and p.name != 'manifest.json']
    write_json(folder/'manifest.json', {'algorithm':'SHA-256','self_exclusion':'manifest.json','artifacts':artifacts})


def verify(folder):
    manifest = json.loads((folder/'manifest.json').read_text(encoding='utf-8'))
    expected = set()
    for item in manifest['artifacts']:
        path = (folder/item['path']).resolve()
        if folder.resolve() not in path.parents or path.is_symlink():
            raise ValueError('unsafe artifact path')
        if path.stat().st_size != item['bytes'] or digest(path.read_bytes()) != item['sha256']:
            raise ValueError('artifact mismatch:' + item['path'])
        expected.add(item['path'])
    actual = {p.relative_to(folder).as_posix() for p in folder.rglob('*') if p.is_file() and p.name!='manifest.json'}
    if expected != actual:
        raise ValueError('artifact set mismatch')
    print(f'PASS {len(expected)} artifact hashes and exact file set')


def source_digest_matches(data, expected):
    if not expected:
        return None
    algorithm, sep, value = expected.partition(':')
    if not sep or algorithm.lower() not in {'sha1', 'sha256'}:
        return None
    raw = hashlib.new(algorithm.lower(), data).digest()
    return value.upper() in {raw.hex().upper(), base64.b32encode(raw).decode().rstrip('=')}


def range_valid(meta, data, cdx):
    offset, length = int(cdx['offset']), int(cdx['length'])
    header = next((v for k,v in meta['headers'].items() if k.lower()=='content-range'),'')
    return (meta['status']==206 and meta['complete'] and len(data)==length
            and re.fullmatch(rf'bytes {offset}-{offset+length-1}/\d+',header) is not None)


def window_state(captures, complete, window):
    inside = [c for c in captures if c['window']==window]
    if inside:
        # Coverage completeness is reported separately; do not discard a usable capture.
        if any(c['state']=='content_retrieved_comparable' for c in inside):
            return 'content_retrieved_comparable'
        if any(c['state']=='content_partial_redirect_or_revisit' for c in inside):
            return 'content_partial_redirect_or_revisit'
        return 'capture_content_not_retrieved'
    if captures:
        return 'capture_only_outside_window'
    return 'no_capture_in_queried_indexes' if complete else 'query_failed_or_incomplete'


def analyze_cached(run, output, snapshot_root=None):
    """Re-analyze immutable downloaded bytes; never creates a Transport."""
    verify(run)
    output=output.resolve()
    if output == ROOT or ROOT in output.parents:
        raise ValueError('private analysis must stay outside repository')
    selection=json.loads((run/'selection.json').read_text(encoding='utf-8'))
    validate_selection(selection)
    queries=json.loads((run/'queries.json').read_text(encoding='utf-8'))
    requests={r['request_id']:r for r in json.loads((run/'requests.json').read_text(encoding='utf-8'))}
    captured=json.loads((run/'captures.json').read_text(encoding='utf-8'))
    output.mkdir(parents=False,exist_ok=False)
    source_evidence=[]
    for item in selection['sample']:
        evidence={'sample_id':item['sample_id'],'url':item['url'],'snapshot_verified':False,
                  'deployment_at_capture':'not established','observation_transaction_match':'not established'}
        if snapshot_root is not None:
            site=urlsplit(item['url']).hostname
            metadata_path=snapshot_root/'sources'/site/'snapshot.json'
            metadata=json.loads(metadata_path.read_text(encoding='utf-8'))
            entry=next(e for e in metadata['files'] if e['url_path']==urlsplit(item['url']).path)
            source=(metadata_path.parent/entry['snapshot_file']).resolve()
            if metadata_path.parent.resolve() not in source.parents:
                raise ValueError('snapshot path escape')
            content=source.read_bytes()
            if digest(content)!=entry['sha256'] or digest(content)!=item['documentary_snapshot_sha256']:
                raise ValueError('snapshot hash mismatch')
            target=output/'snapshots'/item['sample_id']
            target.parent.mkdir(exist_ok=True)
            target.write_bytes(content)
            evidence.update({'snapshot_verified':True,'sha256':digest(content),'bytes':len(content),
                             'artifact_path':target.relative_to(output).as_posix(),'metadata_sha256':digest(metadata_path.read_bytes()),
                             'metadata_path':str(metadata_path),'snapshot_method':entry.get('obtained') or entry.get('how_obtained'),
                             'snapshot_generated_on':metadata['generated_on'],'source_entry':entry})
        source_evidence.append(evidence)
    results=[]
    for prior in captured:
        c={k:prior[k] for k in ['capture_id','sample_id','index','cdx','window','query_complete']}
        c['state']='capture_content_not_retrieved'
        request=requests.get(prior.get('request_id'))
        if request:
            data=(run/request['body_path']).read_bytes()
            if range_valid(request,data,c['cdx']):
                inspection,artifacts=inspect_warc(data,c['cdx'],selection['windows'])
                c.update(inspection)
                c['request_id']=request['request_id']
                c['compressed_artifact']='../'+run.name+'/'+request['body_path']
                folder=output/'captures'/c['capture_id']
                folder.mkdir(parents=True)
                c['artifacts']=[]
                for name,value in artifacts.items():
                    path=folder/name
                    path.write_bytes(value)
                    c['artifacts'].append({'path':path.relative_to(output).as_posix(),'bytes':len(value),'sha256':digest(value)})
                if 'payload.bin' in artifacts:
                    checks={'warc_payload':source_digest_matches(artifacts['payload.bin'],c.get('source_payload_digest')),
                            'warc_block':source_digest_matches(artifacts['http-message.bin'],c.get('source_block_digest')),
                            'cdx_payload':source_digest_matches(artifacts['payload.bin'],'sha1:'+c['cdx']['digest'])}
                    c['source_digest_checks']=checks
                    if False in checks.values():
                        c['state']='content_partial_redirect_or_revisit'
                        c['issues'].append('source_digest_mismatch')
                source=next(e for e in source_evidence if e['sample_id']==c['sample_id'])
                if source['snapshot_verified'] and 'decoded.bin' in artifacts:
                    local=(output/source['artifact_path']).read_bytes()
                    c['snapshot_bytes_equal']=artifacts['decoded.bin']==local
                    c['snapshot_normalized_equal']=None
                    try:
                        normalized=local.decode(c.get('charset_used','utf-8')).replace('\r\n','\n').replace('\r','\n').encode('utf-8')
                        c['snapshot_normalized_equal']=artifacts.get('normalized.txt')==normalized
                    except (UnicodeError,LookupError):
                        pass
            else:
                c['retrieval_issue']='invalid_or_incomplete_range_response'
        results.append(c)
    matrix=[]
    for item in selection['sample']:
        relevant=[q for q in queries if q['sample_id']==item['sample_id']]
        complete=len(relevant)==len(selection['indexes']) and all(q['complete'] for q in relevant)
        caps=[c for c in results if c['sample_id']==item['sample_id']]
        evidence=next(e for e in source_evidence if e['sample_id']==item['sample_id'])
        for c in caps or [None]:
            matrix.append({'sample_id':item['sample_id'],'url':item['url'],
                           'M1_state':window_state(caps,complete,'M1'),'M2_state':window_state(caps,complete,'M2'),
                           'all_index_queries_complete':complete,'completed_queries':sum(q['complete'] for q in relevant),
                           'planned_queries':len(selection['indexes']),'capture_id':c['capture_id'] if c else '',
                           'capture_state':c['state'] if c else '',
                           'captured_at_utc':c.get('captured_at_utc') or c['cdx']['timestamp'] if c else '',
                           'capture_window':c['window'] if c else '',
                           'index':c['index'] if c else '',
                           'http_status':c.get('http_status','') if c else '',
                           'record_type':c.get('record_type','') if c else '',
                           'content_type':c.get('content_type','') if c else '',
                           'warc_filename':c['cdx'].get('filename','') if c else '',
                           'warc_offset':c['cdx'].get('offset','') if c else '',
                           'warc_length':c['cdx'].get('length','') if c else '',
                           'snapshot_bytes_available':evidence['snapshot_verified'],
                           'snapshot_sha256':item['documentary_snapshot_sha256'],
                           'snapshot_bytes_equal':c.get('snapshot_bytes_equal','') if c else '',
                           'observation_source':item['observation_source'],
                           'observation_granularity':item['observation_granularity'],
                           'deployment_at_capture':'not established','same_transaction':'not established'})
    with (output/'matrix.csv').open('w',encoding='utf-8',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(matrix[0]),lineterminator='\n')
        writer.writeheader();writer.writerows(matrix)
    write_json(output/'captures.json',results)
    write_json(output/'source-evidence.json',source_evidence)
    write_json(output/'analysis.json',{'analyzed_at_utc':utcnow(),'tool_version':VERSION,
               'script_sha256':digest(Path(__file__).read_bytes()),'run_manifest_sha256':digest((run/'manifest.json').read_bytes()),
               'selection_sha256':digest((run/'selection.json').read_bytes()),'network_requests':0,
               'comparable_captures':sum(c['state']=='content_retrieved_comparable' for c in results),
               'snapshot_byte_matches':sum(c.get('snapshot_bytes_equal') is True for c in results)})
    seal(output)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    run = commands.add_parser('collect')
    run.add_argument('--selection', required=True, type=Path)
    run.add_argument('--output', required=True, type=Path)
    analyze=commands.add_parser('analyze-cached')
    analyze.add_argument('--run',required=True,type=Path)
    analyze.add_argument('--output',required=True,type=Path)
    analyze.add_argument('--snapshot-root',type=Path)
    for name in ('seal','verify'):
        sub = commands.add_parser(name)
        sub.add_argument('folder',type=Path)
    args = parser.parse_args()
    if args.command == 'collect':
        return collect(args.selection, args.output)
    if args.command == 'analyze-cached':
        analyze_cached(args.run,args.output,args.snapshot_root)
        return 0
    if args.command == 'seal':
        seal(args.folder)
    else:
        verify(args.folder)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
