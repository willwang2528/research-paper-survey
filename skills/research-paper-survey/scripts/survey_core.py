"""Versioned research runs and evidence-presence gates, not semantic truth verification."""
from collections import Counter
import copy
from datetime import date, datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import uuid
from urllib.parse import urlsplit

from providers import HTTPClient, ProviderError, search_s2, search_arxiv, search_openalex, snowball_s2

SKILL_DIR = Path(__file__).resolve().parents[1]
VERSION = (SKILL_DIR / 'VERSION').read_text().strip()


def now():
    return datetime.now(timezone.utc).isoformat()


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + '.tmp')
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    tmp.replace(path)


def read_jsonl(path):
    path = Path(path)
    if not path.exists(): return []
    rows = []
    for i, line in enumerate(path.read_text(encoding='utf-8').splitlines(), 1):
        if not line.strip(): continue
        try:
            value = json.loads(line)
        except ValueError:
            raise ValueError('%s line %s: invalid JSON' % (path.name, i)) from None
        if not isinstance(value, dict):
            raise ValueError('%s line %s: expected an object' % (path.name, i))
        rows.append(value)
    return rows


def write_jsonl(path, rows):
    path = Path(path)
    tmp = path.with_name(path.name + '.tmp')
    tmp.write_text(''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in rows), encoding='utf-8')
    tmp.replace(path)


def append_jsonl(path, row):
    with Path(path).open('a', encoding='utf-8') as f:
        f.write(json.dumps(row, ensure_ascii=False) + '\n')


def load_credentials(env_file=None):
    """Read only supported variable names. Do not source shell files or evaluate values."""
    names = ('SEMANTIC_SCHOLAR_API_KEY', 'S2_API_KEY', 'SEMANTIC_SCHOLAR_API_KEY_FILE', 'OPENALEX_API_KEY')
    values = {}
    if env_file:
        for line in Path(env_file).expanduser().read_text(encoding='utf-8').splitlines():
            m = re.match(r'^\s*(?:export\s+)?([A-Z0-9_]+)\s*=\s*(.*?)\s*$', line)
            if m and m.group(1) in names:
                v = m.group(2)
                if len(v) >= 2 and v[0] == v[-1] and v[0] in ('"', "'"):
                    v = v[1:-1]
                if '$' in v or '`' in v or '\n' in v:
                    raise ValueError('Credential file must contain literal values, not shell expressions')
                values[m.group(1)] = v
    values.update({k: os.environ[k] for k in names if os.environ.get(k)})
    key = values.get('SEMANTIC_SCHOLAR_API_KEY') or values.get('S2_API_KEY')
    if not key and values.get('SEMANTIC_SCHOLAR_API_KEY_FILE'):
        key = Path(values['SEMANTIC_SCHOLAR_API_KEY_FILE']).expanduser().read_text().strip()
    return {'s2': key or '', 'openalex': values.get('OPENALEX_API_KEY', '')}


def validate_protocol(p, require_queries=False):
    if not isinstance(p, dict) or p.get('schema_version') != 1:
        raise ValueError('protocol schema_version must be 1')
    if not p.get('topic') or not p.get('objective'):
        raise ValueError('protocol topic and objective are required')
    try:
        start, end = date.fromisoformat(p['start_date']), date.fromisoformat(p['end_date'])
    except (KeyError, TypeError, ValueError):
        raise ValueError('start_date/end_date must be ISO dates') from None
    if start > end: raise ValueError('start_date must not be after end_date')
    if p.get('date_basis') not in ('first_public', 'formal_publication'):
        raise ValueError('date_basis must be first_public or formal_publication')
    reqs = p.get('requirements')
    if not isinstance(reqs, list) or not reqs:
        raise ValueError('requirements must be a nonempty list')
    ids = []
    for r in reqs:
        if not isinstance(r, dict) or not r.get('id') or not r.get('description') or not isinstance(r.get('hard'), bool):
            raise ValueError('Each requirement needs id, description, and boolean hard')
        ids.append(r['id'])
    if len(ids) != len(set(ids)) or not any(r['hard'] for r in reqs):
        raise ValueError('Requirement IDs must be unique; at least one must be hard')
    checks = p.get('coverage_requirements')
    if not isinstance(checks, list) or not checks or len(checks) != len(set(checks)):
        raise ValueError('coverage_requirements must be nonempty and unique')
    queries = p.get('queries', [])
    if not isinstance(queries, list) or (require_queries and not queries):
        raise ValueError('Add explicit provider-specific queries to protocol.json before searching')
    qids = []
    for q in queries:
        if not isinstance(q, dict) or not q.get('id') or not q.get('query') or q.get('provider') not in ('s2', 'arxiv', 'openalex'):
            raise ValueError('Each query needs id, query, and supported provider')
        if not isinstance(q.get('limit', 100), int) or isinstance(q.get('limit'), bool) or not 1 <= q.get('limit', 100) <= 10000:
            raise ValueError('Query limit must be an integer from 1 to 10000')
        qids.append(q['id'])
    if len(qids) != len(set(qids)): raise ValueError('Query IDs must be unique')
    return p


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def init_run(out, topic, start, end):
    out = Path(out)
    protocol = {'schema_version': 1, 'topic': topic, 'objective': '建立近期研究地图与证据可查的阅读计划',
                'start_date': start, 'end_date': end, 'date_basis': 'first_public',
                'requirements': [{'id': 'R1', 'description': '论文主要研究问题直接对应：' + topic, 'hard': True}],
                'preferences': [], 'exclusions': [], 'queries': [],
                'coverage_requirements': ['keyword_search', 'citation_search', 'venue_scan', 'recent_preprints', 'seed_check']}
    validate_protocol(protocol)
    if out.exists() and any(out.iterdir()): raise ValueError('Run directory is not empty; refusing to overwrite')
    out.mkdir(parents=True, exist_ok=True)
    (out / 'raw').mkdir()
    write_json(out / 'protocol.json', protocol)
    write_json(out / 'run.json', {'schema_version': 1, 'run_id': uuid.uuid4().hex, 'created_at': now(), 'skill_version': VERSION})
    write_json(out / 'coverage.json', {'checks': [{'id': k, 'status': 'pending', 'evidence': '', 'reason': ''}
                                               for k in protocol['coverage_requirements']], 'limitations': []})
    for f in ('papers.jsonl', 'reviews.jsonl', 'search_log.jsonl', 'feedback.jsonl'):
        (out / f).touch()
    return {'run_dir': str(out), 'skill_version': VERSION, 'next': 'Edit protocol.json: refine requirements and add provider-specific queries'}


def normalize_ids(ids):
    out = {}
    for k, v in ids.items():
        if not v: continue
        v = str(v).strip()
        if k == 'doi': v = re.sub(r'^(https?://(?:dx\.)?doi\.org/|doi:)', '', v, flags=re.I).lower()
        if k == 'arxiv':
            v = re.sub(r'^(https?://arxiv\.org/(abs|pdf)/|arxiv:)', '', v, flags=re.I)
            v = re.sub(r'(v\d+)?(\.pdf)?$', '', v)
        if k == 'openalex': v = v.rstrip('/').split('/')[-1]
        out[k] = v
    return out


def merge_records(records):
    """Merge exact identifier-connected components. Title similarity never auto-merges."""
    parent = list(range(len(records)))
    def root(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i
    owners = {}
    normalized = []
    for i, record in enumerate(records):
        if not record.get('title') or not isinstance(record.get('ids'), dict):
            raise ValueError('Imported records require a title and ids object')
        r = copy.deepcopy(record)
        r['ids'] = normalize_ids(r['ids'])
        if not r['ids']: raise ValueError('A stable scholarly identifier is required; title alone cannot safely deduplicate')
        normalized.append(r)
        for key in r['ids'].items():
            if key in owners:
                a, b = root(i), root(owners[key])
                parent[max(a, b)] = min(a, b)
            owners[key] = i
    groups = {}
    for i, r in enumerate(normalized): groups.setdefault(root(i), []).append(r)
    result = []
    for group in groups.values():
        first = copy.deepcopy(group[0])
        first.setdefault('work_id', 'w-' + fingerprint(first['ids'])[:16])
        first['ids'], first['provenance'], first['observations'] = {}, [], []
        conflicts = []
        for r in group:
            first['provenance'].extend(r.get('provenance', []))
            first['observations'].extend(r.get('observations') or [{k: v for k, v in r.items() if k not in ('provenance', 'observations')}])
            for k, v in r['ids'].items():
                if k in first['ids'] and first['ids'][k] != v:
                    conflicts.append({'field': k, 'values': [first['ids'][k], v]})
                else: first['ids'][k] = v
            for k, v in r.items():
                if k not in ('ids', 'provenance', 'observations', 'work_id') and not first.get(k): first[k] = v
            conflicts.extend(r.get('identifier_conflicts', []))
        first['identifier_conflicts'] = conflicts
        result.append(first)
    return result


def import_records(run, path, source):
    run, path = Path(run), Path(path)
    validate_protocol(read_json(run / 'protocol.json'))
    rows = read_jsonl(path) if path.suffix == '.jsonl' else read_json(path)
    if not isinstance(rows, list): raise ValueError('Import file must be a JSON array or JSONL objects')
    for r in rows:
        if not isinstance(r, dict): raise ValueError('Import records must be objects')
        r.setdefault('provenance', []).append({'source': source, 'imported_at': now(), 'input_sha256': hashlib.sha256(path.read_bytes()).hexdigest()})
    merged = merge_records(read_jsonl(run / 'papers.jsonl') + rows)
    write_jsonl(run / 'papers.jsonl', merged)
    append_jsonl(run / 'search_log.jsonl', {'kind': 'import', 'source': source, 'at': now(), 'status': 'ok', 'retained_count': len(rows)})
    return {'imported': len(rows), 'independent_works': len(merged)}


def search_run(run, credentials, refresh=False):
    run = Path(run)
    p = validate_protocol(read_json(run / 'protocol.json'), require_queries=True)
    history = read_jsonl(run / 'search_log.jsonl')
    http = HTTPClient(run / 'raw', credentials)
    failed, skipped, searched = 0, 0, 0
    for q in p['queries']:
        sig = fingerprint({'query': q, 'start': p['start_date'], 'end': p['end_date'], 'version': VERSION})
        if not refresh and any(h.get('fingerprint') == sig and h.get('status') == 'ok' for h in history):
            skipped += 1
            continue
        before = len(http.artifacts)
        try:
            fn = {'s2': search_s2, 'arxiv': search_arxiv, 'openalex': search_openalex}[q['provider']]
            rows, meta = fn(http, q, int(p['start_date'][:4]), int(p['end_date'][:4]))
        except (ValueError, ProviderError) as exc:
            rows, meta = [], {'status': 'failed', 'error': str(exc), 'truncated': True, 'retained_count': 0}
        stamp = now()
        for r in rows:
            r['provenance'] = [{'source': q['provider'], 'query_id': q['id'], 'retrieved_at': stamp, 'fingerprint': sig}]
        if rows:
            write_jsonl(run / 'papers.jsonl', merge_records(read_jsonl(run / 'papers.jsonl') + rows))
        log = dict(meta, kind='search', query=q, query_id=q['id'], fingerprint=sig, at=stamp, skill_version=VERSION,
                   requested_window=[p['start_date'], p['end_date']], retrieval_window=[p['start_date'][:4], p['end_date'][:4]],
                   date_filter_note='Year-wide candidate retrieval; exact requested date basis must be verified from primary sources',
                   artifacts=http.artifacts[before:])
        append_jsonl(run / 'search_log.jsonl', log)
        searched += 1
        failed += meta['status'] != 'ok'
    return {'searched': searched, 'skipped': skipped, 'failed': failed,
            'independent_works': len(read_jsonl(run / 'papers.jsonl'))}


def snowball_run(run, credentials, paper_id, direction, limit):
    run = Path(run)
    validate_protocol(read_json(run / 'protocol.json'))
    if not 1 <= limit <= 10000: raise ValueError('limit must be between 1 and 10000')
    http = HTTPClient(run / 'raw', credentials)
    rows, meta = snowball_s2(http, paper_id, direction, limit)
    stamp = now()
    for r in rows:
        r['provenance'] = [{'source': 's2', 'seed': paper_id, 'direction': direction, 'retrieved_at': stamp}]
    write_jsonl(run / 'papers.jsonl', merge_records(read_jsonl(run / 'papers.jsonl') + rows))
    append_jsonl(run / 'search_log.jsonl', dict(meta, kind='snowball', seed=paper_id, direction=direction,
                                               limit=limit, at=stamp, artifacts=http.artifacts))
    return meta


def valid_url(value):
    if not isinstance(value, str): return False
    p = urlsplit(value)
    return p.scheme in ('http', 'https') and bool(p.hostname)


def evidence_present(ev):
    return (isinstance(ev, dict) and valid_url(ev.get('source_url'))
            and bool(str(ev.get('locator', '')).strip()) and bool(str(ev.get('evidence', '')).strip()))


def audit_run(run):
    run = Path(run)
    p = validate_protocol(read_json(run / 'protocol.json'))
    papers, reviews = read_jsonl(run / 'papers.jsonl'), read_jsonl(run / 'reviews.jsonl')
    errors, warnings = [], []
    counts = Counter()
    paper_ids = {x['work_id'] for x in papers}
    if len(paper_ids) != len(papers): errors.append('duplicate work_id in papers')
    seen = set()
    for r in reviews:
        wid = r.get('work_id')
        if wid in seen: errors.append('%s: duplicate review' % wid)
        seen.add(wid)
        if wid not in paper_ids: errors.append('%s: review refers to unknown work_id' % wid)
        decision = r.get('decision')
        counts[str(decision)] += 1
        if decision not in ('core', 'background', 'excluded', 'pending'):
            errors.append('%s: invalid decision' % wid)
        if decision == 'pending': errors.append('%s: pending review' % wid)
        if not all(r.get(k) for k in ('reason', 'reviewer', 'reviewed_at')):
            errors.append('%s: reason/reviewer/reviewed_at required' % wid)
        if decision != 'core': continue
        identity = r.get('identity') or {}
        fulltext = r.get('fulltext') or {}
        if identity.get('verified') is not True or not valid_url(identity.get('source_url')):
            errors.append('%s: identity evidence missing' % wid)
        if fulltext.get('reviewed') is not True or not valid_url(fulltext.get('source_url')) or not fulltext.get('version'):
            errors.append('%s: fulltext review/version missing' % wid)
        requirements = r.get('requirements') or {}
        for req in p['requirements']:
            if req['hard']:
                e = requirements.get(req['id'], {})
                if e.get('verdict') != 'yes' or not evidence_present(e) or not e.get('rationale'):
                    errors.append('%s: %s not supported as yes' % (wid, req['id']))
        de = r.get('date_evidence') or {}
        try:
            actual = date.fromisoformat(de.get('date', ''))
            date_ok = date.fromisoformat(p['start_date']) <= actual <= date.fromisoformat(p['end_date'])
        except (TypeError, ValueError): date_ok = False
        if not date_ok or de.get('basis') != p['date_basis'] or not valid_url(de.get('source_url')) or not de.get('locator'):
            errors.append('%s: date basis/window evidence missing or mismatched' % wid)
        claims = r.get('claims') or []
        if not claims or any(not evidence_present(c) or not c.get('text') for c in claims):
            errors.append('%s: claim evidence missing' % wid)
        paper = next((x for x in papers if x['work_id'] == wid), {})
        if paper.get('identifier_conflicts'):
            errors.append('%s: identifier conflicts require manual resolution' % wid)
    missing = paper_ids - seen
    for wid in sorted(missing): errors.append('%s: unreviewed paper' % wid)
    counts['pending'] += len(missing)
    coverage = read_json(run / 'coverage.json')
    checks = {c['id']: c for c in coverage.get('checks', [])}
    if len(checks) != len(coverage.get('checks', [])): errors.append('coverage: duplicate check IDs')
    for cid in p['coverage_requirements']:
        check = checks.get(cid, {})
        if not (check.get('status') == 'done' and check.get('evidence')) and not (check.get('status') == 'not_applicable' and check.get('reason')):
            errors.append('coverage: %s unresolved' % cid)
    logs = read_jsonl(run / 'search_log.jsonl')
    # Latest attempt for the same fingerprint supersedes a recovered API failure.
    latest = {}
    for i, log in enumerate(logs): latest[log.get('fingerprint', str(i))] = log
    for log in latest.values():
        if log.get('status') in ('failed', 'partial'):
            errors.append('search: unresolved failure for %s' % log.get('query_id', log.get('kind')))
        if log.get('truncated'):
            warnings.append('Bounded retrieval: %s' % log.get('query_id', log.get('kind')))
    output = {'schema_version': 1, 'skill_version': VERSION, 'audited_at': now(), 'ready': not errors,
              'semantic_truth_verified_by_script': False, 'independent_works': len(papers),
              'decisions': dict(counts), 'errors': errors, 'warnings': warnings,
              'note': 'Structural evidence-presence checks only; source correctness and coverage require reviewer judgment.'}
    write_json(run / 'audit.json', output)
    return output


def md(value):
    return str(value or '').replace('|', '\\|').replace('\n', ' ')


def render_report(run, strict=False):
    run = Path(run)
    audit = audit_run(run)
    p = read_json(run / 'protocol.json')
    papers = read_jsonl(run / 'papers.jsonl')
    reviews = {r.get('work_id'): r for r in read_jsonl(run / 'reviews.jsonl')}
    lines = ['# ' + p['topic'], '', '状态：' + ('STRUCTURALLY_READY' if audit['ready'] else 'DRAFT / 待核验'),
             '', '结构检查通过不等于原文语义、科学结论或全领域覆盖已获证明。', '',
             '检索窗口：%s 至 %s；日期口径：%s；skill：%s。' % (p['start_date'], p['end_date'], p['date_basis'], VERSION),
             '', '## 需求', '']
    for r in p['requirements']:
        lines.append('- %s (%s): %s' % (r['id'], 'hard' if r['hard'] else 'preference', r['description']))
    lines += ['', '## 文献总表', '', '| work_id | 论文 | 去向 | 理由 |', '|---|---|---|---|']
    for paper in papers:
        r = reviews.get(paper['work_id'], {})
        lines.append('| %s | %s | %s | %s |' % (paper['work_id'], md(paper['title']), r.get('decision', 'pending'), md(r.get('reason', '未完成逐篇核验'))))
    lines += ['', '## 逐篇证据', '']
    for paper in papers:
        r = reviews.get(paper['work_id'], {})
        lines += ['### ' + paper['title'], '', '- work_id: ' + paper['work_id'],
                  '- 原始入口：' + str(paper.get('url') or ''), '- 标识：`' + json.dumps(paper['ids'], ensure_ascii=False) + '`',
                  '- 日期/版本核验：' + json.dumps(r.get('date_evidence', {}), ensure_ascii=False),
                  '- 全文记录：' + json.dumps(r.get('fulltext', {}), ensure_ascii=False)]
        for rid, e in (r.get('requirements') or {}).items():
            lines.append('- %s: %s；%s；%s；%s；理由：%s' % (rid, e.get('verdict'), e.get('evidence', ''), e.get('locator', ''), e.get('source_url', ''), e.get('rationale', '')))
        for c in r.get('claims') or []:
            lines.append('- 主张：%s；证据：%s；%s；%s' % (c.get('text'), c.get('evidence'), c.get('locator'), c.get('source_url')))
        lines.append('- 局限：' + '; '.join(r.get('limitations') or []))
        lines.append('')
    synthesis = run / 'synthesis.md'
    lines += ['## 综合与阅读计划', '', synthesis.read_text() if synthesis.exists() else '待 reviewer 基于证据撰写 synthesis.md；脚本不生成无依据的研究结论。',
              '', '## 检索记录', '']
    for log in read_jsonl(run / 'search_log.jsonl'):
        lines.append('- ' + json.dumps({k: v for k, v in log.items() if k != 'artifacts'}, ensure_ascii=False))
    lines += ['', '## 覆盖与限制', '', '```json', json.dumps(read_json(run / 'coverage.json'), ensure_ascii=False, indent=2), '```',
              '', '## 审计', '', '```json', json.dumps(audit, ensure_ascii=False, indent=2), '```', '']
    (run / 'report.md').write_text('\n'.join(lines), encoding='utf-8')
    if strict and not audit['ready']:
        raise ValueError('Strict report blocked: audit failed. An explicitly labeled DRAFT was saved for inspection.')
    return {'report': str(run / 'report.md'), 'ready': audit['ready'], 'semantic_truth_verified_by_script': False}


def feedback(run, category, observation, proposal):
    run = Path(run)
    meta = read_json(run / 'run.json')
    row = {'id': uuid.uuid4().hex, 'at': now(), 'run_id': meta['run_id'], 'skill_version': VERSION,
           'category': category, 'observation': observation, 'proposal': proposal, 'status': 'proposed'}
    append_jsonl(run / 'feedback.jsonl', row)
    return row
