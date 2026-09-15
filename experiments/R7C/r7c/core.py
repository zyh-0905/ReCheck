"""Small strict serialization and archive helpers. No network or credential access."""
from __future__ import annotations
import hashlib,json,math,os,tempfile,zipfile,stat
from datetime import datetime,timezone
from pathlib import Path,PurePosixPath

ROOT=Path(__file__).resolve().parents[1]
UPSTREAM_COMMIT='c8571d7854316d2e1c5f288e59fe1e34e53f6dd1'
MAX_STEPS=6
MAIN_CAP=432
TOTAL_CAP=433
METHODS=('no_memory','memory_standard','memory_verify')

def canonical(x):return json.dumps(x,sort_keys=True,ensure_ascii=False,separators=(',',':'),allow_nan=False)
def digest(x):return hashlib.sha256(canonical(x).encode('utf-8')).hexdigest()
def file_sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def utcnow():return datetime.now(timezone.utc).isoformat()
def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def write(p,x):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
 data=json.dumps(x,ensure_ascii=False,sort_keys=True,indent=2,allow_nan=False)+'\n'
 tmp=p.with_name(p.name+'.tmp');tmp.write_text(data,encoding='utf-8');os.replace(tmp,p)
def write_once(p,x):
 p=Path(p)
 if p.exists():
  if read(p)!=x:raise ValueError('Immutable file mismatch: '+p.name)
 else:write(p,x)
def strict_json(s):
 def pairs(items):
  d={}
  for k,v in items:
   if k in d:raise ValueError('Duplicate JSON key')
   d[k]=v
  return d
 def bad(v):raise ValueError('Non-finite JSON')
 x=json.loads(s,object_pairs_hook=pairs,parse_constant=bad)
 if type(x) is not dict:raise ValueError('Expected JSON object')
 canonical(x)
 return x

def action(x):
 if type(x) is not dict:raise ValueError('Action must be an object')
 if x.get('action')=='finish':
  if set(x)!={'action','summary'} or type(x['summary']) is not str or len(x['summary'])>4000:raise ValueError('Invalid finish')
 elif x.get('action')=='tool':
  if set(x)!={'action','name','arguments'} or type(x['name']) is not str or type(x['arguments']) is not dict:raise ValueError('Invalid tool action')
  if not x['name'].isidentifier() or len(canonical(x['arguments']))>12000:raise ValueError('Invalid tool name/argument size')
 else:raise ValueError('Unknown action')
 return x

def safe_unzip(zpath,dest):
 dest=Path(dest);dest.mkdir(parents=True,exist_ok=True)
 with zipfile.ZipFile(zpath) as z:
  names=set();total=0
  for i in z.infolist():
   p=PurePosixPath(i.filename);mode=i.external_attr>>16
   if p.is_absolute() or '..' in p.parts or '\\' in i.filename or i.filename in names or stat.S_ISLNK(mode) or i.flag_bits&1:raise ValueError('Unsafe zip entry')
   names.add(i.filename);total+=i.file_size
   if i.file_size>12_000_000 or total>80_000_000:raise ValueError('Oversized source zip')
  z.extractall(dest)

def source_manifest(root=ROOT):
 files={}
 for p in sorted(Path(root).rglob('*')):
  rel=p.relative_to(root)
  if not p.is_file() or any(x in ('.venv','__pycache__','_vendor','runs','uploads','offline_reports','.git','.pytest_cache') for x in rel.parts):continue
  if rel.as_posix() in ('SOURCE_MANIFEST.json','PREPARED.json'):continue
  if p.suffix in ('.pyc',) or p.name=='.DS_Store':continue
  files[rel.as_posix()]={'sha256':file_sha(p),'bytes':p.stat().st_size}
 return {'files':files}

def verify_sources(root=ROOT):
 root=Path(root);ref=read(root/'SOURCE_MANIFEST.json');actual=source_manifest(root)
 if actual!=ref:raise ValueError('Source/protocol integrity mismatch; do not edit files to continue')
 return {'pass':True,'files':len(ref['files']),'manifest_sha256':file_sha(root/'SOURCE_MANIFEST.json')}

def ensure_upstream():
 import sys
 arc=ROOT/'upstream'/('ToolSandbox-'+UPSTREAM_COMMIT+'.zip')
 dest=ROOT/'_vendor';src=dest/('ToolSandbox-'+UPSTREAM_COMMIT)
 if not src.exists():safe_unzip(arc,dest)
 # Detect any modified original file before import, not only the archive hash.
 with zipfile.ZipFile(arc) as z:
  for i in z.infolist():
   if i.is_dir():continue
   p=dest/i.filename
   if not p.is_file() or p.read_bytes()!=z.read(i):raise ValueError('Expanded upstream source changed')
 if str(src) not in sys.path:sys.path.insert(0,str(src))
 return src
