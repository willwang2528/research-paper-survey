#!/usr/bin/env python3
"""CLI for auditable paper survey runs. See --help and bundled skill references."""
import argparse
import json
from pathlib import Path
import sys

from providers import HTTPClient, ProviderError
from survey_core import (VERSION, load_credentials, init_run, search_run, import_records,
                         snowball_run, audit_run, render_report, feedback)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--version', action='version', version=VERSION)
    parser.add_argument('--env-file', type=Path, help='Literal .env assignments; never sourced as shell')
    sub = parser.add_subparsers(dest='command', required=True)
    doctor = sub.add_parser('doctor', help='Check Python and credential presence without printing secrets')
    doctor.add_argument('--live', action='store_true', help='Make one Semantic Scholar authenticated read')
    doctor.add_argument('--out', type=Path, help='Store live probe evidence here (required with --live)')
    init = sub.add_parser('init', help='Initialize an empty, version-stamped run')
    for flag in ('topic', 'start', 'end'): init.add_argument('--' + flag, required=True)
    init.add_argument('--out', required=True, type=Path)
    for name in ('search', 'import', 'snowball', 'audit', 'report', 'feedback'):
        cmd = sub.add_parser(name)
        cmd.add_argument('--run', type=Path, required=True)
        if name == 'search': cmd.add_argument('--refresh', action='store_true')
        if name == 'import':
            cmd.add_argument('--input', required=True, type=Path)
            cmd.add_argument('--source', required=True)
        if name == 'snowball':
            cmd.add_argument('--paper-id', required=True)
            cmd.add_argument('--direction', choices=['references', 'citations'], required=True)
            cmd.add_argument('--limit', type=int, default=100)
        if name == 'report': cmd.add_argument('--strict', action='store_true')
        if name == 'feedback':
            for flag in ('category', 'observation', 'proposal'): cmd.add_argument('--' + flag, required=True)
    args = parser.parse_args(argv)
    try:
        credentials = load_credentials(args.env_file)
        exit_code = 0
        if args.command == 'doctor':
            out = {'python': sys.version.split()[0], 'skill_version': VERSION,
                   'semantic_scholar_key_configured': bool(credentials['s2']),
                   'openalex_key_configured': bool(credentials['openalex']), 'live_checked': False}
            if args.live:
                if not args.out: raise ValueError('--live requires --out for evidence')
                if not credentials['s2']: raise ValueError('Semantic Scholar API key is missing')
                http = HTTPClient(args.out / 'raw', credentials)
                paper = http.get('https://api.semanticscholar.org/graph/v1/paper/ARXIV:1706.03762', {'fields': 'title,externalIds'}, 's2')
                out.update(live_checked=True, returned_paper_id=paper.get('paperId'), returned_title=paper.get('title'))
        elif args.command == 'init': out = init_run(args.out, args.topic, args.start, args.end)
        elif args.command == 'search':
            out = search_run(args.run, credentials, args.refresh)
            exit_code = 1 if out['failed'] else 0
        elif args.command == 'import': out = import_records(args.run, args.input, args.source)
        elif args.command == 'snowball':
            out = snowball_run(args.run, credentials, args.paper_id, args.direction, args.limit)
            exit_code = 0 if out['status'] == 'ok' else 1
        elif args.command == 'audit':
            out = audit_run(args.run)
            exit_code = 0 if out['ready'] else 1
        elif args.command == 'report': out = render_report(args.run, args.strict)
        else: out = feedback(args.run, args.category, args.observation, args.proposal)
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return exit_code
    except (ValueError, OSError, ProviderError, KeyError, TypeError) as exc:
        # Avoid dumping tracebacks, response bodies, credentials or arbitrary file contents.
        message = str(exc) if isinstance(exc, (ValueError, ProviderError)) else type(exc).__name__ + ': check input paths and schema'
        for secret in locals().get('credentials', {}).values():
            if secret: message = message.replace(secret, '[REDACTED]')
        print(json.dumps({'error': message}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
