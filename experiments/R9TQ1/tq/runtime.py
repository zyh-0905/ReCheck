
"""One small qualification only. No research batch, no implicit resumption."""
from pathlib import Path
import os,sys,platform,time,zipfile,re
from .common import read,write,sha,digest,now,verify_source,locked,no_network
from .contract import ContractError
def checked(root):
 root=Path(root);source=verify_source(root)
 cfg=read(root/"config.json");proto=read(root/"protocol.json")
 required={"endpoint":"https://api.deepseek.com/v1/chat/completions","model":"deepseek-flash",
           "max_tokens":16384,"thinking":{"type":"enabled"},"reasoning_effort":"high","tool_choice":"auto",
           "stream":False,"max_attempts":12,"max_tools_per_response":4,"key_env":"LLM_API_KEY"}
 if any(cfg.get(k)!=v for k,v in required.items()):raise ContractError("Frozen profile mismatch")
 if proto.get("task_id")!="R9TQ1_NATIVE_TOOL_QUALIFICATION_01":raise ContractError("Wrong protocol")
 return {"source_manifest_sha256":source,"config":cfg,"protocol":proto,
         "binding":digest({"source":source,"config":cfg,"protocol":proto})}
def prepare(root):
 root=Path(root);b=checked(root)
 if sys.version_info[:2]!=(3,11):raise ContractError("Use existing Python 3.11.x environment")
 p=root/"PREPARED.json"
 if p.exists():
  old=read(p)
  if old["binding"]!=b["binding"]:raise ContractError("Prepared binding changed")
  return old
 if (root/"runs").exists():raise ContractError("Run exists without preparation; export instead")
 from legacy.native import NativeSession,FUNCTIONS
 import polars,numpy
 if polars.__version__!="0.20.31" or numpy.__version__!="1.26.4":raise ContractError("Use fixed native dependency versions")
 schemas=read(root/"fixtures/tools.json")
 if {t["function"]["name"] for t in schemas}!=set(FUNCTIONS):raise ContractError("Tool list mismatch")
 with no_network():
  for c in read(root/"fixtures/cases.json"):
   if NativeSession(c["snapshot"]).world()!=c["world_before"]:raise ContractError("Snapshot check failed")
 out={**b,"prepared_utc":now(),"environment":{"python":platform.python_version(),
     "platform":platform.system(),"machine":platform.machine(),"numpy":numpy.__version__,"polars":polars.__version__},
     "new_model_calls":0}
 write(p,out,once=True);return out
def qualify(root,confirm_calls,secret=None,exchange=None,test_endpoint=None):
 root=Path(root);b=checked(root)
 if confirm_calls!=12:raise ContractError("qualify requires --confirm-calls 12 (total upper limit)")
 prep=read(root/"PREPARED.json")
 if prep["binding"]!=b["binding"]:raise ContractError("Prepared binding mismatch")
 run=root/"runs/qualification";sp=run/"status.json"
 if sp.exists():
  prior=read(sp)
  if prior["status"] in ("completed","completed_not_qualified"):return prior
  raise ContractError("Paused or incomplete qualification cannot restart; audit/export for review")
 if run.exists() and any(run.iterdir()):raise ContractError("Orphan records: do not re-run")
 if (root/".run.lock").exists():raise ContractError("Run lock exists; do not delete")
 if secret is None:
  import getpass
  secret=os.environ.get("LLM_API_KEY") or getpass.getpass("LLM API key (hidden, not saved): ")
 if not secret:raise ContractError("No API key; no request sent")
 from .journal import Client
 from .engine import run_case
 run.mkdir(parents=True,exist_ok=True)
 start=now();tic=time.perf_counter();qual_results=[]
 with locked(root):
  write(run/"manifest.json",{**b,"created_utc":start,"evidence_kind":
       "SOFTWARE_TEST_NOT_RESEARCH" if exchange or test_endpoint else "REAL_ENDPOINT_INTERFACE_QUALIFICATION"},once=True)
  write(sp,{"status":"running","started_utc":start})
  cl=Client(b["config"],run,read(root/"fixtures/tools.json"),secret,exchange,test_endpoint)
  try:
   for case in read(root/"fixtures/cases.json"):
    r=run_case(case,cl,run/"cases"/case["id"]);qual_results.append(r["qualification"])
    if not r["qualification"]["qualified"]:
     result={"status":"completed_not_qualified","qualification_pass":False,"case_results":qual_results,
             "reason":"Native chain or task-state qualification not satisfied; no further cases started"}
     break
   else:result={"status":"completed","qualification_pass":True,"case_results":qual_results}
  except Exception as exc:
   # Known contract errors are controlled text; unknown native/runtime errors omit their possibly sensitive message.
   msg=str(exc) if isinstance(exc,ContractError) else "Local runtime error; preserve evidence for review"
   if secret in msg:msg=msg.replace(secret,"[REDACTED]")
   result={"status":"paused","qualification_pass":False,"error_type":type(exc).__name__,"error":msg,
           "case_results":qual_results}
  result.update(started_utc=start,ended_utc=now(),elapsed_seconds=time.perf_counter()-tic,
                recorded_attempts=len(cl.requests()),automatic_full_research_authorized=False)
  write(sp,result)
 return result
def audit(root):
 from .audit import audit as run_audit
 return run_audit(root)
def export(root):
 root=Path(root)
 if (root/".run.lock").exists():raise ContractError("Run active or lock remains; never export changing files")
 source=read(root/"SOURCE_MANIFEST.json")["files"]
 candidates=[root/p for p in source]+[root/"SOURCE_MANIFEST.json"]
 if (root/"PREPARED.json").exists():candidates.append(root/"PREPARED.json")
 if (root/"runs").exists():candidates += [p for p in (root/"runs").rglob("*") if p.is_file()]
 files={}
 secret_patterns=[re.compile(rb"(?i)Bearer\s+[a-zA-Z0-9._\-]{16,}"),re.compile(rb"\bsk-[a-zA-Z0-9]{20,}\b")]
 for p in sorted(set(candidates)):
  if p.is_symlink() or not p.resolve().is_relative_to(root.resolve()):raise ContractError("Unsafe export path")
  rel=p.relative_to(root).as_posix();raw=p.read_bytes()
  if any(rx.search(raw) for rx in secret_patterns):raise ContractError("Possible credential in export; no ZIP created")
  files[rel]=raw
 manifest={k:{"bytes":len(v),"sha256":sha(v)} for k,v in files.items()}
 folder=root/"uploads";folder.mkdir(exist_ok=True)
 path=folder/("R9TQ1_feedback_"+now().replace(":","").replace("-","").replace("+0000","Z")+".zip")
 with zipfile.ZipFile(path,"x",compression=zipfile.ZIP_DEFLATED) as z:
  for name,b in files.items():z.writestr(name,b)
  z.writestr("BUNDLE_MANIFEST.json",__import__("json").dumps({"files":manifest},sort_keys=True,indent=2))
 return str(path)
