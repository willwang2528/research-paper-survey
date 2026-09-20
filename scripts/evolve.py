#!/usr/bin/env python3
"""Evidence-gated local version maintenance. Never commits, pushes, installs, or edits a running survey."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys


def stamp(): return datetime.now(timezone.utc).isoformat()


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def load(path): return json.loads(path.read_text(encoding='utf-8'))


def iteration(root, ident):
    if not re.fullmatch(r'[a-z0-9][a-z0-9-]{0,63}', ident):
        raise ValueError('iteration ID must be lowercase letters, digits, or hyphens')
    return root / 'iterations' / ident


def digest(root):
    excluded = {'.git', '__pycache__', '.venv', '.pytest_cache', 'runs', 'iterations', 'validation', 'dist'}
    sha = hashlib.sha256()
    for f in sorted(root.rglob('*')):
        rel = f.relative_to(root)
        if not f.is_file() or f.is_symlink() or excluded.intersection(rel.parts) or f.name.startswith('.env') or f.suffix in ('.pyc', '.key', '.pem'):
            continue
        sha.update(str(rel).encode() + b'\0' + f.read_bytes() + b'\0')
    return sha.hexdigest()


def new_iteration(root, ident, problem, proposal):
    out = iteration(root, ident)
    if out.exists(): raise ValueError('Iteration already exists; choose a new ID')
    plan = {'id': ident, 'created_at': stamp(), 'baseline_version': (root / 'VERSION').read_text().strip(),
            'problem': problem, 'proposal': proposal, 'status': 'proposed',
            'method_effectiveness': 'Not measured by regression tests; document separately when applicable'}
    write(out / 'plan.json', plan)
    return plan


def check(root, ident):
    out = iteration(root, ident)
    if not (out / 'plan.json').exists(): raise ValueError('Create the iteration first')
    if not list((root / 'tests').glob('test*.py')): raise ValueError('No regression tests found')
    before = digest(root)
    cmd = [sys.executable, '-m', 'unittest', 'discover', '-s', 'tests', '-v']
    run = subprocess.run(cmd, cwd=str(root), capture_output=True, text=True)
    log = run.stdout + run.stderr
    # Test runners should use synthetic sentinels; redact any inherited known key anyway.
    import os
    for name in ('SEMANTIC_SCHOLAR_API_KEY', 'S2_API_KEY', 'OPENALEX_API_KEY'):
        if os.environ.get(name): log = log.replace(os.environ[name], '[REDACTED]')
    (out / 'tests.txt').write_text(log, encoding='utf-8')
    versions = [(root / 'VERSION').read_text().strip(),
                (root / 'skills/research-paper-survey/VERSION').read_text().strip()]
    skill = (root / 'skills/research-paper-survey/SKILL.md').read_text()
    match = re.search(r'^  version: [\"\']?([0-9]+\.[0-9]+\.[0-9]+)', skill, re.M)
    aligned = match is not None and versions[0] == versions[1] == match.group(1)
    data = {'checked_at': stamp(), 'source_digest': before, 'source_unchanged_during_check': digest(root) == before,
            'test_exit_code': run.returncode, 'versions_aligned': aligned,
            'passed': run.returncode == 0 and aligned and digest(root) == before,
            'test_log': 'tests.txt', 'semantic_research_quality_proven': False}
    write(out / 'check.json', data)
    return data


def parse_version(value):
    if not re.fullmatch(r'(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)', value):
        raise ValueError('Version must be a stable SemVer triple')
    return tuple(map(int, value.split('.')))


def release(root, ident, version, summary):
    out = iteration(root, ident)
    if not (out / 'check.json').exists(): raise ValueError('Run check before release')
    if (out / 'release.json').exists(): raise ValueError('This iteration was already released')
    data = load(out / 'check.json')
    if not data.get('passed') or data.get('source_digest') != digest(root):
        raise ValueError('Checks failed or sources changed after validation; rerun check')
    old = (root / 'VERSION').read_text().strip()
    if parse_version(version) <= parse_version(old): raise ValueError('Release version must increase')
    skill = root / 'skills/research-paper-survey'
    text = (skill / 'SKILL.md').read_text()
    text, n = re.subn(r'^  version: .*$', '  version: "' + version + '"', text, count=1, flags=re.M)
    if n != 1: raise ValueError('Cannot locate skill metadata version')
    (skill / 'SKILL.md').write_text(text, encoding='utf-8')
    for file in (root / 'VERSION', skill / 'VERSION'): file.write_text(version + '\n')
    changelog = root / 'CHANGELOG.md'
    oldtext = changelog.read_text()
    heading, sep, body = oldtext.partition('\n')
    entry = '\n## %s — %s\n\n- %s\n- 验证记录：[iterations/%s](iterations/%s/plan.json)。回归通过不代表研究召回率已测量。\n' % (version, stamp()[:10], summary, ident, ident)
    changelog.write_text(heading + '\n' + entry + body, encoding='utf-8')
    record = {'released_at': stamp(), 'previous_version': old, 'version': version, 'summary': summary,
              'validated_source_digest': data['source_digest'], 'released_source_digest': digest(root),
              'publication': 'local files only; commit/tag/push remain separate authorized operations'}
    write(out / 'release.json', record)
    plan = load(out / 'plan.json')
    plan['status'] = 'released_locally'
    write(out / 'plan.json', plan)
    return record


def main():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest='cmd', required=True)
    for name in ('new', 'check', 'release'):
        s = sub.add_parser(name)
        s.add_argument('--id', required=True)
        if name == 'new':
            s.add_argument('--problem', required=True)
            s.add_argument('--proposal', required=True)
        if name == 'release':
            s.add_argument('--version', required=True)
            s.add_argument('--summary', required=True)
    args = p.parse_args()
    root = Path(__file__).resolve().parents[1]
    try:
        if args.cmd == 'new': data = new_iteration(root, args.id, args.problem, args.proposal)
        elif args.cmd == 'check': data = check(root, args.id)
        else: data = release(root, args.id, args.version, args.summary)
        print(json.dumps(data, ensure_ascii=False, indent=2))
        return 1 if data.get('passed') is False else 0
    except (ValueError, OSError) as exc:
        print(str(exc), file=sys.stderr)
        return 2


if __name__ == '__main__': raise SystemExit(main())
