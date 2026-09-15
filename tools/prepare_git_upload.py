#!/usr/bin/env python3
"""Verify an archive and optionally stage its exact bytes. Never commit or push.

Use --stage only in a checked-out zyh-0905/ReCheck repository. Staging bypasses
historical .gitignore/.gitattributes and Git clean filters. Local Git metadata is
changed only by --stage; original research files are never rewritten.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from verify_archive import verify, safe_relative

TARGET='zyh-0905/ReCheck'
ALLOWED_ORIGINS={f'https://github.com/{TARGET}',f'https://github.com/{TARGET}.git',
                 f'git@github.com:{TARGET}',f'git@github.com:{TARGET}.git',
                 f'ssh://git@github.com/{TARGET}',f'ssh://git@github.com/{TARGET}.git'}

def validate_origin(url:str)->bool:
    if url.strip() not in ALLOWED_ORIGINS:
        raise ValueError('origin must be the specified ReCheck repository without embedded credentials')
    return True

def git(root:Path,*args:str,data:bytes|None=None)->bytes:
    p=subprocess.run(['git',*args],cwd=root,input=data,stdout=subprocess.PIPE,
                     stderr=subprocess.PIPE,timeout=180,check=False)
    if p.returncode:
        # Avoid printing remote URLs, configuration contents, or credentials.
        raise ValueError(f'Local Git command {args[0]!r} failed (exit {p.returncode})')
    return p.stdout

def expected_oids(root:Path,paths:list[str],algorithm:str)->dict[str,str]:
    result={}
    for name in paths:
        p=root/name
        h=hashlib.new(algorithm)
        h.update(f'blob {p.stat().st_size}\0'.encode('ascii'))
        with p.open('rb') as f:
            for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
        result[name]=h.hexdigest()
    return result

def read_index(root:Path)->dict[str,str]:
    result={}
    for entry in git(root,'ls-files','--stage','-z').split(b'\0'):
        if not entry:continue
        head,name=entry.split(b'\t',1)
        mode,oid,stage=head.split()
        if stage!=b'0':raise ValueError('Unmerged entries exist; resolve them before staging')
        result[name.decode('utf8')]=oid.decode('ascii')
    return result

def prepare(root:Path,stage:bool=False,check_index:bool=False)->dict:
    root=Path(root).resolve()
    result=verify(root)
    entries=json.loads((root/'ARCHIVE_MANIFEST.json').read_text(encoding='utf8'))['files']
    paths=sorted([e['path'] for e in entries]+['ARCHIVE_MANIFEST.json'])
    for name in paths:
        safe_relative(name)
        if '\n' in name or '\r' in name or name.startswith('"'):
            raise ValueError('Path not supported by exact-byte Git staging')
    result.update(files_to_stage=len(paths),target_repository=TARGET,
                  local_index_modified=False,remote_actions=0)
    if not stage and not check_index:return result
    gitroot=Path(git(root,'rev-parse','--show-toplevel').decode('utf8').strip()).resolve()
    if gitroot!=root:raise ValueError('Archive root must be the repository root, not a subdirectory')
    validate_origin(git(root,'remote','get-url','origin').decode('utf8').strip())
    algo=git(root,'rev-parse','--show-object-format').decode('ascii').strip()
    if algo not in {'sha1','sha256'}:raise ValueError('Unsupported Git object format')
    expected=expected_oids(root,paths,algo)
    index=read_index(root)
    already=all(index.get(n)==oid for n,oid in expected.items())
    if stage and not already:
        staged=git(root,'diff','--cached','--name-only','-z')
        if staged:raise ValueError('Index already has staged changes; preserve or commit them first')
        got=git(root,'hash-object','-w','--no-filters','--stdin-paths',
                data='\n'.join(paths).encode('utf8')+b'\n').decode('ascii').splitlines()
        if got!=[expected[n] for n in paths]:raise ValueError('Git object bytes did not match the archive')
        records=b''.join(f'100644 {expected[n]}\t{n}\0'.encode('utf8') for n in paths)
        git(root,'update-index','--add','-z','--index-info',data=records)
        result['local_index_modified']=True
        index=read_index(root)
    if not all(index.get(n)==oid for n,oid in expected.items()):
        raise ValueError('The Git index does not contain every verified archive file')
    result.update(index_verified_files=len(paths),git_object_format=algo,already_staged=already)
    return result

def main()->int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1])
    group=parser.add_mutually_exclusive_group()
    group.add_argument('--stage',action='store_true',help='Explicitly write the local Git index; no commit or push')
    group.add_argument('--check-index',action='store_true',help='Verify existing index without changing it')
    args=parser.parse_args()
    try:
        result=prepare(args.root,stage=args.stage,check_index=args.check_index)
    except (ValueError,OSError,subprocess.TimeoutExpired) as e:
        print(f'PREPARATION FAILED: {e}',file=sys.stderr);return 1
    print(json.dumps(result,ensure_ascii=False,indent=2));return 0
if __name__=='__main__':raise SystemExit(main())
