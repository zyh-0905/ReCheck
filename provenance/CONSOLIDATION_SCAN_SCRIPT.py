from pathlib import Path,PurePosixPath
from zipfile import ZipFile
import io,hashlib,re,json,stat,collections
ROOT=Path('/mnt/data/recheck_consolidation_work/ReCheck');OUT=ROOT.parent
seen=set(); entries=0; text_bytes=0; containers=0; flags=[]; forbidden=[]
FONT={'.ttf','.otf','.ttc','.woff','.woff2','.pfb','.pfa','.afm','.eot','.dfont','.tfm','.fon'}
PAT={
'api_token':re.compile(rb'\bsk-(?:proj-|svcacct-)?[A-Za-z0-9_-]{20,}'),
'github_token':re.compile(rb'\b(?:gh[pousr]_[A-Za-z0-9]{25,}|github_pat_[A-Za-z0-9_]{40,})'),
'aws_id':re.compile(rb'\b(?:AKIA|ASIA)[A-Z0-9]{16}\b'),
'private_key':re.compile(rb'-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----'),
'bearer_literal':re.compile(rb'(?i)["\']authorization["\']\s*:\s*["\'](?:bearer|basic)\s+([A-Za-z0-9_+/=.-]{15,})'),
'key_literal':re.compile(rb'(?i)["\'](?:api_key|apiKey|access_token|client_secret)["\']\s*:\s*["\']([A-Za-z0-9_+/=.-]{15,})["\']'),
}
TEXT={'.json','.jsonl','.md','.txt','.csv','.py','.tex','.bib','.log','.toml','.yaml','.yml','.sh','.ps1','.xml','.html','.raw','.cfg','.ini','.rst','.sty','.sha256'}

def visit(b,path,depth=0):
 global entries,text_bytes,containers
 n=path.split('!')[-1];p=PurePosixPath(n);ext=p.suffix.lower()
 if ext in FONT or p.name in {'.env','id_rsa','id_ed25519'}:
  forbidden.append({'path':path,'kind':'font_or_credential_file'});return
 digest=hashlib.sha256(b).hexdigest()
 if digest in seen:return
 seen.add(digest)
 if ext=='.zip':
  containers+=1
  if depth>12:raise ValueError('zip nesting')
  with ZipFile(io.BytesIO(b)) as z:
   members=set()
   for i in z.infolist():
    if i.is_dir():continue
    entries+=1
    rel=PurePosixPath(i.filename.replace('\\','/'))
    if rel.is_absolute() or '..' in rel.parts or stat.S_ISLNK(i.external_attr>>16) or i.filename in members:
     raise ValueError('Unsafe ZIP entry '+path+'!'+i.filename)
    members.add(i.filename)
    if i.file_size>300_000_000:raise ValueError('Oversize inner entry')
    if '__MACOSX' in rel.parts or rel.name.startswith('._') or rel.name=='.DS_Store':continue
    visit(z.read(i),path+'!'+i.filename,depth+1)
 elif ext in TEXT or p.name in {'LICENSE','NOTICE','Makefile'}:
  text_bytes+=len(b)
  lower=b.lower()
  for k,pattern in PAT.items():
   markers={'api_token':(b'sk-',),'github_token':(b'ghp_',b'gho_',b'ghu_',b'ghs_',b'ghr_',b'github_pat_'),'aws_id':(b'AKIA',b'ASIA'),'private_key':(b'PRIVATE KEY',),'bearer_literal':(b'authorization',),'key_literal':(b'api_key',b'apikey',b'access_token',b'client_secret')}[k]
   hay=lower if k in {'bearer_literal','key_literal'} else b
   if not any(v in hay for v in markers):continue
   for m in pattern.finditer(b):
    val=m.group(1) if m.lastindex else m.group(0)
    context=b[max(0,m.start()-70):min(len(b),m.end()+80)].decode('utf8','replace').replace(val.decode('utf8','replace'),'<REDACTED_CANDIDATE>')
    flags.append({'path':path,'kind':k,'candidate_sha256':hashlib.sha256(val).hexdigest(),'length':len(val),'context_redacted':context})

count=0
for p in sorted(ROOT.rglob('*')):
 if not p.is_file() or any(x in p.parts for x in ('.git','__pycache__')):continue
 if p.is_symlink():raise ValueError('File symlink')
 count+=1;visit(p.read_bytes(),p.relative_to(ROOT).as_posix())
report={'files_scanned':count,'unique_contents_scanned':len(seen),'zip_containers_scanned':containers,
'zip_members_inspected':entries,'text_bytes_scanned':text_bytes,'forbidden_files':forbidden,
'credential_candidates':flags,'scope':'Pattern-based candidate scan, not comprehensive privacy or IP certification.'}
(OUT/'current_scan.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k not in {'credential_candidates'}},ensure_ascii=False,indent=2))
print('CANDIDATES',len(flags))
for flag in flags:print(json.dumps(flag,ensure_ascii=False))
