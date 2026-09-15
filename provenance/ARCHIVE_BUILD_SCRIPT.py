#!/usr/bin/env python3
"""Assemble two archival repositories from existing research bytes; no network."""
from __future__ import annotations
import csv, gzip, hashlib, io, json, re, shutil, zipfile
from pathlib import Path, PurePosixPath
from datetime import datetime, timezone

BASE=Path('/mnt/data'); WORK=BASE/'archive_work'; OUT=WORK/'repositories'
OUT.mkdir(exist_ok=True)
PROV={k:{} for k in ('ReCheck','RepairLens')}
COPIED=[]; OMITTED=[]
FONT={'.ttf','.otf','.ttc','.woff','.woff2','.pfb','.pfa','.afm'}
DIST=('.whl','.so','.dylib','.dll','.exe','.zst','.tar.gz','.tar.xz')
sha=lambda b:hashlib.sha256(b).hexdigest()

def safe_name(s):
    if '\\' in s or s.startswith('/') or any(x in ('..','') for x in s.rstrip('/').split('/')): raise ValueError(s)
    if any(':' in x for x in s.split('/')): raise ValueError(s)
    return s

def decoded(s):
    try: return s.encode('cp437').decode('utf-8')
    except (UnicodeEncodeError,UnicodeDecodeError): return s

def ignored(n):
    parts=PurePosixPath(n).parts
    return '__MACOSX' in parts or any(p.startswith('._') for p in parts) or PurePosixPath(n).name=='.DS_Store' or '__pycache__' in parts or n.endswith(('.pyc','.pyo'))

def forbidden(n):
    return PurePosixPath(n).suffix.lower() in FONT or n.lower().endswith(DIST)

def put(repo,dest,data,origin,kind='source_copy'):
    safe_name(dest)
    if forbidden(dest): raise ValueError(f'Excluded type: {dest}')
    if len(data)>48*1024*1024: raise ValueError(f'Individual file too large: {dest}')
    target=OUT/repo/dest
    digest=sha(data)
    if dest in PROV[repo]:
        if PROV[repo][dest]['sha256']!=digest: raise ValueError(f'Collision {repo}/{dest}')
        return
    target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
    PROV[repo][dest]={'path':dest,'bytes':len(data),'sha256':digest,'kind':kind,'source':origin}

def text(repo,dest,value): put(repo,dest,value.encode('utf-8'),'archive assembly, 2026-09-15','generated_document')
def js(repo,dest,value): text(repo,dest,json.dumps(value,ensure_ascii=False,indent=2)+'\n')

def unzip_to(repo,archive,dest,origin,strip=True,predicate=None):
    if isinstance(archive,Path): data=archive.read_bytes()
    else: data=archive
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        infos=[i for i in z.infolist() if not i.is_dir() and not ignored(i.filename)]
        names=[decoded(i.filename) for i in infos]
        roots=set(n.split('/')[0] for n in names)
        prefix=(next(iter(roots))+'/') if strip and len(roots)==1 and all('/' in n for n in names) else ''
        for i,n in zip(infos,names):
            safe_name(n)
            if (i.external_attr>>16)&0o170000 == 0o120000: raise ValueError('Symlink '+i.filename)
            rel=n.removeprefix(prefix)
            if forbidden(rel):
                OMITTED.append({'source':origin+'!'+i.filename,'reason':'dependency/font/binary distribution','sha256':sha(z.read(i)),'bytes':i.file_size});continue
            if predicate and not predicate(rel): continue
            put(repo,dest.rstrip('/')+'/'+rel,z.read(i),origin+'!'+i.filename,'archive_member_copy')

def phase_of(name):
    m=re.match(r'(?:Research_Handoff_)?(R\d+(?:NT1|TQ1|J1|C1|C|A|B)?)(?:_|\.)',name)
    if m:return m.group(1)
    if name.startswith('R7_'):return 'R7'
    raise ValueError(name)

shared={
 'ICASSP_Research_Package.zip':'initial_release',
 'Research_Audit_ZH.md':'initial_release',
 'Executed_Research_Results.md':'initial_release',
 'Delivery_Verification.json':'initial_release',
 'LLM_Pilot_Kit_v0.1.zip':'pilot',
 'LLM_Experiment_Runbook_ZH.md':'pilot',
 'LLM_Pilot_Audit_Package.zip':'pilot',
 'LLM_Pilot_Audit_ZH.md':'pilot',
 'LLM_Pilot_Verification.json':'pilot',
 '8a80ceb7-3588-4ffe-a4b2-4d6c9943b2d5.zip':'pilot',
}
feedback={
 '09af9535-f0df-4db5-a4a9-60a6b8f1b839.zip':'R1',
 '6ce67d0a-9d3f-4804-8453-06a57df12a50.zip':'R2',
 'a46910a7-8636-4bf3-a2c2-c5ccb28c8fe0.zip':'R3',
 'fae81259-daf9-403f-a3c6-767c311f50df.zip':'R4',
 '7bfb267f-104c-454b-a840-8f049baf3249.zip':'R5',
 'dc1eed59-6e1c-4ee7-ac48-6ea211b1bcdc.zip':'R6',
 '13081fe6-3570-4a9a-a0d3-abb338e58feb.zip':'R7C',
 '125a1ad6-6919-49c8-8c07-78e488a33edb.zip':'R7C1',
 '8583b54f-738b-4dff-af9b-1356f5fffb1e.zip':'R9',
 '5bd73050-e37d-4cb4-98ae-484d716fd2b8.zip':'R9J1',
 'e2fad0dc-b6e9-488a-b01e-a5816e5ae536.zip':'R9TQ1',
 'e9c3066b-474b-4d1c-b162-a0ca812a1c89.zip':'R9NT1',
 '反馈18_R10选择与写入范围诊断_满分_20260914.zip':'R10',
}
inv=json.loads((WORK/'source_inventory.json').read_text())
known={r['source'] for r in inv}
for p in (WORK/'historical_same_name_releases').glob('*'):
    rel=p.relative_to(BASE).as_posix()
    if rel not in known: inv.append({'source':rel,'bytes':p.stat().st_size,'sha256':sha(p.read_bytes())})
assert len(inv)==230, len(inv)
js_records=[]
for row in sorted(inv,key=lambda r:r['source']):
    src=row['source'];p=BASE/src;b=p.read_bytes();name=p.name
    if sha(b)!=row['sha256'] or len(b)!=row['bytes']:raise ValueError('Input changed '+src)
    destinations=[]
    if src.startswith('archive_work/historical_'):
        group=p.parent.name
        dest='history/same_name_releases/'+group+'/'+name
        put('ReCheck',dest,b,src); destinations.append('ReCheck/'+dest)
    elif name in shared:
        for repo in PROV:
            dest='shared_history/'+shared[name]+'/'+name
            put(repo,dest,b,src);destinations.append(repo+'/'+dest)
    elif name in feedback:
        ph=feedback[name];dest=f'feedback/{ph}/original_upload/{name}'
        put('ReCheck',dest,b,src);destinations.append('ReCheck/'+dest)
    elif name=='be0c8748-7cf7-4095-8e92-699f71d9a566.zip':
        destinations.append('ReCheck/feedback/R7_materials/filtered_reference/ (selected members; original hash retained)')
        OMITTED.append({'source':src,'bytes':len(b),'sha256':sha(b),'reason':'Original container embeds runtime/distribution binaries. Do not publish this ZIP; selected non-distribution members retained separately.'})
    elif name.startswith('01_ReCheck_'):
        dest='plans/'+name;put('ReCheck',dest,b,src);destinations.append('ReCheck/'+dest)
    elif name.startswith('02_RepairLens_'):
        dest='plans/'+name;put('RepairLens',dest,b,src);destinations.append('RepairLens/'+dest)
    elif name.startswith('RepairLens_'):
        dest='papers/controlled_draft/'+name;put('RepairLens',dest,b,src);destinations.append('RepairLens/'+dest)
    elif name=='Repair_Readiness_Recomputed_Results.csv':
        dest='reviews/pilot_readiness/'+name;put('RepairLens',dest,b,src);destinations.append('RepairLens/'+dest)
    elif name.startswith('ReCheck_'):
        if name.endswith('.csv'): dest='reviews/pilot/'+name
        else:
            tag='R11' if '_R11' in name else ('R8' if '_R8' in name else 'initial')
            dest=f'papers/{tag}/'+name
        put('ReCheck',dest,b,src);destinations.append('ReCheck/'+dest)
    else:
        ph=phase_of(name)
        category='archives' if name.endswith('.zip') else ('tables' if name.endswith('.csv') else 'documents')
        dest=f'stages/{ph}/{category}/{name}'
        put('ReCheck',dest,b,src);destinations.append('ReCheck/'+dest)
    js_records.append({**row,'destinations':destinations,'status':'selected_members_only' if name.startswith('be0c8748') else 'original_bytes_preserved'})

# Readable original shared engine keeps all original relative dependencies intact.
for repo in PROV:
    unzip_to(repo,BASE/'ICASSP_Research_Package.zip','shared_history/initial_release/engine_snapshot','ICASSP_Research_Package.zip')
    unzip_to(repo,BASE/'LLM_Pilot_Kit_v0.1.zip','shared_history/pilot/engine_snapshot','LLM_Pilot_Kit_v0.1.zip')
    text(repo,'shared_history/README.md','''# 共享早期原始发布 / shared provenance

这里保留两条研究线当时共同发布的原包，不能把另一个项目的结果计入本项目。
`initial_release/engine_snapshot` 是原初始工程的逐字节展开，保留原来的目录依赖；
`pilot/engine_snapshot` 是共享端点预实验运行器。初始 README 和执行指令是历史快照，
不构成现在重新花费模型额度的授权。项目专属材料请从仓库根 README 和索引进入。
''')

# Extract all handoff source trees so code can be browsed without unzipping.
for p in sorted(BASE.glob('Research_Handoff_*.zip')):
    ph=phase_of(p.name)
    unzip_to('ReCheck',p,f'experiments/{ph}',p.name)
unzip_to('ReCheck',WORK/'historical_R7C_turn23/Research_Handoff_R7C.zip','experiments/R7C_original_14_case','archive_work/historical_R7C_turn23/Research_Handoff_R7C.zip')
for name,tag in [('R7A_Source_Study.zip','R7A'),('R7B_Native_Audit_Package.zip','R7B'),('R8_Research_Update.zip','R8'),('R11_Evidence_Synthesis.zip','R11')]:
    unzip_to('ReCheck',BASE/name,f'analysis/{tag}',name)
unzip_to('ReCheck',BASE/'R7_Materials_Request.zip','experiments/R7_materials_collector','R7_Materials_Request.zip')
for name,repo,dest in [
 ('ReCheck_LaTeX.zip','ReCheck','papers/initial/latex'),
 ('ReCheck_Diagnostic_Revision_R8_LaTeX.zip','ReCheck','papers/R8/latex'),
 ('ReCheck_Evidence_Synthesis_R11_LaTeX.zip','ReCheck','papers/R11/latex'),
 ('RepairLens_LaTeX.zip','RepairLens','papers/controlled_draft/latex')]:
    unzip_to(repo,BASE/name,dest,name)

# Submitted explanatory files are readable; raw original ZIPs remain byte-for-byte.
for name,ph in feedback.items():
    unzip_to('ReCheck',BASE/name,f'feedback/{ph}/submitted_notes',name,
             predicate=lambda n:not n.lower().endswith('.zip'))
# Pilot was jointly delivered. Preserve whole original in shared_history and select project runs.
pilot_name='8a80ceb7-3588-4ffe-a4b2-4d6c9943b2d5.zip'
for repo in PROV:
    unzip_to(repo,BASE/pilot_name,'shared_history/pilot/submitted_notes',pilot_name,
             predicate=lambda n:not n.lower().endswith('.zip'))
with zipfile.ZipFile(BASE/pilot_name) as z:
    for n in z.namelist():
        if ignored(n) or not n.lower().endswith('.zip'):continue
        if 'repair_readiness' in n: repo='RepairLens';tag='pilot_readiness'
        elif '/recheck_' in n: repo='ReCheck';tag='pilot'
        elif 'smoke_' in n:
            for rr in PROV:put(rr,'shared_history/pilot/'+PurePosixPath(n).name,z.read(n),pilot_name+'!'+n,'archive_member_copy')
            continue
        else: raise ValueError('Unknown pilot child '+n)
        put(repo,f'feedback/{tag}/original_run.zip',z.read(n),pilot_name+'!'+n,'archive_member_copy')
        unzip_to(repo,z.read(n),f'feedback/{tag}/raw',pilot_name+'!'+n)

# Latest live cohorts have directly browsable raw request/response/data trees.
for name,ph in feedback.items():
    if ph not in {'R7C1','R9NT1','R10'}:continue
    with zipfile.ZipFile(BASE/name) as z:
        inner=[n for n in z.namelist() if n.lower().endswith('.zip') and not ignored(n)]
        if len(inner)!=1:raise ValueError((name,inner))
        unzip_to('ReCheck',z.read(inner[0]),f'feedback/{ph}/raw',name+'!'+inner[0])

# R7 public dependencies: retain provenance/download metadata/source; omit runtime distributions.
material='be0c8748-7cf7-4095-8e92-699f71d9a566.zip'
def filtered_material(b,origin,dest):
    with zipfile.ZipFile(io.BytesIO(b)) as z:
        fs=[i for i in z.infolist() if not i.is_dir() and not ignored(i.filename)]
        for i in fs:
            name=decoded(i.filename);safe_name(name);data=z.read(i)
            if forbidden(name):
                OMITTED.append({'source':origin+'!'+i.filename,'bytes':len(data),'sha256':sha(data),'reason':'Reproducible public dependency distribution, not research evidence'});continue
            if name.lower().endswith('.zip'):
                filtered_material(data,origin+'!'+i.filename,dest+'/'+name[:-4]);continue
            put('ReCheck',dest+'/'+name,data,origin+'!'+i.filename,'selected_dependency_provenance')
filtered_material((BASE/material).read_bytes(),material,'feedback/R7_materials/filtered_reference')
js('ReCheck','feedback/R7_materials/OMITTED_DISTRIBUTIONS.json',OMITTED)
text('ReCheck','feedback/R7_materials/README.md','''# R7依赖材料：公开归档边界

原始 135,008,166 字节 ZIP 未放入此仓库，因为它包含完整 Python 运行时和依赖分发。
不是丢弃研究失败或原始模型数据：该批只是供研究端离线安装的公开材料。
保留收集器、下载记录、版本、校验和、报告及上游源码；原完整 ZIP 的摘要和所有
排除分发的名称/长度/摘要见 OMITTED_DISTRIBUTIONS.json。运行时、wheel、源码分发
和字体不随本仓库重发。原文件在会话中保持不变。

filtered_reference 是明确标记的选择性展开，不是完整原包；其中原 BUNDLE_MANIFEST
列出的是原包内容，不能拿它把已排除的安装文件误判为研究数据缺失。
''')

# Only genuine RepairLens-related later helpers; no ReCheck live results repurposed.
for phase in ('R2','R3','R4'):
    src='Research_Handoff_'+phase+'.zip'
    with zipfile.ZipFile(BASE/src) as z:
        chosen=[]
        for n in z.namelist():
            tail=n.split('/',1)[-1]
            if any(w in tail.lower() for w in ('repair_guard','repair_cost','pilot/readiness.py')):
                if not n.endswith('/'):
                    put('RepairLens',f'analysis/cost_diagnostics/{phase}/'+tail,z.read(n),src+'!'+n,'project_specific_excerpt');chosen.append(tail)
        # License applies to the original helper snapshot.
        for n in z.namelist():
            if n.endswith('/LICENSE'):
                put('RepairLens',f'analysis/cost_diagnostics/{phase}/LICENSE',z.read(n),src+'!'+n,'archive_member_copy');break
        js('RepairLens',f'analysis/cost_diagnostics/{phase}/EXCERPT_SCOPE.json',{'source_archive':src,'source_sha256':sha((BASE/src).read_bytes()),'selected_files':chosen,'scope':'RepairLens cost/guard diagnostics only; not a new main-scheduler experiment; excerpt may require imports from original handoff.'})

# Provenance, duplicate snapshots, and helper tests.
for repo in PROV:
    put(repo,'tools/verify_archive.py',(WORK/'tooling/verify_archive.py').read_bytes(),'new archive verification utility','archive_tool')
    put(repo,'tests/test_verify_archive.py',(WORK/'tooling/tests/test_verify_archive.py').read_bytes(),'new archive verification tests','archive_tool')
    put(repo,'provenance/verification_tests_initial_red.log',(WORK/'verify_red.log').read_bytes(),'archive verifier development','verification_log')
    put(repo,'provenance/verification_tests_green.log',(WORK/'verify_green.log').read_bytes(),'archive verifier development','verification_log')
    relevant=[{**r,'destinations':[d for d in r['destinations'] if d.startswith(repo+'/')]} for r in js_records if any(d.startswith(repo+'/') for d in r['destinations'])]
    js(repo,'provenance/SOURCE_ARTIFACTS.json',relevant)
    text(repo,'.gitignore','''# New local by-products only. Original archived evidence is retained.\n.git/\n.venv/\nvenv/\n__pycache__/\n*.pyc\n.DS_Store\n.env\n.env.*\n!.env.example\n''')
    text(repo,'NOTICE.md','''# Archive and licensing notice

This collection preserves research materials prepared during this conversation.
It is not a new experiment, publication, peer review, or claim of successful GitHub upload.
Original licenses and notices inside source snapshots are retained. This wrapper does
not relicense third-party software, model responses, datasets, or generated paper text.
No font files or installation distributions are included. Existing PDF font embedding
is part of the PDF document, not a redistribution of standalone font files.

Historical documents may contain preliminary or corrected interpretations. Read their
subsequent audit and correction files together; do not silently overwrite history.
No original author names, experimental claims, or paper text were rewritten for this archive.
The repository owner and eventual human authors must review publication rights and claims.
''')
    js(repo,'PUBLISH_STATUS.json',{'target_repository':'zyh-0905/'+repo,'visibility_observed':'public',
        'local_archive_prepared':True,'remote_push_completed':False,'remote_commits_created':0,
        'github_write_attempt_http_status':403,'github_message':'Resource not accessible by integration',
        'authenticated_login_observed':'Sorasky681','target_owner':'zyh-0905',
        'push_permission_observed':False,'note':'This describes this archival turn only. Update after a separately verified successful upload.'})

# Indices generated from exact destinations, not file-name guesses.
for repo in PROV:
    rows=['# 原始研究材料索引','',
          '本索引按本次实际读取、复制的文件生成。源 ZIP 保留原字节；展开副本保留成员字节。',
          '同一数据在反馈、审核包、离线证据中重复出现并不增加样本数。',
          '', '| 原文件 | 归档位置 | 字节 | SHA-256 |','|---|---|---:|---|']
    for r in sorted(json_records if False else js_records,key=lambda x:x['source']):
        ds=[d[len(repo)+1:] for d in r['destinations'] if d.startswith(repo+'/')]
        if ds:
            links='<br>'.join(f'`{x}`' for x in ds)
            rows.append(f"| `{r['source']}` | {links} | {r['bytes']} | `{r['sha256']}` |")
    text(repo,'ARCHIVE_INDEX_ZH.md','\n'.join(rows)+'\n')

# Global mapping used for completeness validation outside the two repositories.
(WORK/'source_routing.json').write_text(json.dumps(js_records,ensure_ascii=False,indent=2))
(WORK/'provenance_work.json').write_text(json.dumps(PROV,ensure_ascii=False,indent=2))
print(json.dumps({r:{'files_so_far':len(p),'bytes_so_far':sum(v['bytes'] for v in p.values())} for r,p in PROV.items()},indent=2))
