"""Immutable local data, narrowly allowlisted archives, offline-only execution."""
from pathlib import Path,PurePosixPath
from contextlib import contextmanager
import os,json,hashlib,socket,zipfile,stat,datetime,re
from .data import canonical,digest

def sha(b):return hashlib.sha256(b).hexdigest()
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def write_once(p,o):
    p=Path(p);b=canonical(o)+b'\n';p.parent.mkdir(parents=True,exist_ok=True)
    if p.exists():
        if p.read_bytes()!=b:raise ValueError('immutable output differs: '+str(p))
        return
    with p.open('xb') as f:f.write(b)
def replace_local(p,o):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);t=p.with_name(p.name+'.tmp')
    t.write_bytes(canonical(o)+b'\n');os.replace(t,p)
def safe_path(name):
    pp=PurePosixPath(name)
    return bool(name) and not pp.is_absolute() and '..' not in pp.parts and '\\' not in name and ':' not in name

def source_files(root):
    root=Path(root);files=[]
    for f in root.rglob('*'):
        rel=f.relative_to(root)
        if any(x in {'.git','.venv','__pycache__','runs','uploads','verification'} for x in rel.parts):continue
        if f.is_symlink():raise ValueError('source symlink')
        if not f.is_file() or f.name=='SOURCE_MANIFEST.json':continue
        if f.suffix in ('.py','.json','.md','.txt','.tex','.csv') or f.name in ('LICENSE','.gitignore'):files.append(f)
    return sorted(files)
def make_manifest(root):
    root=Path(root);m={'algorithm':'sha256','files':{f.relative_to(root).as_posix():sha(f.read_bytes()) for f in source_files(root)}}
    replace_local(root/'SOURCE_MANIFEST.json',m);return m

def verify_source(root):
    root=Path(root)
    try:
        m=read(root/'SOURCE_MANIFEST.json');actual={f.relative_to(root).as_posix():sha(f.read_bytes()) for f in source_files(root)}
        if any(not safe_path(k) for k in m['files']):raise ValueError('unsafe source manifest')
        issues=['missing or changed '+k for k,v in m['files'].items() if actual.get(k)!=v]
        issues+=['unregistered '+k for k in actual if k not in m['files']]
        return {'pass':not issues,'issues':issues,'files':len(m['files']),'manifest_sha256':sha((root/'SOURCE_MANIFEST.json').read_bytes())}
    except (OSError,ValueError,KeyError) as e:return {'pass':False,'issues':[str(e)]}

@contextmanager
def no_network():
    orig=(socket.socket,socket.create_connection,socket.getaddrinfo)
    def denied(*a,**k):raise RuntimeError('R6_OFFLINE_ONLY: network prohibited')
    socket.socket=denied;socket.create_connection=denied;socket.getaddrinfo=denied
    try:yield
    finally:socket.socket,socket.create_connection,socket.getaddrinfo=orig
@contextmanager
def lock(folder):
    p=Path(folder)/'.write.lock';p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('x',encoding='utf-8') as f:json.dump({'pid':os.getpid(),'at':now()},f)
    try:yield
    finally:p.unlink(missing_ok=True)

def bundle(root,out):
    root=Path(root);out=Path(out)
    if out.exists():raise FileExistsError('refuse to overwrite export')
    registered=read(root/'SOURCE_MANIFEST.json')['files'];items={}
    for name in list(registered)+['SOURCE_MANIFEST.json']:
        if not safe_path(name):raise ValueError('unsafe source')
        f=root/name
        if f.is_symlink():raise ValueError('symlink')
        if f.is_file():items['kit_source/'+name]=f.read_bytes()
    run=root/'runs/R6_offline'
    fixed={'manifest.json','status.json','execution_summary.json','compilation.json','design_metadata.json','private/cases.json','private/split_ids.json','audit/report.json','audit/per_task.csv','audit/summary.csv','audit/paired.csv','audit/cost_frontier.csv','audit/calibration_costs.csv','audit/reference_validation.json'}
    if run.exists():
        for f in run.rglob('*'):
            if f.is_symlink():raise ValueError('symlink in evidence')
            if not f.is_file():continue
            name=f.relative_to(run).as_posix()
            allowed=name in fixed or re.fullmatch(r'(calibration/panel_\d{3}_(single|full|random|occupancy|decision)|models/panel_\d{3}_[a-z0-9_]+|trajectories/\d{3}_(single|shared)_[a-z0-9_]+)\.json',name)
            if name.startswith('code_snapshot/'):
                allowed=name[14:] in registered or name=='code_snapshot/SOURCE_MANIFEST.json'
            if allowed:items['run/'+name]=f.read_bytes()
    secrets=re.compile(rb'(sk-[A-Za-z0-9_-]{20,}|Bearer[ ]+[A-Za-z0-9._-]{20,}|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----)')
    if any(secrets.search(x) for x in items.values()):raise ValueError('BLOCKED_SENSITIVE_CONTENT')
    meta={'task':'R6_SELECTIVE_CALIBRATION_01','new_llm_api_calls':0,'files':{k:{'sha256':sha(v),'bytes':len(v)} for k,v in items.items()}}
    out.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(out,'x',zipfile.ZIP_DEFLATED) as z:
        for k,v in items.items():z.writestr(k,v)
        z.writestr('BUNDLE_MANIFEST.json',canonical(meta)+b'\n')
    return verify_bundle(out)
def verify_bundle(path):
    with zipfile.ZipFile(path) as z:
        inf=z.infolist();names=[i.filename for i in inf]
        if len(inf)>40000 or len(set(names))!=len(names) or sum(i.file_size for i in inf)>256*1024**2:raise ValueError('unsafe archive size/duplicates')
        if any(not safe_path(i.filename) or stat.S_ISLNK(i.external_attr>>16) or i.flag_bits&1 for i in inf):raise ValueError('unsafe archive entry')
        m=json.loads(z.read('BUNDLE_MANIFEST.json'));issues=[]
        if set(names)!=set(m['files'])|{'BUNDLE_MANIFEST.json'}:issues.append('archive index mismatch')
        for k,v in m['files'].items():
            if k not in names:issues.append('missing '+k);continue
            b=z.read(k)
            if len(b)!=v['bytes'] or sha(b)!=v['sha256']:issues.append('hash mismatch '+k)
        return {'pass':not issues,'entries':len(m['files']),'issues':issues}
