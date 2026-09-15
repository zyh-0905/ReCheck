
"""No new model output. Rebuild messages and replay recorded native tool transitions."""
from pathlib import Path
import copy,json,csv,traceback
from .common import read,write,digest,sha,verify_source,no_network
from .contract import canonical,strict_json,build_payload,validate_response,tool_reply,ContractError
def projection(obj):
 if isinstance(obj,dict):return {k:projection(v) for k,v in obj.items() if k!="elapsed_seconds"}
 if isinstance(obj,list):return [projection(v) for v in obj]
 return obj
def check_equal(a,b,label):
 if canonical(a)!=canonical(b):raise ContractError("Mismatch: "+label)
def _audit(root):
 from .runtime import checked
 from .engine import initial_messages,qualification
 from legacy.native import NativeSession
 from legacy.replay import replay_nondeterminism
 root=Path(root);binding=checked(root);prep=read(root/"PREPARED.json")
 check_equal(prep["binding"],binding["binding"],"prepare")
 run=root/"runs/qualification";status=read(run/"status.json") if (run/"status.json").exists() else {"status":"absent"}
 if status["status"]=="absent":
  return {"mechanical_pass":True,"execution_complete":False,"qualification_pass":False,"recorded_requests":0,
          "reconstructed_requests":0,"research_complete":False,"user_action":"Only run the fixed qualification if not previously started"}
 check_equal(read(run/"manifest.json")["binding"],binding["binding"],"run binding")
 tools_all=read(root/"fixtures/tools.json");cases=read(root/"fixtures/cases.json")
 reqfiles=sorted((run/"attempts").glob("*_request.json"))
 if len(reqfiles)>12:raise ContractError("Global request cap exceeded")
 requests={};records={};response_ids=set();envelope_failures=[];usage=[];expected_identity=None
 for i,p in enumerate(reqfiles,1):
  st=read(p);check_equal(st["attempt"],i,"attempt sequence")
  if st["logical_id"] in requests:raise ContractError("Duplicate logical request")
  if st["payload_sha256"]!=digest(st["payload"]) or st["request_sha256"]!=digest({"endpoint":binding["config"]["endpoint"],"payload":st["payload"]}):
   raise ContractError("Request hash mismatch")
  requests[st["logical_id"]]=st
  rp=run/"attempts"/f"{i:06d}_response.json";rawp=rp.with_suffix(".raw")
  if not rp.exists():continue
  rec=read(rp);records[st["logical_id"]]=rec
  for k in st:check_equal(st[k],rec[k],"request/response journal "+k)
  raw=rawp.read_bytes()
  check_equal(sha(raw),rec["raw_stored_sha256"],"raw bytes")
  if not rec["secret_redacted"]:check_equal(sha(raw),rec["raw_original_sha256"],"raw unchanged")
  if rec["response"] is not None:check_equal(strict_json(raw.decode()),rec["response"],"parsed wire")
  if not (run/"attempts"/f"{i:06d}_send_intent.json").exists():raise ContractError("No send intent")
  case=next(c for c in cases if c["id"]==st["metadata"]["case_id"])
  tools=tools_all if case["allowed_tools"]=="all" else [t for t in tools_all if t["function"]["name"] in case["allowed_tools"]]
  try:
   if rec["status"]!="received" or rec["http_status"]!=200:raise ContractError("Transport failure")
   v=validate_response(rec["response"],tools,expected_identity=expected_identity)
   expected_identity=v["identity"]
   if rec["response"]["id"] in response_ids:raise ContractError("Duplicate response ID")
   response_ids.add(rec["response"]["id"])
   usage.append({"logical_id":st["logical_id"],**v["usage"],"latency_seconds":rec["latency_seconds"]})
  except ContractError as e:envelope_failures.append({"logical_id":st["logical_id"],"reason":str(e)})
 if expected_identity is not None:check_equal(expected_identity,read(run/"endpoint_identity.json"),"identity")
 reconstructed=set();completed=[];finals=[];total_events=0
 for case in cases:
  directory=run/"cases"/case["id"]
  if not directory.exists():continue
  resultpath=directory/"result.json"
  complete=resultpath.exists();saved=read(resultpath) if complete else read(directory/"boundary.json")
  turns=saved["turns"];events=saved["events"]
  if len(turns)>case["max_requests"]:raise ContractError("Per-case cap exceeded")
  tools=tools_all if case["allowed_tools"]=="all" else [t for t in tools_all if t["function"]["name"] in case["allowed_tools"]]
  messages=initial_messages(case);used=set()
  session=NativeSession(case["snapshot"])
  check_equal(session.world(),case["world_before"],"initial world")
  event_i=0;terminated=False;final_text=""
  for j,turn in enumerate(turns):
   logical=case["id"]+f"/turn_{j:02d}"
   check_equal(turn["logical_id"],logical,"turn logical ID")
   check_equal(turn,read(directory/f"turn_{j:02d}.json"),"turn sidecar")
   st=requests[logical];rec=records[logical]
   check_equal(st["payload"],build_payload(binding["config"],messages,tools),"reconstructed request")
   check_equal(st["metadata"],{"case_id":case["id"],"turn":j},"metadata")
   v=validate_response(rec["response"],tools,used,expected_identity)
   check_equal(v["message"],turn["assistant_message"],"assistant message")
   check_equal(v["calls"],turn["decoded_calls"],"decoded calls")
   check_equal(v["kind"],turn["kind"],"turn kind")
   check_equal(st["request_sha256"],turn["request_sha256"],"turn request hash")
   check_equal(event_i,turn["event_start"],"event offset")
   messages.append(copy.deepcopy(v["message"]));reconstructed.add(logical);replies=[]
   if v["kind"]=="tools":
    for c in v["calls"]:
     used.add(c["id"]);e=events[event_i]
     with no_network(),replay_nondeterminism(e):r=session.call(c["name"],c["arguments"])
     check_equal(projection(session.events[-1]),projection(e),"native event")
     reply=tool_reply(c["id"],r);messages.append(reply);replies.append(reply);event_i+=1
   else:terminated=True;final_text=v["message"]["content"]
   check_equal(replies,turn["tool_messages"],"tool-role receipts")
   check_equal(event_i,turn["event_end"],"end offset")
  check_equal(event_i,len(events),"event count")
  total_events+=event_i
  if complete:
   check_equal(saved["initial_messages"],initial_messages(case),"initial messages")
   check_equal(saved["case_sha256"],digest(case),"case binding")
   check_equal(saved["final_messages"],messages,"final messages")
   check_equal(saved["final_world"],session.world(),"final world")
   check_equal(saved["final_snapshot"],session.snapshot(),"final native snapshot")
   check_equal(saved["terminated"],terminated,"termination")
   check_equal(saved["final_text"],final_text,"final content")
   check_equal(saved["model_calls"],len(turns),"case call count")
   q=qualification(case,events,session.world(),terminated,final_text)
   check_equal(q,saved["qualification"],"qualification score")
   finals.append(q);completed.append(case["id"])
  else:
   check_equal(saved["messages"],messages,"paused messages")
   check_equal(saved["world"],session.world(),"paused world")
   check_equal(saved["snapshot"],session.snapshot(),"paused snapshot")
   logical=saved["logical_id"]
   if logical in requests:
    check_equal(requests[logical]["payload"],build_payload(binding["config"],messages,tools),"partial request")
    reconstructed.add(logical)
 if set(requests)!=reconstructed:raise ContractError("Unbound or unreconstructed requests")
 check_equal(finals,status.get("case_results",[]),"status case summaries")
 if status["status"]=="completed":
  if completed!=[c["id"] for c in cases] or not all(q["qualified"] for q in finals):raise ContractError("Incorrect completed claim")
  if envelope_failures:raise ContractError("Completed with rejected response")
 if status["status"]=="completed_not_qualified" and (not finals or finals[-1]["qualified"]):
  raise ContractError("Not-qualified status lacks failing qualification")
 if status.get("recorded_attempts")!=len(reqfiles):raise ContractError("Attempt count in status")
 out={"mechanical_pass":True,"execution_complete":status["status"] in ("completed","completed_not_qualified"),
      "qualification_pass":status["status"]=="completed" and len(finals)==3,
      "recorded_requests":len(reqfiles),"reconstructed_requests":len(reconstructed),
      "completed_qualification_cases":completed,"native_tool_events":total_events,
      "retained_response_failures":envelope_failures,"status":status["status"],
      "research_complete":False,"automatic_full_research_authorized":False,
      "monetary_cost":"UNKNOWN","new_remote_model_calls":0,
      "usage_total":{k:sum(x[k] for x in usage if x.get(k) is not None) for k in ("prompt_tokens","completion_tokens","total_tokens","latency_seconds")},
      "usage_records":usage,
      "note":"Engineering qualification, not model reliability or experiment success rate; same-assistant replay"}
 return out

def audit(root):
 root=Path(root);out=root/"runs/AUDIT.json"
 try:
  with no_network():r=_audit(root)
 except Exception as e:
  r={"mechanical_pass":False,"execution_complete":False,"qualification_pass":False,
     "error_type":type(e).__name__,"error":str(e),"new_remote_model_calls":0,
     "research_complete":False,"instruction":"Preserve and export. Do not edit source, hashes or samples."}
 write(out,r);return r
