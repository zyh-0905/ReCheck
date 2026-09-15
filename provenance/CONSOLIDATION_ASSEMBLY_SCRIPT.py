from pathlib import Path, PurePosixPath
from zipfile import ZipFile
import hashlib,json,shutil,io,re,stat
BASE=Path('/mnt/data'); ROOT=BASE/'recheck_consolidation_work/ReCheck'
H=lambda b:hashlib.sha256(b).hexdigest()
old_manifest=json.loads((ROOT/'ARCHIVE_MANIFEST.json').read_text())
old_sources=json.loads((ROOT/'provenance/SOURCE_ARTIFACTS.json').read_text())
meta={e['path']:dict(e) for e in old_manifest['files']}
meta['ARCHIVE_MANIFEST.json']={'path':'ARCHIVE_MANIFEST.json','bytes':(ROOT/'ARCHIVE_MANIFEST.json').stat().st_size,'sha256':H((ROOT/'ARCHIVE_MANIFEST.json').read_bytes()),'kind':'legacy_manifest','source':'earlier repository archive R1-R11'}
new_sources=[]; movements=[]
nav=['README.md','CONTENTS_ZH.md','ARCHIVE_INDEX_ZH.md','RESEARCH_TIMELINE_ZH.md','PUBLISH_STATUS.json','ARCHIVE_MANIFEST.json']
for n in nav:
 p=ROOT/n; dest=ROOT/'history/archive_through_R11'/n;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,dest)
 meta[dest.relative_to(ROOT).as_posix()]={**meta[n],'path':dest.relative_to(ROOT).as_posix()}
 movements.append({'old_path':n,'preserved_at':dest.relative_to(ROOT).as_posix(),'sha256':H(p.read_bytes())})

def write_exact(data,dest,source,kind='source_copy'):
 p=ROOT/dest;p.parent.mkdir(parents=True,exist_ok=True)
 if p.exists() and p.read_bytes()!=data: raise RuntimeError('Collision: '+dest)
 p.write_bytes(data)
 meta[dest]={'path':dest,'bytes':len(data),'sha256':H(data),'kind':kind,'source':source}
 return dest

def copy_source(p,dest,stage):
 b=p.read_bytes();write_exact(b,dest,p.name,'original_attachment')
 new_sources.append({'source':p.name,'bytes':len(b),'sha256':H(b),'destinations':['ReCheck/'+dest],'status':'original_bytes_preserved','research_stage':stage})

for p in sorted(BASE.iterdir()):
 if not p.is_file():continue
 m=re.match(r'^R(12|13|14|15)_',p.name)
 if not m:continue
 stage='R'+m.group(1)
 category='archives' if p.suffix=='.zip' else 'verification' if p.suffix=='.json' else 'results' if p.suffix in {'.csv','.svg'} else 'handoff' if any(x in p.name for x in ('Prompt','Runbook')) else 'reports'
 copy_source(p,f'stages/{stage}/{category}/{p.name}',stage)
for n,cat in [('ReCheck_ICASSP_Research_Draft_R16.pdf','papers/R16'),('ReCheck_ICASSP_LaTeX_R16.zip','papers/R16'),('ReCheck_R16_Completion_Report_ZH.md','stages/R16/reports'),('ReCheck_R16_Verification.json','stages/R16/verification'),('ReCheck_R16_Research_and_Evidence.zip','stages/R16/archives')]:
 copy_source(BASE/n,f'{cat}/{n}','R16')
for n,stage in [('反馈19_R12公开评测器离线核查_无需运行_20260915.zip','R12_receipt19'),('反馈20_R14公开数据下载_完成_20260915.zip','R14_download20')]:
 copy_source(BASE/n,f'feedback/{stage}/original_upload/{n}',stage)

FONT={'.ttf','.otf','.ttc','.woff','.woff2','.pfb','.pfa','.afm','.eot','.fon'}
def extract_zip(p,dest,strip_root=False,decode_names=False):
 with ZipFile(p) as z:
  names=[i.filename for i in z.infolist() if not i.is_dir() and not i.filename.startswith('__MACOSX/')]
  prefix=(PurePosixPath(names[0]).parts[0]+'/') if strip_root else ''
  for i in z.infolist():
   if i.is_dir() or i.filename.startswith('__MACOSX/') or PurePosixPath(i.filename).name.startswith('._'):continue
   name=i.filename
   if decode_names:
    try:name=name.encode('cp437').decode('utf8')
    except (UnicodeError,ValueError):pass
   if strip_root:
    name=name.split('/',1)[1]
   rel=PurePosixPath(name)
   if rel.is_absolute() or '..' in rel.parts or '\\' in name or stat.S_ISLNK(i.external_attr>>16):raise RuntimeError('Unsafe '+name)
   if rel.suffix.lower() in FONT:raise RuntimeError('Font '+name)
   if '.git' in rel.parts:raise RuntimeError('Git metadata '+name)
   write_exact(z.read(i),str(PurePosixPath(dest)/rel),f'{Path(p).name}!{i.filename}','expanded_source_member')

for n,d in [('R12_Public_Evaluator_Audit.zip','analysis/R12'),('R13_Temporal_Scope_Audit.zip','analysis/R13'),('R14_Public_Corpus_Analysis.zip','analysis/R14'),('R15_Public_Effect_Audit.zip','analysis/R15')]:extract_zip(BASE/n,d,strip_root=True)
extract_zip(BASE/'ReCheck_R16_Research_and_Evidence.zip','analysis/R16')
extract_zip(BASE/'ReCheck_ICASSP_LaTeX_R16.zip','papers/R16/latex')
extract_zip(BASE/'R14_Public_Data_Download_Kit.zip','data/collection/R14',strip_root=True)
extract_zip(BASE/'反馈19_R12公开评测器离线核查_无需运行_20260915.zip','feedback/R12_receipt19/readable',True,True)
extract_zip(BASE/'反馈20_R14公开数据下载_完成_20260915.zip','feedback/R14_download20/readable',True,True)
# Preserve each public JSON as an ordinary, individually browsable file.
public=ROOT/'analysis/R14/inputs/R14_public_data_original.zip'
assert H(public.read_bytes())=='22eae5e31183ca4e109bd13ed5f6b79f082a6e81511f1ae0dfd38f83499a6dd6'
extract_zip(public,'data/public/SAP_agent-quality-inspect/593e686f4d0c2e9fcae5ae664c16a7687907cf97')
# Byte checks only, not re-execution of any scientific results.
for n in ['R12_Public_Evaluator_Audit.zip','R13_Temporal_Scope_Audit.zip','R14_Public_Corpus_Analysis.zip','R15_Public_Effect_Audit.zip']:
 assert (ROOT/'analysis/R16/evidence_archives'/n).read_bytes()==(BASE/n).read_bytes()
assert (ROOT/'analysis/R16/paper/main.pdf').read_bytes()==(BASE/'ReCheck_ICASSP_Research_Draft_R16.pdf').read_bytes()
(ROOT/'provenance/ADDED_SOURCE_ARTIFACTS_R12_R16.json').write_text(json.dumps(new_sources,ensure_ascii=False,indent=2)+'\n')
(ROOT/'provenance/LEGACY_NAVIGATION_PRESERVATION.json').write_text(json.dumps(movements,ensure_ascii=False,indent=2)+'\n')
(ROOT/'provenance/SOURCE_ARTIFACTS_ALL.json').write_text(json.dumps(old_sources+new_sources,ensure_ascii=False,indent=2)+'\n')
(BASE/'recheck_consolidation_work/assembly_state.json').write_text(json.dumps({'meta':meta,'new_sources':new_sources,'movements':movements},ensure_ascii=False))
print(json.dumps({'old_artifact_records':len(old_sources),'added_artifact_records':len(new_sources),'files_so_far':sum(p.is_file() for p in ROOT.rglob('*')),'bytes_so_far':sum(p.stat().st_size for p in ROOT.rglob('*') if p.is_file())},ensure_ascii=False))
