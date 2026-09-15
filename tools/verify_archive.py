#!/usr/bin/env python3
"""Verify the deposited archive without running research or accessing the network.

This is an integrity check, not scientific re-evaluation or a privacy certification.
The manifest is intentionally not self-hashed. Its SHA-256 is recorded in the
separate delivery verification supplied with the repository archive.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import sys

FONT_SUFFIXES = {'.ttf', '.otf', '.ttc', '.woff', '.woff2', '.pfb', '.pfa', '.afm'}
IGNORED_PARTS = {'.git', '__pycache__', '.pytest_cache'}
IGNORED_NAMES = {'.DS_Store'}


def safe_relative(value: str) -> PurePosixPath:
    if not isinstance(value, str) or not value or '\\' in value or ':' in value or '\0' in value:
        raise ValueError('Invalid relative path')
    if value.startswith('/') or any(p in {'', '.', '..'} for p in value.split('/')):
        raise ValueError('Unsafe relative path')
    return PurePosixPath(value)


def digest_file(path: Path) -> str:
    h=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024), b''):
            h.update(chunk)
    return h.hexdigest()


def ignored(relative: Path) -> bool:
    return bool(set(relative.parts) & IGNORED_PARTS) or relative.name in IGNORED_NAMES


def verify(root: Path) -> dict:
    root=Path(root).resolve()
    manifest_path=root/'ARCHIVE_MANIFEST.json'
    if not manifest_path.is_file() or manifest_path.is_symlink():
        raise ValueError('Missing or invalid ARCHIVE_MANIFEST.json')
    try:
        manifest=json.loads(manifest_path.read_text(encoding='utf-8'))
        entries=manifest['files']
    except (ValueError, KeyError, TypeError) as exc:
        raise ValueError('Invalid manifest structure') from exc
    if not isinstance(entries,list): raise ValueError('files must be a list')
    seen=set(); total_bytes=0
    for entry in entries:
        if not isinstance(entry,dict): raise ValueError('Invalid file entry')
        rel=safe_relative(entry.get('path'))
        p=root.joinpath(*rel.parts)
        key=rel.as_posix()
        if key in seen or key=='ARCHIVE_MANIFEST.json': raise ValueError(f'Duplicate/self entry: {key}')
        seen.add(key)
        if rel.suffix.lower() in FONT_SUFFIXES or rel.name in {'.env','id_rsa','id_ed25519'}:
            raise ValueError(f'Forbidden file type/name: {key}')
        if type(entry.get('bytes')) is not int or entry['bytes']<0:
            raise ValueError(f'Invalid size: {key}')
        if not isinstance(entry.get('sha256'),str) or not re.fullmatch(r'[a-f0-9]{64}',entry['sha256']):
            raise ValueError(f'Invalid digest: {key}')
        if not p.is_file() or any(q.is_symlink() for q in [p,*p.parents] if q!=root):
            raise ValueError(f'Missing file or symlink: {key}')
        if p.stat().st_size!=entry['bytes'] or digest_file(p)!=entry['sha256']:
            raise ValueError(f'Integrity mismatch: {key}')
        total_bytes+=entry['bytes']
    actual=set()
    for p in root.rglob('*'):
        rel=p.relative_to(root)
        if ignored(rel): continue
        if p.is_symlink(): raise ValueError(f'Unexpected symlink: {rel}')
        if p.is_file() and rel.as_posix()!='ARCHIVE_MANIFEST.json': actual.add(rel.as_posix())
    if actual!=seen:
        raise ValueError(f'Unregistered/missing files: extra={sorted(actual-seen)[:5]}, missing={sorted(seen-actual)[:5]}')
    return {'integrity_pass':True,'verified_files':len(seen),'verified_bytes':total_bytes,
            'manifest_sha256':digest_file(manifest_path),'new_model_calls':0,
            'scientific_results_reexecuted':False}


def main() -> int:
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1])
    args=ap.parse_args()
    try:
        result=verify(args.root)
    except (ValueError,OSError) as exc:
        print(f'ARCHIVE VERIFICATION FAILED: {exc}',file=sys.stderr); return 1
    print(json.dumps(result,ensure_ascii=False,indent=2));return 0

if __name__=='__main__': raise SystemExit(main())
