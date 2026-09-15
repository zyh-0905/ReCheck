#!/usr/bin/env python3
"""Download immutable public research JSON. No LLM calls or downloaded-code execution.

Python >= 3.9, standard library only. Default invocation is offline.
Run once: python3 download_public.py --download
A failed transfer still exports the files already received, without retrying.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
import time
from datetime import datetime, timezone
from typing import Callable
from urllib.parse import quote
from urllib.request import Request, urlopen
import zipfile

REVISION = '593e686f4d0c2e9fcae5ae664c16a7687907cf97'
REPOSITORY = 'SAP/agent-quality-inspect'
MODELS = ('gpt_4_1', 'gpt_4o', 'gpt_4o_mini', 'gpt_5',
          'mistral_large_2411', 'mistral_nemo')
PERSONAS = ('expert', 'nonexpert')
MAX_FILE_BYTES = 32 * 1024 * 1024
MAX_TOTAL_BYTES = 512 * 1024 * 1024
MAX_SECONDS = 20 * 60
PROTOCOL = 'R14_PUBLIC_JSON_TRANSFER_01'


def planned_paths() -> list[str]:
    """Fixed coverage, independent of outcomes; no pickle or model weights."""
    paths = ['README.md']
    for model in MODELS:
        for persona in PERSONAS:
            folder = f'toolsandbox/{model}/{persona}'
            paths += [f'{folder}/trial_{i}_results.json' for i in range(8)]
            paths.append(f'{folder}/aggregate_metrics_results.json')
    return paths


def source_url(path: str) -> str:
    if path not in planned_paths():
        raise ValueError('Path is outside the fixed public-data allowlist')
    return (f'https://huggingface.co/datasets/{REPOSITORY}/resolve/'
            f'{REVISION}/{quote(path, safe="/")}')


def validate_commit(headers: dict) -> None:
    supplied = {str(k).lower(): str(v) for k, v in headers.items()}.get('x-repo-commit')
    if supplied is not None and supplied != REVISION:
        raise ValueError('The response identifies a different repository revision')


def validate_payload(path: str, body: bytes) -> dict:
    source_url(path)  # also enforces the path allowlist
    if len(body) > MAX_FILE_BYTES:
        raise ValueError('File exceeds the byte limit')
    text = body.decode('utf-8')
    if path == 'README.md':
        if 'apache-2.0' not in text.lower():
            raise ValueError('Expected Apache-2.0 dataset-card declaration was not found')
        return {'kind': 'dataset_card'}
    obj = json.loads(text)
    if not isinstance(obj, dict):
        raise ValueError('Expected a JSON object; original bytes are not repaired')
    if '/trial_' not in path:
        if 'metrics' not in obj:
            raise ValueError('Expected aggregate metrics object')
        return {'kind': 'aggregate'}
    trial = int(Path(path).stem.split('_')[1])
    if obj.get('trial_id') != trial or not isinstance(obj.get('samples'), list):
        raise ValueError('Trial identity or samples schema does not match the requested file')
    # Preserve reported status and metrics; collecting a file does not score its tasks.
    return {'kind': 'trial', 'trial_id': trial,
            'sample_count': len(obj['samples']),
            'declared_total_samples': obj.get('total_samples'),
            'reported_agent_model': obj.get('agent_model'),
            'reported_user_persona': obj.get('user_proxy_persona')}


def https_fetch(url: str) -> tuple[bytes, dict]:
    """Public unauthenticated GET; use system TLS trust, no cookie or token store."""
    request = Request(url, headers={'User-Agent': 'R14-Public-Research-Data/1.0',
                                    'Accept-Encoding': 'identity'}, method='GET')
    started = time.monotonic()
    with urlopen(request, timeout=30) as response:
        if response.status != 200:
            raise ValueError(f'Unexpected HTTP status: {response.status}')
        length = response.headers.get('Content-Length')
        if length is not None and int(length) > MAX_FILE_BYTES:
            raise ValueError('Remote file exceeds the byte limit')
        parts, size = [], 0
        while True:
            chunk = response.read(256 * 1024)
            if not chunk:
                break
            size += len(chunk)
            if size > MAX_FILE_BYTES or time.monotonic() - started > 180:
                raise ValueError('Transfer exceeded file size or time limit')
            parts.append(chunk)
        body = b''.join(parts)
        if length is not None and len(body) != int(length):
            raise ValueError('Incomplete HTTP response body')
        # Deliberately omit cookies, credentials and signed-redirect query strings.
        headers = {k.lower(): response.headers[k] for k in
                   ('ETag', 'Content-Length', 'X-Repo-Commit', 'Last-Modified')
                   if k in response.headers}
    return body, headers


def collect(out: Path, fetch: Callable = https_fetch, quiet: bool = False) -> dict:
    out = Path(out)
    out.mkdir(parents=True, exist_ok=False)  # no overwrites and no accidental resampling
    raw = out / 'raw'
    raw.mkdir()
    script_bytes = Path(__file__).read_bytes()
    (out / 'collector_used.py').write_bytes(script_bytes)
    rows, errors, total = [], [], 0
    begun = datetime.now(timezone.utc)
    started = time.monotonic()
    roster = planned_paths()
    for path in roster:
        try:
            if time.monotonic() - started > MAX_SECONDS:
                raise TimeoutError('Overall transfer time limit reached')
            body, headers = fetch(source_url(path))
            validate_commit(headers)
            metadata = validate_payload(path, body)
            if total + len(body) > MAX_TOTAL_BYTES:
                raise ValueError('Total byte limit reached')
            destination = raw / path
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(body)
            total += len(body)
            rows.append({'path': path, 'url': source_url(path), 'bytes': len(body),
                         'sha256': hashlib.sha256(body).hexdigest(),
                         'response_headers': headers, 'metadata': metadata})
            if not quiet:
                print(f'[{len(rows)}/{len(roster)}] {path} ({len(body)} bytes)', flush=True)
        except (Exception, KeyboardInterrupt) as exc:
            # No automatic retries and no substitution with another revision or mirror.
            error = {'path': path, 'type': type(exc).__name__}
            code = getattr(exc, 'code', None)
            if isinstance(code, int):
                error['http_status'] = code
            errors.append(error)
            if not quiet:
                print(f'Stopped: {error}. Exporting partial download.', flush=True)
            break
    status = 'COMPLETE' if len(rows) == len(roster) else 'INCOMPLETE'
    acquired = {r['path'] for r in rows}
    manifest = {'protocol': PROTOCOL, 'repository': REPOSITORY,
                'revision': REVISION, 'status': status,
                'new_llm_calls': 0, 'research_tasks_executed': 0,
                'started_utc': begun.isoformat(),
                'finished_utc': datetime.now(timezone.utc).isoformat(),
                'requested_files': roster, 'files': rows,
                'missing_files': [p for p in roster if p not in acquired],
                'errors': errors, 'total_downloaded_bytes': total,
                'collector_sha256': hashlib.sha256(script_bytes).hexdigest(),
                'hash_scope': 'Local raw-byte SHA256; not a provider signature or independent provenance authentication'}
    (out / 'MANIFEST.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    uploads = out.parent / 'uploads'
    uploads.mkdir(exist_ok=True)
    archive = uploads / ('R14_public_data_' + begun.strftime('%Y%m%dT%H%M%S%fZ') + '.zip')
    with zipfile.ZipFile(archive, 'x', zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for name in ('MANIFEST.json', 'collector_used.py'):
            z.write(out / name, name)
        for row in rows:
            z.write(raw / row['path'], 'raw/' + row['path'])
    checked = verify_archive(archive)
    return {'status': status, 'acquired_files': len(rows),
            'trial_files': sum(r['metadata']['kind']=='trial' for r in rows),
            'archive': str(archive.resolve()), 'archive_verification': checked}


def verify_archive(path: Path) -> dict:
    """Read and validate only; never extract or execute the archived collector."""
    with zipfile.ZipFile(path) as z:
        names = z.namelist()
        if len(names) != len(set(names)):
            raise ValueError('Duplicate ZIP paths')
        m = json.loads(z.read('MANIFEST.json'))
        if m.get('revision') != REVISION or m.get('protocol') != PROTOCOL:
            raise ValueError('Unexpected protocol or revision')
        if m.get('requested_files') != planned_paths():
            raise ValueError('Changed selection roster')
        got = [r['path'] for r in m['files']]
        if len(set(got)) != len(got) or any(p not in planned_paths() for p in got):
            raise ValueError('Duplicate or unexpected manifest paths')
        if set(names) != {'MANIFEST.json', 'collector_used.py'} | {'raw/'+p for p in got}:
            raise ValueError('Manifest and ZIP entries do not correspond')
        if hashlib.sha256(z.read('collector_used.py')).hexdigest() != m['collector_sha256']:
            raise ValueError('Collector bytes changed')
        for row in m['files']:
            data = z.read('raw/'+row['path'])
            if len(data) != row['bytes'] or hashlib.sha256(data).hexdigest() != row['sha256']:
                raise ValueError('Raw-file hash or size mismatch: '+row['path'])
        missing = [p for p in planned_paths() if p not in set(got)]
        expected_status = 'COMPLETE' if not missing else 'INCOMPLETE'
        if m.get('missing_files') != missing or m.get('status') != expected_status:
            raise ValueError('Coverage or status is inconsistent')
        if m.get('total_downloaded_bytes') != sum(r['bytes'] for r in m['files']):
            raise ValueError('Total byte count is inconsistent')
    return {'verified': True, 'files': len(got), 'status': expected_status}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--download', action='store_true', help='Allow fixed public-file GETs; no LLM inference')
    group.add_argument('--verify', type=Path, metavar='ZIP', help='Offline raw-byte archive verification')
    args = parser.parse_args()
    if args.verify:
        print(json.dumps(verify_archive(args.verify), indent=2))
        return 0
    if not args.download:
        print(f'No network used. Planned: 96 existing trial JSONs + 12 aggregates + README; revision {REVISION}.')
        parser.print_help()
        return 0
    try:
        result = collect(Path(__file__).resolve().parent / 'R14_public_data')
    except FileExistsError:
        print('R14_public_data already exists. Do not overwrite. Return the existing uploads/R14_public_data_*.zip.')
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    print('Upload the ZIP printed above, including when status is INCOMPLETE. No experiment was run.')
    return 0 if result['status']=='COMPLETE' else 2


if __name__ == '__main__':
    raise SystemExit(main())
