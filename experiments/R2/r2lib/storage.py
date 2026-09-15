
"""Immutable run contracts and allowlisted export. No API calls."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,re,platform,zipfile,os
from pilot.common import digest,read_json,write_json,public_config,utcnow
from .session import write_once
ROOT=Path(__file__).resolve().parents[1]

def source_paths(root=ROOT):
    root=Path(root);paths=[]
    for name in ("r2.py","requirements.txt","config.example.json","billing.example.json","README_ZH.md","EXECUTION_PROMPT_ZH.md","LICENSE"):
        f=root/name
        if f.exists():paths.append(f)
    for name in ("r2lib","pilot","vendor","configs","tests","docs","regression"):
        if (root/name).exists():
            paths.extend(x for x in (root/name).rglob("*") if x.is_file() and x.suffix in (".py",".md",".json",".txt") and "__pycache__" not in x.parts)
    if any(x.is_symlink() for x in paths):raise ValueError("Symlink in source")
    return sorted(set(paths))

def source_hashes(root=ROOT):
    root=Path(root)
    return {x.relative_to(root).as_posix():hashlib.sha256(x.read_bytes()).hexdigest() for x in source_paths(root)}

def verify_distribution(root=ROOT):
    root=Path(root);f=root/"SOURCE_MANIFEST.json"
    if not f.exists():raise ValueError("Missing distribution SOURCE_MANIFEST.json")
    declared=read_json(f)["sha256"];current=source_hashes(root)
    if declared!=current:raise ValueError("Delivered source/config template changed; do not run paid experiments. Re-extract unchanged kit.")
    return {"pass":True,"files":len(current),"source_manifest_sha256":hashlib.sha256(f.read_bytes()).hexdigest()}

def profile(cfg):
    keep=("base_url","model","max_tokens_field","max_output_tokens","temperature","extra_body","instruction_role","backend_kind")
    x={k:cfg[k] for k in keep};x["base_url_sha256"]=digest(x.pop("base_url"))
    return x

def freeze(run_dir,cfg,study,spec,billing,root=ROOT):
    root=Path(root);run_dir=Path(run_dir);run_dir.mkdir(parents=True,exist_ok=True)
    contract={"version":"r2-2.0.0","config":public_config(cfg),"study":study,"spec":spec,
              "billing_schedule":billing,"source_hashes":source_hashes(root)}
    fp=digest(contract);f=run_dir/"manifest.json"
    if f.exists():
        old=read_json(f)
        if old["fingerprint"]!=fp:raise ValueError("Run frozen: model/config/code/protocol/prices changed.")
        return old
    import numpy
    m={**contract,"fingerprint":fp,"created_utc":utcnow(),"profile_sha256":digest(profile(cfg)),
       "runtime":{"python":platform.python_version(),"numpy":numpy.__version__,"os":platform.system()},
       "evidence_label":"SOFTWARE_TEST_NOT_RESEARCH" if cfg["backend_kind"]=="test_fixture" else "REAL_ENDPOINT_CONTROLLED_DEVELOPMENT_NOT_CONFIRMATORY"}
    write_json(f,m)
    for src in source_paths(root):
        dst=run_dir/"code_snapshot"/src.relative_to(root);dst.parent.mkdir(parents=True,exist_ok=True);dst.write_bytes(src.read_bytes())
    return m

def append_event(root,name,event):
    p=Path(root)/name;p.parent.mkdir(parents=True,exist_ok=True)
    with p.open("a",encoding="utf-8") as f:f.write(json.dumps(event,ensure_ascii=False,allow_nan=False)+"\n")

def _sensitive(data):
    # Detect common credentials, not all personal data; never "sanitize to pass".
    text=data.decode("utf-8",errors="replace")
    patterns=[r"sk-[A-Za-z0-9_-]{20,}",r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----",
              r"(?i)bearer\s+[A-Za-z0-9_.-]{20,}"]
    return any(re.search(x,text) for x in patterns)

def export_bundle(root=ROOT,out=None):
    root=Path(root).resolve()
    if out is None:
        token=datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S_%fZ")
        out=root/"uploads"/("R2_feedback_"+token+".zip")
    out=Path(out).resolve()
    if out.exists():raise FileExistsError("Refusing to overwrite an existing feedback ZIP")
    entries={}
    def add(path,rel):
        # Check every path component below the root for symbolic links.
        q=path
        while q!=root:
            if q.is_symlink():raise ValueError("Symlink rejected during export")
            if q.parent==q:raise ValueError("Source is outside project")
            q=q.parent
        data=path.read_bytes()
        if _sensitive(data):raise ValueError("Common credential pattern found. Export blocked; do not delete evidence to pass.")
        entries[rel]=data
    # Code snapshot enables offline regeneration without exporting non-secret local endpoint URL.
    for f in source_paths(root):add(f,"kit_source/"+f.relative_to(root).as_posix())
    if (root/"SOURCE_MANIFEST.json").exists():add(root/"SOURCE_MANIFEST.json","kit_source/SOURCE_MANIFEST.json")
    for name in ("offline_reports","runs"):
        base=root/name
        if not base.exists():continue
        for f in sorted(base.rglob("*")):
            if f.is_symlink():raise ValueError("Symlink rejected during export")
            if not f.is_file():continue
            rel=f.relative_to(root)
            if any(x.startswith(".") for x in rel.parts) or f.suffix in (".tmp",".pyc",".pem",".key"):continue
            if name=="runs":
                parts=f.relative_to(base).parts
                if parts[0] not in ("R2_smoke","R2_recheck"):continue
                if len(parts)>2 and parts[1] not in ("attempts","calls","prefixes","records","private","code_snapshot"):continue
                if len(parts)==2 and parts[1] not in {
                    "manifest.json","status.json","smoke_result.json","endpoint_identity.json","controller_metadata.json",
                    "summary.json","SUMMARY.md","per_task.csv","per_call.csv","method_summary.csv","run_events.jsonl","replay_audit.json"}:continue
                if f.suffix not in (".json",".jsonl",".csv",".md",".py",".txt"):continue
                if "code_snapshot" in parts:
                    m=read_json(base/parts[0]/"manifest.json")
                    i=parts.index("code_snapshot");inner="/".join(parts[i+1:])
                    if inner not in m["source_hashes"]:continue
            elif f.suffix not in (".json",".md",".csv",".txt"):continue
            add(f,rel.as_posix())
    # Do not collect operator assertions automatically or private system files.
    checks={k:hashlib.sha256(v).hexdigest() for k,v in sorted(entries.items())}
    manifest={"task_id":"R2_RECHECK_MECHANISM_01","created_utc":utcnow(),"sha256":checks,
              "scientific_status":"REQUIRES_RESEARCHER_REVIEW","credentials_scan":"limited-pattern scan, not full privacy certification"}
    out.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(out,"x",zipfile.ZIP_DEFLATED) as z:
        for name,data in sorted(entries.items()):z.writestr(name,data)
        z.writestr("BUNDLE_MANIFEST.json",json.dumps(manifest,ensure_ascii=False,indent=2))
    verify_bundle(out)
    return out

def verify_bundle(path):
    with zipfile.ZipFile(path) as z:
        names=z.namelist()
        if len(names)!=len(set(names)):raise ValueError("Duplicate ZIP entry")
        for n in names:
            q=Path(n)
            if q.is_absolute() or ".." in q.parts or "\\" in n:raise ValueError("Unsafe archive path")
        m=json.loads(z.read("BUNDLE_MANIFEST.json"));expected=set(m["sha256"])|{"BUNDLE_MANIFEST.json"}
        if set(names)!=expected:raise ValueError("Archive entry set differs from manifest")
        for n,h in m["sha256"].items():
            if hashlib.sha256(z.read(n)).hexdigest()!=h:raise ValueError("Hash mismatch: "+n)
    return {"pass":True,"entries":len(expected)-1}
