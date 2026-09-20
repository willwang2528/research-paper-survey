"""Read-only scholarly API clients. Standard library only; credentials never enter URLs."""
import hashlib
import json
from pathlib import Path
import re
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
import xml.etree.ElementTree as ET

S2 = 'https://api.semanticscholar.org/graph/v1'
FIELDS = 'title,abstract,authors,year,publicationDate,venue,publicationTypes,externalIds,url,openAccessPdf,citationCount'


class ProviderError(RuntimeError):
    pass


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        # Never forward an API credential to a redirect destination.
        return None


class HTTPClient:
    def __init__(self, raw_dir, credentials, retries=3, interval=None):
        self.raw_dir = Path(raw_dir)
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        self.credentials = credentials
        self.retries = retries
        self.interval = interval
        self.last = {}
        self.artifacts = []
        self.opener = urllib.request.build_opener(NoRedirect())

    def get(self, url, params, provider):
        hosts = {'s2': 'api.semanticscholar.org', 'arxiv': 'export.arxiv.org', 'openalex': 'api.openalex.org'}
        parsed = urllib.parse.urlsplit(url)
        if parsed.scheme != 'https' or parsed.hostname != hosts.get(provider):
            raise ProviderError('Provider URL is not an approved HTTPS API endpoint')
        if any(re.search(r'key|token|secret', k, re.I) for k in params if k != 'token'):
            raise ProviderError('Credentials must not be sent as query parameters')
        endpoint = url + '?' + urllib.parse.urlencode(params)
        headers = {'User-Agent': 'research-paper-survey/0.1 (+https://github.com/willwang2528/research-paper-survey)'}
        key = self.credentials.get(provider)
        if key:
            headers['x-api-key' if provider == 's2' else 'Authorization'] = key if provider == 's2' else 'Bearer ' + key
        interval = self.interval if self.interval is not None else {'s2': 1.1, 'arxiv': 3.1, 'openalex': 0.2}[provider]
        for attempt in range(self.retries + 1):
            time.sleep(max(0, interval - (time.monotonic() - self.last.get(provider, 0))))
            self.last[provider] = time.monotonic()
            try:
                req = urllib.request.Request(endpoint, headers=headers)
                with self.opener.open(req, timeout=30) as response:
                    body = response.read()
                for secret in self.credentials.values():
                    if secret:
                        body = body.replace(secret.encode(), b'[REDACTED]')
                try:
                    value = body if provider == 'arxiv' else json.loads(body)
                except (ValueError, UnicodeDecodeError):
                    raise ProviderError(provider + ': invalid JSON response') from None
                name = provider + '-' + uuid.uuid4().hex + ('.xml' if provider == 'arxiv' else '.json')
                (self.raw_dir / name).write_bytes(body)
                self.artifacts.append({'file': 'raw/' + name, 'sha256': hashlib.sha256(body).hexdigest()})
                return value
            except urllib.error.HTTPError as exc:
                if exc.code in (429, 500, 502, 503, 504) and attempt < self.retries:
                    retry = exc.headers.get('Retry-After', '') if exc.headers else ''
                    delay = float(retry) if re.fullmatch(r'\d+(\.\d+)?', retry) else 2 ** (attempt + 1)
                    time.sleep(min(delay, 30))
                    continue
                raise ProviderError('%s: HTTP %s after %s attempt(s)' % (provider, exc.code, attempt + 1)) from None
            except (urllib.error.URLError, TimeoutError, OSError):
                if attempt < self.retries:
                    time.sleep(2 ** (attempt + 1))
                    continue
                raise ProviderError(provider + ': network failure (details withheld to protect credentials)') from None


def result(rows, total, more, error=None, retrieved=None):
    return rows, {'total_reported': total, 'retained_count': len(rows),
                  'retrieved_count': len(rows) if retrieved is None else retrieved,
                  'truncated': bool(more), 'status': ('partial' if rows else 'failed') if error else 'ok',
                  'error': error}


def normalize_s2(p):
    ids = {'s2': p.get('paperId')}
    ext = p.get('externalIds') or {}
    ids.update(doi=ext.get('DOI'), arxiv=ext.get('ArXiv'))
    return {'ids': {k: v for k, v in ids.items() if v}, 'title': p.get('title') or '',
            'abstract': p.get('abstract'), 'authors': [a.get('name', '') for a in p.get('authors') or []],
            'year': p.get('year'), 'publication_date': p.get('publicationDate'),
            'venue': p.get('venue'), 'publication_types': p.get('publicationTypes'),
            'url': p.get('url'), 'open_access_pdf': (p.get('openAccessPdf') or {}).get('url'),
            'citation_count': p.get('citationCount'), 'metadata_source': 's2'}


def search_s2(http, query, start_year, end_year):
    mode = query.get('mode', 'relevance')
    limit = query.get('limit', 100)
    text = query['query']
    if mode not in ('relevance', 'bulk'):
        raise ValueError('s2 mode must be relevance or bulk')
    if re.search(r'\b(AND|OR|NOT)\b', text):
        raise ValueError('s2 does not use AND/OR/NOT words: relevance is plain text; bulk uses + | -')
    if mode == 'relevance' and re.search(r'[|+*~()]', text):
        raise ValueError('s2 relevance query must be plain text; use bulk for operator syntax')
    if mode == 'relevance' and query.get('sort'):
        raise ValueError('s2 relevance does not support sort; use bulk for publicationDate:desc')
    # Year-wide retrieval avoids falsely excluding records whose day is unknown.
    params = {'query': text, 'fields': FIELDS, 'year': '%s-%s' % (start_year, end_year)}
    if mode == 'bulk':
        params['sort'] = query.get('sort', 'paperId:asc')
        if params['sort'] not in ('paperId:asc', 'paperId:desc', 'publicationDate:asc', 'publicationDate:desc', 'citationCount:asc', 'citationCount:desc'):
            raise ValueError('Unsupported s2 bulk sort')
    rows, total, retrieved, more = [], None, 0, True
    seen = set()
    while len(rows) < limit and more:
        if mode == 'relevance':
            params.update(offset=params.get('offset', 0), limit=min(100, limit - len(rows), 1000 - len(rows)))
        try:
            data = http.get(S2 + '/paper/search' + ('/bulk' if mode == 'bulk' else ''), params, 's2')
        except ProviderError as exc:
            return result(rows, total, True, str(exc), retrieved)
        if not isinstance(data, dict) or not isinstance(data.get('data'), list):
            return result(rows, total, True, 's2: invalid result envelope', retrieved)
        total = data.get('total')
        batch = data['data']
        retrieved += len(batch)
        rows.extend(normalize_s2(p) for p in batch[:limit - len(rows)])
        cursor = data.get('token' if mode == 'bulk' else 'next')
        more = cursor is not None or retrieved > len(rows)
        if cursor is None:
            break
        if str(cursor) in seen or not batch:
            return result(rows, total, True, 's2: repeated cursor or empty continuation page', retrieved)
        seen.add(str(cursor))
        params['token' if mode == 'bulk' else 'offset'] = cursor
        if mode == 'relevance' and cursor >= 1000:
            break
    return result(rows, total, more, retrieved=retrieved)


def snowball_s2(http, paper_id, direction, limit):
    if direction not in ('references', 'citations'):
        raise ValueError('direction must be references or citations')
    url = S2 + '/paper/' + urllib.parse.quote(paper_id, safe='') + '/' + direction
    rows, offset, more = [], 0, True
    while len(rows) < limit and more:
        try:
            d = http.get(url, {'fields': FIELDS, 'offset': offset, 'limit': min(1000, limit - len(rows))}, 's2')
        except ProviderError as exc:
            return result(rows, None, True, str(exc))
        if not isinstance(d, dict) or not isinstance(d.get('data'), list):
            return result(rows, None, True, 's2: invalid citation envelope')
        for edge in d['data']:
            p = edge.get('citedPaper' if direction == 'references' else 'citingPaper')
            if p and p.get('paperId'):
                rows.append(normalize_s2(p))
        cursor = d.get('next')
        more = cursor is not None
        if not more:
            break
        if cursor <= offset:
            return result(rows, None, True, 's2: non-advancing citation cursor')
        offset = cursor
    return result(rows, None, more)


def search_arxiv(http, query, start_year, end_year):
    ns = {'a': 'http://www.w3.org/2005/Atom', 'o': 'http://a9.com/-/spec/opensearch/1.1/',
          'x': 'http://arxiv.org/schemas/atom'}
    limit = query.get('limit', 100)
    sort = query.get('sort', 'relevance')
    if sort not in ('relevance', 'submittedDate', 'lastUpdatedDate'):
        raise ValueError('Unsupported arxiv sort')
    q = '(%s) AND submittedDate:[%s01010000 TO %s12312359]' % (query['query'], start_year, end_year)
    rows, total = [], None
    while len(rows) < limit:
        params = {'search_query': q, 'start': len(rows), 'max_results': min(100, limit - len(rows)),
                  'sortBy': sort, 'sortOrder': 'descending'}
        try:
            raw = http.get('https://export.arxiv.org/api/query', params, 'arxiv')
            root = ET.fromstring(raw)
        except (ProviderError, ET.ParseError) as exc:
            return result(rows, total, True, str(exc) if isinstance(exc, ProviderError) else 'arxiv: invalid XML')
        entries = root.findall('a:entry', ns)
        total = int(root.findtext('o:totalResults', '0', ns))
        for e in entries:
            url = e.findtext('a:id', '', ns)
            if '/api/errors' in url:
                return result(rows, total, True, 'arxiv: API error entry')
            arxiv_id = url.split('/abs/')[-1]
            pub = e.findtext('a:published', '', ns)[:10]
            links = e.findall('a:link', ns)
            rows.append({'ids': {'arxiv': arxiv_id, **({'doi': e.findtext('x:doi', '', ns)} if e.findtext('x:doi', '', ns) else {})},
                         'title': ' '.join(e.findtext('a:title', '', ns).split()),
                         'abstract': e.findtext('a:summary', '', ns), 'authors': [a.findtext('a:name', '', ns) for a in e.findall('a:author', ns)],
                         'year': int(pub[:4]) if pub else None, 'first_public_date': pub,
                         'updated_date': e.findtext('a:updated', '', ns)[:10], 'publication_date': None,
                         'url': url.replace('http://', 'https://'),
                         'open_access_pdf': next((a.get('href').replace('http://', 'https://') for a in links if a.get('title') == 'pdf'), None),
                         'venue': e.findtext('x:journal_ref', '', ns), 'metadata_source': 'arxiv'})
        if not entries or len(rows) >= total:
            break
    return result(rows, total, len(rows) < (total or 0))


def search_openalex(http, query, start_year, end_year):
    limit = query.get('limit', 100)
    params = {'search': query['query'], 'filter': 'from_publication_date:%s-01-01,to_publication_date:%s-12-31' % (start_year, end_year),
              'per-page': min(200, limit), 'cursor': '*'}
    if query.get('sort'):
        if query['sort'] not in ('publication_date:desc', 'publication_date:asc', 'cited_by_count:desc', 'relevance_score:desc'):
            raise ValueError('Unsupported openalex sort')
        params['sort'] = query['sort']
    rows, total, seen = [], None, set()
    while len(rows) < limit:
        params['per-page'] = min(200, limit - len(rows))
        try:
            d = http.get('https://api.openalex.org/works', params, 'openalex')
        except ProviderError as exc:
            return result(rows, total, True, str(exc))
        if not isinstance(d, dict) or not isinstance(d.get('results'), list):
            return result(rows, total, True, 'openalex: invalid result envelope')
        total = (d.get('meta') or {}).get('count')
        for p in d['results']:
            loc = p.get('primary_location') or {}
            ids = {'openalex': p['id']}
            if p.get('doi'): ids['doi'] = p['doi']
            rows.append({'ids': ids, 'title': p.get('title') or '',
                         'authors': [(a.get('author') or {}).get('display_name', '') for a in p.get('authorships') or []],
                         'abstract': None, 'abstract_inverted_index': p.get('abstract_inverted_index'),
                         'year': p.get('publication_year'), 'publication_date': p.get('publication_date'),
                         'url': loc.get('landing_page_url') or p['id'], 'open_access_pdf': loc.get('pdf_url'),
                         'venue': (loc.get('source') or {}).get('display_name'), 'metadata_source': 'openalex'})
        cursor = (d.get('meta') or {}).get('next_cursor')
        if not cursor or not d['results'] or len(rows) >= (total or 0):
            break
        if cursor in seen:
            return result(rows, total, True, 'openalex: repeated cursor')
        seen.add(cursor)
        params['cursor'] = cursor
    return result(rows, total, total is not None and len(rows) < total)
