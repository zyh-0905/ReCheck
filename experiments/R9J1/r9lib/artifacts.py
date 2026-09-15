
"""Frozen source/protocol binding, safe allowlisted export; no remote calls."""
from pathlib import Path
import json,hashlib,zipfile,stat,re
from datetime import datetime,timezone
from pilot.common import read_json,write_json,digest
ROOT_FILES=('r9.py','requirements.txt','config.example.json','protocol.json','README_ZH.md',
 'EXECUTION_PROMPT_ZH.md','LICENSE','UPSTREAM_MANIFEST.json')
ROOT_DIRS=('r9lib','pilot','tests','fixtures','vendor','docs','scripts')
def source_paths(root):
 root=Path(root)
 files=[root/x for x in ROOT_FILES if (root/x).is_file()]
 for d in ROOT_DIRS:
  if not (root/d).exists():continue
  for p in (root/d).rglob('*'):
   if any(x in p.parts for x in ('__pycache__','.pytest_cache','.git')) or p.suffix in ('.pyc','.pyo'):continue
   if p.is_symlink():raise ValueError('Source symlink')
   if p.is_file():files.append(p)
 return sorted(set(files))
def source_hashes(root):
 root=Path(root)
 return {p.relative_to(root).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in source_paths(root)}
def verify_distribution(root):
 root=Path(root);p=root/'SOURCE_MANIFEST.json'
 if not p.exists():raise ValueError('Missing source manifest')
 actual=source_hashes(root)
 if read_json(p)['sha256']!=actual:raise ValueError('Source/protocol/fixture changed. No paid calls allowed.')
 up=read_json(root/'UPSTREAM_MANIFEST.json')
 for n,h in up['sha256'].items():
  if actual.get('vendor/toolsandbox/'+n)!=h:raise ValueError('Upstream altered')
 return {'pass':True,'files':len(actual),'source_manifest_sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
def sensitive(data):
 s=data.decode('utf8','replace')
 return any(re.search(p,s) for p in (r'sk-[A-Za-z0-9_-]{20,}',r'(?i)bearer\s+[A-Za-z0-9_.-]{20,}',r'-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----'))
def export_bundle(root,out=None):
 root=Path(root).resolve()
 if out is None:out=root/'uploads'/('R9J1_feedback_'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'.zip')
 out=Path(out);files={}
 def add(p,name):
  if p.is_symlink() or any(q.is_symlink() for q in p.parents if q!=root.parent):raise ValueError('Symlink rejected')
  data=p.read_bytes()
  if sensitive(data):raise ValueError('Credential-like text detected; export blocked, do not delete evidence to bypass')
  files[name]=data
 for p in source_paths(root):add(p,'kit_source/'+p.relative_to(root).as_posix())
 if (root/'SOURCE_MANIFEST.json').exists():add(root/'SOURCE_MANIFEST.json','kit_source/SOURCE_MANIFEST.json')
 for base in ('runs/R9_smoke','runs/R9_main','offline_reports'):
  d=root/base
  if not d.exists():continue
  for p in sorted(d.rglob('*')):
   if p.is_symlink():raise ValueError('Symlink rejected')
   if not p.is_file() or p.suffix not in ('.json','.jsonl','.csv','.md','.txt'):continue
   if any(x.startswith('.') for x in p.relative_to(d).parts):continue
   if p.name in ('config.local.json','.env','billing.local.json'):continue
   add(p,p.relative_to(root).as_posix())
 if (root/'PREPARED.json').exists():add(root/'PREPARED.json','PREPARED.json')
 m={'task_id':'R9J1_LIVE_CONTINUATION_DIAGNOSIS_01','sha256':{k:hashlib.sha256(v).hexdigest() for k,v in sorted(files.items())},
    'status':'PENDING_RESEARCHER_REVIEW','security_note':'Hash consistency is not provider or billing authentication'}
 out.parent.mkdir(parents=True,exist_ok=True)
 with zipfile.ZipFile(out,'x',zipfile.ZIP_DEFLATED) as z:
  for n,b in sorted(files.items()):z.writestr(n,b)
  z.writestr('BUNDLE_MANIFEST.json',json.dumps(m,indent=2))
 verify_bundle(out);return out
def verify_bundle(path):
 with zipfile.ZipFile(path) as z:
  names=z.namelist()
  if len(names)!=len(set(names)):raise ValueError('Duplicate archive entries')
  if sum(i.file_size for i in z.infolist())>750_000_000:raise ValueError('Archive too large')
  for i in z.infolist():
   p=Path(i.filename)
   if p.is_absolute() or '..' in p.parts or '\\' in i.filename or stat.S_ISLNK(i.external_attr>>16):raise ValueError('Unsafe archive')
  m=json.loads(z.read('BUNDLE_MANIFEST.json'))
  if set(names)!=set(m['sha256'])|{'BUNDLE_MANIFEST.json'}:raise ValueError('File set mismatch')
  for n,h in m['sha256'].items():
   if hashlib.sha256(z.read(n)).hexdigest()!=h:raise ValueError('Digest mismatch')
 return {'pass':True,'files':len(m['sha256'])}
