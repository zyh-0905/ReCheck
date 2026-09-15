from pathlib import Path, PurePosixPath
from zipfile import ZipFile
from io import BytesIO
import hashlib,json,re,gzip,collections
ROOT=Path('/mnt/data')
WORK=ROOT/'archive_work'
FONT={'.ttf','.otf','.ttc','.woff','.woff2','.eot','.pfb','.pfa','.dfont','.afm','.tfm'}
DIST={'.whl','.dylib','.so','.dll','.exe','.zst'}
# These patterns detect candidate credentials, not all confidential data.
PAT={
 'api_token':re.compile(rb'\bsk-(?:proj-|svcacct-)?[A-Za-z0-9_-]{20,}'),
 'github_token':re.compile(rb'\b(?:gh[pousr]_[A-Za-z0-9]{25,}|github_pat_[A-Za-z0-9_]{40,})'),
 'aws_id':re.compile(rb'\b(?:AKIA|ASIA)[A-Z0-9]{16}\b'),
 'private_key':re.compile(rb'-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----'),
 'bearer_literal':re.compile(rb'(?i)[\"\']authorization[\"\']\s*:\s*[\"\'](?:bearer|basic)\s+([A-Za-z0-9_+/=.-]{15,})'),
 'key_literal':re.compile(rb'(?i)[\"\'](?:api_key|apiKey|access_token|client_secret)[\"\']\s*:\s*[\"\']([A-Za-z0-9_+/=.-]{15,})[\"\']'),
}
TEXT={'.json','.jsonl','.md','.txt','.csv','.py','.tex','.bib','.log','.toml','.yaml','.yml','.sh','.ps1','.xml','.html','.raw','.cfg','.ini','.rst','.sty','.sha256'}
seen=set(); entries=[]; findings=[]; rejected=[]; scanbytes=0

def sha(b): return hashlib.sha256(b).hexdigest()
def bad_path(n):
 p=PurePosixPath(n.replace('\\','/'))
 return p.is_absolute() or '..' in p.parts or bool(re.match(r'^[A-Za-z]:',n))
def visit(b,loc,depth=0):
 global scanbytes
 h=sha(b)
 if h in seen: return
 seen.add(h)
 name=loc.rsplit('!',1)[-1]; ext=Path(name).suffix.lower()
 if ext in FONT:
  rejected.append({'path':loc,'sha256':h,'reason':'font_file'}); return
 if ext in DIST or name.endswith(('.tar.gz','.tar.xz','.tar.zst')):
  rejected.append({'path':loc,'sha256':h,'reason':'third_party_runtime_distribution'});return
 if ext=='.zip':
  if depth>10: raise ValueError('excessive nesting '+loc)
  with ZipFile(BytesIO(b)) as z:
   seen_names=set()
   for i in z.infolist():
    if i.is_dir():continue
    if i.filename in seen_names: raise ValueError('duplicate archive path '+loc+'!'+i.filename)
    seen_names.add(i.filename)
    if bad_path(i.filename): raise ValueError('unsafe archive path '+loc+'!'+i.filename)
    if (i.external_attr>>16)&0o170000 == 0o120000: raise ValueError('archive symlink '+loc+'!'+i.filename)
    if i.file_size>300_000_000:raise ValueError('oversized member '+loc+'!'+i.filename)
    d=z.read(i)
    entries.append({'container':loc,'member':i.filename,'bytes':len(d),'sha256':sha(d)})
    if '__MACOSX' in PurePosixPath(i.filename).parts or Path(i.filename).name.startswith('._') or Path(i.filename).name=='.DS_Store':continue
    visit(d,loc+'!'+i.filename,depth+1)
 elif ext=='.gz':
  with gzip.GzipFile(fileobj=BytesIO(b)) as f:
   d=f.read(350_000_001)
   if len(d)>350_000_000:raise ValueError('gzip oversized '+loc)
  visit(d,loc[:-3],depth+1)
 elif ext in TEXT or Path(name).name in {'LICENSE','NOTICE','Dockerfile','Makefile'}:
  scanbytes+=len(b)
  for key,rg in PAT.items():
   for m in rg.finditer(b):
    frag=m.group(1) if m.lastindex else m.group(0)
    context=b[max(0,m.start()-55):min(len(b),m.end()+50)].decode('utf-8','replace')
    context=context.replace(frag.decode('utf-8','replace'),'<CREDENTIAL_CANDIDATE>')
    findings.append({'path':loc,'kind':key,'candidate_sha256':sha(frag),'length':len(frag),'context_redacted':context})

sources=list(ROOT.glob('*'))
sources=[p for p in sources if p.is_file()]
sources+=list((ROOT/'research_plans').glob('*.md'))
sources+=list((ROOT/'research_convergence').glob('*.md'))
sources+=list((WORK/'historical_R7C_turn23').glob('*'))
source_rows=[]
for p in sources:
 d=p.read_bytes();source_rows.append({'source':str(p.relative_to(ROOT)),'bytes':len(d),'sha256':sha(d)})
 visit(d,str(p.relative_to(ROOT)))
WORK.mkdir(exist_ok=True)
(WORK/'source_inventory.json').write_text(json.dumps(source_rows,ensure_ascii=False,indent=2))
(WORK/'archive_entries.json').write_text(json.dumps(entries,ensure_ascii=False,indent=2))
(WORK/'credential_candidates.json').write_text(json.dumps(findings,ensure_ascii=False,indent=2))
(WORK/'excluded_distributions.json').write_text(json.dumps(rejected,ensure_ascii=False,indent=2))
print(json.dumps({'top_sources':len(source_rows),'unique_blobs_examined':len(seen),'archive_members':len(entries),'text_bytes_scanned':scanbytes,'candidate_matches':len(findings),'excluded_distributions_or_fonts':len(rejected)},indent=2))
print('candidate categories',dict(collections.Counter(x['kind'] for x in findings)))
print('excluded categories',dict(collections.Counter(x['reason'] for x in rejected)))
