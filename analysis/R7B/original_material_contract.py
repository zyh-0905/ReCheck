#!/usr/bin/env python3
"""Download ONLY public ToolSandbox source and Linux CPython 3.11 dependencies.

No installation, imported downloaded code, LLM calls, account access, or research
experiment. Works with the host Python standard library. The Linux artifacts
are for the research assistant's container, NOT to execute on the user's PC.
"""
from __future__ import annotations
import argparse
import datetime
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import sys
import urllib.error
import urllib.parse
import urllib.request
import zipfile

VERSION = 'r7-materials-1.0'
COMMIT = 'c8571d7854316d2e1c5f288e59fe1e34e53f6dd1'
TREE = '64ccd1694a91f2029844434d5995a2c0945cd6b2'
SOURCE_URL = f'https://codeload.github.com/apple-aiml-research/ToolSandbox/zip/{COMMIT}'
PYTHON_NAME = 'cpython-3.11.14+20260203-x86_64-unknown-linux-gnu-install_only_stripped.tar.gz'
PYTHON_URL = 'https://github.com/astral-sh/python-build-standalone/releases/download/20260203/' + urllib.parse.quote(PYTHON_NAME, safe='')
PYTHON_SHA256 = 'e5696efed11346d8c53ec89587bbd3e4bce79cabdd67a62e7af60af62f01159c'
# Core local tool, state/evaluation, and tests only. Not the full cloud/LLM role stack.
PACKAGES = [
    ('polars','0.20.31'),('dill','0.3.8'),('phonenumbers','8.13.39'),('StrEnum','0.4.15'),
    ('ccy','1.3.1'),('decorator','5.1.1'),('rapidfuzz','3.9.3'),('typing_extensions','4.12.2'),
    ('python-dateutil','2.9.0.post0'),('pytz','2024.1'),('six','1.16.0'),
    ('geopy','2.4.1'),('geographiclib','2.0'),('holidays','0.51'),('pint','0.23'),
    ('requests','2.32.3'),('urllib3','2.2.2'),('idna','3.7'),
    ('charset-normalizer','3.3.2'),('certifi','2024.7.4'),
    ('numpy','1.26.4'),('networkx','3.2.1'),('scipy','1.13.1'),('attrs','23.2.0'),
    ('rouge-score','0.1.2'),('nltk','3.8.1'),('absl-py','2.1.0'),('click','8.1.7'),
    ('joblib','1.4.2'),('regex','2024.5.15'),('tqdm','4.66.4'),
    ('pydantic','2.7.4'),('pydantic_core','2.18.4'),('annotated-types','0.7.0'),
    ('PyYAML','6.0.1'),('pytest','8.2.2'),('pluggy','1.5.0'),('iniconfig','2.0.0'),
    ('packaging','23.2'),('setuptools','70.3.0'),('wheel','0.43.0'),
    ('openai','1.17.0'),('langchain-core','0.1.23'),('langsmith','0.0.87'),
    ('tenacity','8.4.1'),('jsonpatch','1.33'),('jsonpointer','2.4'),
    ('anyio','4.4.0'),('httpx','0.27.0'),('httpcore','1.0.5'),('h11','0.14.0'),
    ('distro','1.9.0'),('sniffio','1.3.1')]
ALLOW_SDIST = {('rouge-score','0.1.2')}
HOSTS = {'github.com','codeload.github.com','release-assets.githubusercontent.com',
         'objects.githubusercontent.com','pypi.org','files.pythonhosted.org'}
MAX_FILE_BYTES = 150 * 1024 * 1024
MAX_TOTAL_BYTES = 450 * 1024 * 1024

class DownloadFailure(Exception): pass

def utc_now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()

def json_bytes(obj):
    return (json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True) + '\n').encode()

def validate_url(url: str) -> str:
    p = urllib.parse.urlsplit(url)
    if p.scheme != 'https' or p.hostname not in HOSTS:
        raise ValueError('Only approved public HTTPS hosts are allowed')
    if p.username is not None or p.password is not None or p.fragment or p.port not in (None,443):
        raise ValueError('Credentials, fragments, and nonstandard ports are prohibited')
    if p.query and p.hostname not in {'release-assets.githubusercontent.com','objects.githubusercontent.com'}:
        raise ValueError('Unexpected query string')
    return p.hostname

class SafeRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        validate_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)

def pick_filename(name: str) -> str:
    if not name or name in {'.','..'} or any(c in name for c in '/\\:\x00') or len(name)>220:
        raise ValueError('Unsafe filename')
    return name

def norm_name(s): return re.sub(r'[-_.]+','-',s).lower()

def wheel_rank(filename: str) -> int:
    """Select target Linux x86_64 CPython3.11 artifacts, never the host platform."""
    if not filename.endswith('.whl'): return 0
    try: _, py, abi, platform = filename[:-4].rsplit('-',3)
    except ValueError: return 0
    py_ok = 'py3' in py.split('.') or 'cp311' in py.split('.')
    if platform == 'any':
        return 100 if py_ok and abi == 'none' else 0
    tags = platform.split('.')
    valid_platform = False
    for tag in tags:
        if not tag.endswith('_x86_64') or not tag.startswith('manylinux'): continue
        if tag in {'manylinux1_x86_64','manylinux2010_x86_64','manylinux2014_x86_64'}:
            valid_platform = True
        m = re.fullmatch(r'manylinux_(\d+)_(\d+)_x86_64', tag)
        if m and (int(m[1]),int(m[2])) <= (2,28): valid_platform = True
    if not valid_platform: return 0
    if py == 'cp311' and abi == 'cp311': return 200
    if abi == 'abi3':
        m = re.fullmatch(r'cp(\d)(\d+)',py)
        if m and (int(m[1]),int(m[2])) <= (3,11): return 180
    if py_ok and abi == 'none': return 120
    return 0

def select_release_file(meta, name, version, allow_sdist=False):
    info = meta.get('info',{})
    if norm_name(info.get('name','')) != norm_name(name) or info.get('version') != version:
        raise ValueError('PyPI release name/version mismatch')
    choices=[]
    for row in meta.get('urls',[]):
        if row.get('yanked'): continue
        fname=pick_filename(row.get('filename',''))
        score=wheel_rank(fname) if row.get('packagetype')=='bdist_wheel' else 0
        if score: choices.append((score,fname,row))
    if choices: return sorted(choices,key=lambda x:(-x[0],x[1]))[0][2]
    if allow_sdist:
        choices=[r for r in meta.get('urls',[]) if not r.get('yanked')
                 and r.get('packagetype')=='sdist' and r.get('filename','').endswith('.tar.gz')]
        if len(choices)==1: return choices[0]
    raise ValueError(f'No approved target wheel for {name}=={version}')

def verify_bytes(data, expected):
    if not re.fullmatch('[0-9a-f]{64}', expected): raise ValueError('Invalid SHA256 value')
    if hashlib.sha256(data).hexdigest() != expected: raise ValueError('SHA256 mismatch')

def git_hash(kind, data):
    return hashlib.sha1(kind.encode()+b' '+str(len(data)).encode()+b'\0'+data).digest()

def repository_tree(entries):
    root={}
    for path,(mode,data) in entries.items():
        parts=path.split('/')
        if any(x in ('','.','..') for x in parts): raise ValueError('Invalid tree path')
        cur=root
        for piece in parts[:-1]:
            if piece in cur and not isinstance(cur[piece],dict): raise ValueError('Path collision')
            cur=cur.setdefault(piece,{})
        if parts[-1] in cur: raise ValueError('Duplicate file or file-directory collision')
        cur[parts[-1]]=(mode,data)
    def digest(node):
        seq=sorted(node.items(), key=lambda kv:(kv[0]+('/' if isinstance(kv[1],dict) else '')).encode())
        data=b''
        for name,value in seq:
            if isinstance(value,dict): mode='40000'; sha=digest(value)
            else: mode,raw=value; sha=git_hash('blob',raw)
            data+=mode.encode()+b' '+name.encode()+b'\0'+sha
        return git_hash('tree',data)
    return digest(root).hex()

def verify_source_zip(raw, expected_tree):
    entries={}; seen=set(); prefix=None; total=0
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        if len(z.infolist())>3000: raise ValueError('Too many source entries')
        for item in z.infolist():
            if item.filename in seen: raise ValueError('Duplicate ZIP name')
            seen.add(item.filename)
            if '\\' in item.filename or '\x00' in item.filename or item.flag_bits&1:
                raise ValueError('Unsafe/encrypted ZIP entry')
            pieces=item.filename.rstrip('/').split('/')
            if len(pieces)<1 or any(p in ('','.','..') or ':' in p for p in pieces):
                raise ValueError('Unsafe ZIP path')
            if prefix is None: prefix=pieces[0]
            if pieces[0]!=prefix: raise ValueError('Multiple source roots')
            if item.is_dir(): continue
            if len(pieces)<2: raise ValueError('Source file outside root')
            mode=item.external_attr>>16
            if stat.S_ISLNK(mode) or stat.S_IFMT(mode) not in (0,stat.S_IFREG):
                raise ValueError('Non-regular source file')
            total+=item.file_size
            if total>100*1024*1024: raise ValueError('Source expands beyond limit')
            path='/'.join(pieces[1:])
            entries[path]=('100755' if mode&0o111 else '100644',z.read(item))
    tree=repository_tree(entries)
    if tree!=expected_tree: raise ValueError('Source Git tree differs from pinned commit')
    return {'tree_sha1':tree,'file_count':len(entries),'uncompressed_bytes':total,
            'sha256':hashlib.sha256(raw).hexdigest()}

def safe_error(exc):
    # Do not log potentially credential-bearing proxy, URL query, or local paths.
    if isinstance(exc, urllib.error.HTTPError): return f'HTTPError status {exc.code}'
    if isinstance(exc, urllib.error.URLError): return 'URLError: network/TLS/name-resolution failure'
    return f'{type(exc).__name__}: operation failed (sensitive detail omitted)'

def build_bundle(root, relpaths, output, report):
    if output.exists(): raise FileExistsError('Output already exists')
    root=root.resolve(); files={}
    for rel in relpaths:
        pp=PurePosixPath(rel)
        if pp.is_absolute() or '..' in pp.parts or '\\' in rel: raise ValueError('Unsafe bundle path')
        p=root/rel
        if p.is_symlink() or not p.is_file() or root not in p.resolve().parents:
            raise ValueError('Unsafe bundle file')
        files[rel]=p.read_bytes()
    files['DOWNLOAD_REPORT.json']=json_bytes(report)
    manifest={'format':'sha256-file-index-v1','files':{
        k:{'sha256':hashlib.sha256(v).hexdigest(),'bytes':len(v)} for k,v in sorted(files.items())}}
    with zipfile.ZipFile(output,'x',compression=zipfile.ZIP_STORED) as z:
        for k,v in sorted(files.items()): z.writestr(k,v)
        z.writestr('BUNDLE_MANIFEST.json',json_bytes(manifest))
    return manifest

class Downloader:
    def __init__(self):
        self.opener=urllib.request.build_opener(SafeRedirect())
        self.total=0
    def get(self,url,target,limit=MAX_FILE_BYTES,sha256=None,expected_size=None):
        validate_url(url)
        if target.exists() or target.with_suffix(target.suffix+'.partial').exists():
            raise FileExistsError('Refuse overwrite')
        target.parent.mkdir(parents=True,exist_ok=True)
        partial=target.with_suffix(target.suffix+'.partial')
        request=urllib.request.Request(url,headers={'User-Agent':VERSION,'Accept-Encoding':'identity'})
        n=0; h=hashlib.sha256()
        with self.opener.open(request,timeout=90) as response, partial.open('xb') as f:
            validate_url(response.geturl())
            declared=response.headers.get('Content-Length')
            if declared and int(declared)>limit: raise DownloadFailure('Declared file size exceeds limit')
            while True:
                chunk=response.read(1024*1024)
                if not chunk: break
                n+=len(chunk); self.total+=len(chunk)
                if n>limit or self.total>MAX_TOTAL_BYTES: raise DownloadFailure('Size limit')
                h.update(chunk); f.write(chunk)
        if expected_size is not None and n!=expected_size: raise DownloadFailure('Size mismatch')
        if sha256 is not None and h.hexdigest()!=sha256: raise DownloadFailure('SHA mismatch')
        partial.rename(target)
        return {'bytes':n,'sha256':h.hexdigest()}

def collect(output_parent: Path, downloader=None):
    output_parent.mkdir(parents=True,exist_ok=True)
    workspace=output_parent/'R7_materials_work'
    # Never silently repeat an unsuccessful or completed collection.
    workspace.mkdir(exist_ok=False)
    listed=[]; report={'version':VERSION,'started_utc':utc_now(),'status':'IN_PROGRESS',
        'purpose':'PUBLIC_MATERIAL_DOWNLOAD_ONLY_NOT_EXPERIMENT',
        'target':'Linux x86_64 CPython 3.11; NOT the host operating system',
        'new_llm_calls':0,'downloaded_code_executed':False,'packages_installed':False,
        'source_commit':COMMIT,'source_git_tree':TREE,'artifacts':[],
        'pypi_hash_scope':'Each pinned release metadata is saved; digest verified against PyPI over TLS. '
                           'Not all dependency hashes were known before collection.',
        'native_status':'NOT_RUN; CPU local tool/evaluation dependency subset, not full provider role stack'}
    d=downloader or Downloader()
    stage='source'
    try:
        source_path=workspace/'source'/f'ToolSandbox-{COMMIT}.zip'
        artifact=d.get(SOURCE_URL,source_path,limit=100*1024*1024)
        artifact.update(verify_source_zip(source_path.read_bytes(),TREE))
        listed.append(source_path.relative_to(workspace).as_posix())
        report['artifacts'].append({'kind':'source','url':SOURCE_URL,**artifact})
        stage='linux_python_runtime'
        py=workspace/'runtime'/PYTHON_NAME
        artifact=d.get(PYTHON_URL,py,sha256=PYTHON_SHA256)
        listed.append(py.relative_to(workspace).as_posix())
        report['artifacts'].append({'kind':'python_runtime','url':PYTHON_URL,**artifact})
        for i,(name,version) in enumerate(PACKAGES,1):
            stage=f'package_{i}_{name}_{version}'
            print(f'[{i}/{len(PACKAGES)}] Downloading {name}=={version}',flush=True)
            url=f'https://pypi.org/pypi/{urllib.parse.quote(name,safe="")}/{version}/json'
            mp=workspace/'metadata'/f'{norm_name(name)}-{version}.json'
            d.get(url,mp,limit=4*1024*1024)
            listed.append(mp.relative_to(workspace).as_posix())
            meta=json.loads(mp.read_text(encoding='utf-8'))
            row=select_release_file(meta,name,version,(name,version) in ALLOW_SDIST)
            fname=pick_filename(row['filename']); expected=row['digests']['sha256']
            if not re.fullmatch('[0-9a-f]{64}',expected): raise ValueError('Missing file digest')
            fp=workspace/'packages'/fname
            artifact=d.get(row['url'],fp,sha256=expected,expected_size=row['size'])
            listed.append(fp.relative_to(workspace).as_posix())
            report['artifacts'].append({'kind':'package','name':name,'version':version,
                'filename':fname,'url':row['url'],'requires_python':row.get('requires_python'),**artifact})
        report['status']='MATERIALS_COLLECTED_NOT_INSTALLED'
    except Exception as exc:
        report['status']='INCOMPLETE_DOWNLOAD'
        report['failure']={'stage':stage,'exception':safe_error(exc)}
        print('Collection stopped. No files or packages were installed. Exporting available materials.',flush=True)
    report['finished_utc']=utc_now()
    report['downloaded_bytes']=d.total
    rp=workspace/'COLLECTION_REPORT.json'; rp.write_bytes(json_bytes(report))
    # Script itself is evidence of what was requested, not executed dependencies.
    sp=workspace/'collector_used.py'; sp.write_bytes(Path(__file__).read_bytes())
    listed += ['COLLECTION_REPORT.json','collector_used.py']
    stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    out=output_parent/f'R7_materials_{stamp}.zip'
    build_bundle(workspace,listed,out,report)
    print(report['status']); print(out.resolve())
    return 0 if report['status']=='MATERIALS_COLLECTED_NOT_INSTALLED' else 2

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--allow-public-downloads',action='store_true',
                        help='Allow public HTTPS downloads only, without account/model requests')
    args=parser.parse_args()
    if not args.allow_public_downloads:
        parser.error('Use --allow-public-downloads to explicitly allow the public material downloads.')
    try: return collect(Path(__file__).resolve().parent/'uploads')
    except FileExistsError:
        print('Existing R7_materials_work: do not delete or retry blindly. Upload the existing result ZIP.',file=sys.stderr)
        return 2

if __name__=='__main__': sys.exit(main())
