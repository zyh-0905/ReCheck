
"""Same native bridge as R9; here NO state-change events are injected."""
from pathlib import Path
import copy,time
from .common import read,write,digest,no_network
from .contract import canonical,build_payload,tool_reply,ContractError
from legacy.native import NativeSession
from legacy.scoring import grade

BASE="""You operate only a simulated contacts, messaging, reminders and device-settings environment.
Respect the user's exact intent and permitted state changes. Historical evidence can become outdated.
Use ONLY the native API tool_calls field to request a function. Do not print JSON actions, fabricate
tool outputs, or claim a tool ran before its actual tool-role result arrives. Prefer one tool per
response when calls depend on each other; if you request multiple independent tools, they will be
executed sequentially in the order returned. You cannot use arbitrary Python, shell or external tools.
After real tool results, continue if needed and finish with a concise natural-language response and
no tool_calls. A successful function return does not by itself prove the user's intended target.
Use the tool schemas and descriptions. This is a small interface qualification, not a benchmark.
"""
VERIFY="""Resolve a person or reminder identified by description from an appropriate current lookup.
Respect an explicit literal phone number instead of substituting a different number.
After a mutation, use an available read to confirm the relevant result before finishing.
Do not modify unrelated state. Do not duplicate a message while checking its delivery."""
def initial_messages(case):
 return [{"role":"system","content":BASE+("\n"+VERIFY if case["id"]!="q0_read" else "")+
          "\nYou have at most "+str(case["max_requests"])+" model responses including your final response."},
         {"role":"user","content":canonical(case["public"])}]

def qualification(case,events,final,terminated,final_text):
 ok_calls=[e for e in events if e["response"]["ok"]]
 roundtrip=bool(ok_calls) and terminated
 if case["contract"]["kind"]=="read_cellular":
  allowed=all(e["tool"]=="get_cellular_service_status" and e["before_world"]==e["after_world"] for e in events)
  correct_text="CELLULAR_ON" if case["world_before"]["setting"][0]["cellular"] else "CELLULAR_OFF"
  state_ok=final==case["world_before"] and allowed
  answer_ok=final_text.strip()==correct_text
  score={"read_only_state_preserved":state_ok,"observed_value_reported":answer_ok}
  good=roundtrip and state_ok and answer_ok
 else:
  score=grade(case["contract"],case["world_before"],events,final)
  state_ok=score["trace_safe_success"]
  if case["contract"]["kind"]=="reminder":
   lookup=any(e["tool"]=="search_reminder" and e["response"]["ok"] for e in events)
  else:lookup=True
  good=roundtrip and state_ok and lookup
 return {"qualified":bool(good),"roundtrip_ready":roundtrip,"task_state_ok":bool(state_ok),
         "terminated":bool(terminated),"score":score,"tool_calls":len(events),
         "native_tool_errors":sum(not e["response"]["ok"] for e in events),
         "not_a_research_success_rate":True}

def run_case(case,client,out):
 out=Path(out);out.mkdir(parents=True,exist_ok=True)
 with no_network():
  session=NativeSession(case["snapshot"])
  if session.world()!=case["world_before"]:raise ContractError("Case snapshot differs from frozen world")
 initial=initial_messages(case);messages=copy.deepcopy(initial);used=set();turns=[];final_text="";terminated=False
 tools=client.tools if case["allowed_tools"]=="all" else [t for t in client.tools if t["function"]["name"] in case["allowed_tools"]]
 tick=time.perf_counter()
 for turn in range(case["max_requests"]):
  logical=case["id"]+f"/turn_{turn:02d}"
  write(out/"boundary.json",{"case_id":case["id"],"logical_id":logical,"turn":turn,"messages":messages,
                           "events":session.events,"world":session.world(),"snapshot":session.snapshot(),"turns":turns})
  payload=build_payload(client.config,messages,tools)
  result=client.complete(logical,payload,{"case_id":case["id"],"turn":turn},tools,used)
  v=result["validated"];messages.append(copy.deepcopy(v["message"]))
  rec={"turn":turn,"logical_id":logical,"request_sha256":result["request_sha256"],
       "kind":v["kind"],"assistant_message":v["message"],"decoded_calls":v["calls"],
       "tool_messages":[],"event_start":len(session.events)}
  if v["kind"]=="final":
   terminated=True;final_text=v["message"]["content"]
  else:
   # All call names, argument schemas, IDs, and batch limits were checked before any dispatch.
   for c in v["calls"]:
    used.add(c["id"])
    with no_network():resp=session.call(c["name"],c["arguments"])
    reply=tool_reply(c["id"],resp);messages.append(reply);rec["tool_messages"].append(reply)
  rec["event_end"]=len(session.events);turns.append(rec);write(out/f"turn_{turn:02d}.json",rec,once=True)
  if terminated:break
 result={"case_id":case["id"],"source_case":case["source_case"],"case_sha256":digest(case),
        "initial_messages":initial,"turns":turns,"events":session.events,"final_messages":messages,
        "final_world":session.world(),"final_snapshot":session.snapshot(),"terminated":terminated,
        "final_text":final_text,"model_calls":len(turns),"elapsed_seconds":time.perf_counter()-tick,
        "qualification":qualification(case,session.events,session.world(),terminated,final_text),
        "environment_event_count":0,"evidence_kind":"NATIVE_INTERFACE_QUALIFICATION_NOT_R9_RESEARCH"}
 write(out/"result.json",result,once=True)
 return result
