"""Whitelisted export; immutable originals are retained."""
from pathlib import Path
import zipfile,hashlib,re
from datetime import datetime,timezone
from .core import ROOT,read,canonical,source_manifest

def export(root=ROOT):
 root=Path(root);out=root/'uploads';out.mkdir(exist_ok=True)
 files={}
 for rel in read(root/'SOURCE_MANIFEST.json')['files']:
  files['kit_source/'+rel]=root/rel
 files['kit_source/SOURCE_MANIFEST.json']=root/'SOURCE_MANIFEST.json'
 if (root/'PREPARED.json').exists():files['PREPARED.json']=root/'PREPARED.json'
 for folder in ('runs','offline_reports'):
  for p in (root/folder).rglob('*') if (root/folder).exists() else []:
   if p.is_file() and p.name!='.write.lock' and '__pycache__' not in p.parts:
    files[p.relative_to(root).as_posix()]=p
 manifest={}
 for rel,p in files.items():
  if p.is_symlink():raise ValueError('Export symlink rejected')
  raw=p.read_bytes()
  if p.suffix in ('.json','.md','.txt','.csv'):
   text=raw.decode('utf-8','replace')
   if re.search(r'sk-[A-Za-z0-9]{24,}|-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----|Bearer [A-Za-z0-9_\-.]{24,}',text):raise ValueError('Possible credential in export; retained locally for review')
  manifest[rel]={'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)}
 path=out/('R7C_feedback_'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'.zip')
 with zipfile.ZipFile(path,'x',zipfile.ZIP_DEFLATED) as z:
  for rel,p in files.items():z.write(p,rel)
  z.writestr('BUNDLE_MANIFEST.json',canonical({'files':manifest}))
 return path

def verify_bundle(path):
 with zipfile.ZipFile(path) as z:
  import json
  manifest=json.loads(z.read('BUNDLE_MANIFEST.json'))['files']
  if len(z.namelist())!=len(set(z.namelist())) or set(z.namelist())!={*manifest,'BUNDLE_MANIFEST.json'}:raise ValueError('Bundle membership mismatch')
  for n,v in manifest.items():
   if n.startswith('/') or '..' in Path(n).parts:raise ValueError('Unsafe bundle path')
   b=z.read(n)
   if len(b)!=v['bytes'] or hashlib.sha256(b).hexdigest()!=v['sha256']:raise ValueError('Bundle digest mismatch')
 return {'pass':True,'files':len(manifest)}
