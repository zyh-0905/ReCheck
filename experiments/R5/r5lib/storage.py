"""Source-locked, append-only local study artifacts. No credentials or network client."""
from pathlib import Path,PurePosixPath
from contextlib import contextmanager
import json,hashlib,os,socket,zipfile,stat,datetime,re

def canonical(o):
    return json.dumps(o,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode('utf-8')
def digest(o):return hashlib.sha256(canonical(o)).hexdigest()
def sha(b):return hashlib.sha256(b).hexdigest()
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def write_once(p,o):
    p=Path(p);b=canonical(o)+b'\n';p.parent.mkdir(parents=True,exist_ok=True)
    if p.exists():
        if p.read_bytes()!=b:raise ValueError(f'immutable output differs: {p.name}')
        return
    with p.open('xb') as f:f.write(b)
def replace_local(p,o):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
    t=p.with_name(p.name+'.tmp')
    with t.open('wb') as f:f.write(canonical(o)+b'\n')
    os.replace(t,p)
def source_files(root):
    root=Path(root);out=[]
    for f in root.rglob('*'):
        if not f.is_file():continue
        rel=f.relative_to(root)
        if any(x in {'.git','.venv','__pycache__','runs','uploads','verification'} for x in rel.parts):continue
        if rel.as_posix()=='SOURCE_MANIFEST.json':continue
        if f.is_symlink():raise ValueError('source symlink')
        if f.suffix in ('.py','.json','.md','.txt') or f.name in ('LICENSE','.gitignore'):
            out.append(f)
    return sorted(out)
def make_manifest(root):
    root=Path(root)
    obj={'algorithm':'sha256','files':{f.relative_to(root).as_posix():sha(f.read_bytes()) for f in source_files(root)}}
    replace_local(root/'SOURCE_MANIFEST.json',obj);return obj
def verify_source(root):
    root=Path(root);p=root/'SOURCE_MANIFEST.json'
    if not p.exists():return {'pass':False,'issues':['missing SOURCE_MANIFEST']}
    m=read(p);issues=[]
    actual={f.relative_to(root).as_posix():sha(f.read_bytes()) for f in source_files(root)}
    for k,v in m['files'].items():
        if actual.get(k)!=v:issues.append('missing or altered '+k)
    issues+=['unregistered '+k for k in actual if k not in m['files']]
    return {'pass':not issues,'files':len(m['files']),'manifest_sha256':sha(p.read_bytes()),'issues':issues}
@contextmanager
def lock(folder):
    p=Path(folder)/'.write.lock';p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('x',encoding='utf-8') as f:f.write(json.dumps({'pid':os.getpid(),'at':now()}))
    try:yield
    finally:p.unlink(missing_ok=True)
@contextmanager
def no_network():
    old=(socket.socket,socket.create_connection,socket.getaddrinfo)
    def denied(*a,**k):raise RuntimeError('R5_OFFLINE_ONLY: network disabled')
    socket.socket=denied;socket.create_connection=denied;socket.getaddrinfo=denied
    try:yield
    finally:socket.socket,socket.create_connection,socket.getaddrinfo=old
def bundle(root,out):
    root=Path(root);out=Path(out)
    if out.exists():raise FileExistsError('bundle already exists')
    items={}
    # No secrets, old run directories, virtual environments or arbitrary user files.
    registered=read(root/'SOURCE_MANIFEST.json')['files']
    for name in list(registered)+['SOURCE_MANIFEST.json']:
        pp=PurePosixPath(name)
        if pp.is_absolute() or '..' in pp.parts or '\\\\' in name:raise ValueError('unsafe registered path')
        if '.local.' in name or pp.name.startswith('.env') or pp.suffix in ('.pem','.key'):continue
        f=root/name
        if f.is_symlink():raise ValueError('source symlink')
        if f.exists():items['kit_source/'+name]=f.read_bytes()
    r=root/'runs/R5_offline'
    fixed={'manifest.json','status.json','execution_summary.json','compilation.json','model_validation.json','scaling.json',
       'calibration/fitted.json','calibration/split_ids.json','calibration/diagnostic.json','calibration/timing.json',
       'private/validation.json','private/cases.json','audit/report.json','audit/scientific_hashes.json',
       'audit/per_task.csv','audit/summary.csv','audit/paired.csv'}
    if r.exists():
        for f in sorted(r.rglob('*')):
            if f.is_symlink():raise ValueError('run symlink')
            if not f.is_file():continue
            name=f.relative_to(r).as_posix()
            allowed=name in fixed or bool(re.fullmatch(r'trajectories/[0-9]{3}_(single|shared)_[a-z0-9_]+\.json',name))
            if name.startswith('code_snapshot/'):
                allowed=name[len('code_snapshot/'):] in registered or name=='code_snapshot/SOURCE_MANIFEST.json'
            if allowed:items['run/'+name]=f.read_bytes()
    bad=re.compile(rb'(sk-[A-Za-z0-9_-]{20,}|Bearer[ ]+[A-Za-z0-9._-]{20,}|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----)')
    if any(bad.search(b) for b in items.values()):raise ValueError('BLOCKED_SENSITIVE_CONTENT; do not weaken scan')
    m={'task':'R5_TASK_LOSS_OFFLINE_01','new_llm_calls':0,
       'files':{k:{'sha256':sha(v),'bytes':len(v)} for k,v in items.items()}}
    out.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(out,'x',zipfile.ZIP_DEFLATED) as z:
        for k,v in items.items():z.writestr(k,v)
        z.writestr('BUNDLE_MANIFEST.json',canonical(m)+b'\n')
    return verify_bundle(out)
def verify_bundle(path):
    with zipfile.ZipFile(path) as z:
        infos=z.infolist();names=[x.filename for x in infos]
        if len(names)>20000 or sum(x.file_size for x in infos)>512*1024**2 or len(set(names))!=len(names):
            raise ValueError('invalid archive size/duplicates')
        for x in infos:
            pp=PurePosixPath(x.filename)
            if pp.is_absolute() or '..' in pp.parts or '\\' in x.filename or stat.S_ISLNK(x.external_attr>>16) or x.flag_bits&1:
                raise ValueError('unsafe archive path')
        if 'BUNDLE_MANIFEST.json' not in names:raise ValueError('missing bundle manifest')
        m=json.loads(z.read('BUNDLE_MANIFEST.json'));expected=set(m['files'])|{'BUNDLE_MANIFEST.json'}
        if set(names)!=expected:raise ValueError('unexpected or missing archive members')
        for k,v in m['files'].items():
            b=z.read(k)
            if len(b)!=v['bytes'] or sha(b)!=v['sha256']:raise ValueError('archive content mismatch '+k)
        return {'pass':True,'files':len(m['files']),'sha256':sha(Path(path).read_bytes())}
