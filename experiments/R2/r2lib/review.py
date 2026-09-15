
"""Offline metrics, ledger and prior-regression checks; not scientific approval."""
from pathlib import Path
from collections import defaultdict
import hashlib,json,csv
from pilot.common import read_json,write_json,digest,canonical,strict_json_object,request_payload
from .audit import evaluate_record
from .accounting import normalize_usage,price_call
ROOT=Path(__file__).resolve().parents[1]

def regression_checks():
    d=read_json(ROOT/"regression/previous_real_failures.json");rows=[]
    for x in d["examples"]:
        got=evaluate_record(x["record"],x["case"],x["calls_finish_only"])
        ok=all(got[k]==v for k,v in x["expected"].items())
        rows.append({"source_record":x["source_record"],"pass":ok,"evaluation":got})
    return {"pass":all(x["pass"] for x in rows),"examples":len(rows),"new_model_calls":0,"rows":rows}

def repair_cost_diagnostic():
    data=read_json(ROOT/"regression/repair_cost_inputs.json");g=data["groups"]
    full=g["full_regeneration/repair"];patch=g["llm_selected_patch/repair"];select=g["llm_selected_patch/selection"]
    return {"new_model_calls":0,"label":data["label"],"pricing_note":data["pricing_note"],
      "local_patch_call_ratio":(patch["calls"]+select["calls"])/full["calls"],
      "local_patch_cost_ratio":(patch["legacy_flat_USD_estimate"]+select["legacy_flat_USD_estimate"])/full["legacy_flat_USD_estimate"],
      "local_patch_latency_ratio":(patch["latency_seconds"]+select["latency_seconds"])/full["latency_seconds"],
      "selection_cost_to_all_generation":select["legacy_flat_USD_estimate"]/full["legacy_flat_USD_estimate"],
      "selection_cost_vs_saved_generation":select["legacy_flat_USD_estimate"]/(full["legacy_flat_USD_estimate"]-patch["legacy_flat_USD_estimate"]),
      "decision":"R2 pauses new RepairLens API trials. Need net-cost policy with a direct-recompute fallback.",
      "not_a_claim":"No current fee, hypothetical speedup, or RepairLens-algorithm superiority claimed."}

def _readlist(root,pattern):
    return [(p,read_json(p)) for p in sorted(Path(root).glob(pattern))]
def ledger_check(root):
    root=Path(root);ss=_readlist(root/"attempts","*_start.json");rr=_readlist(root/"attempts","*_result.json")
    cc=_readlist(root/"calls","*.json");starts={s.get("attempt"):s for _,s in ss};issues=[];orphans=[]
    results={r.get("attempt"):r for _,r in rr}
    if len(starts)!=len(ss):issues.append("duplicate_attempt_number")
    for path,r in rr:
        st=starts.get(r.get("attempt"))
        if st is None:orphans.append(path.name);continue
        for k in ("logical_id","request_sha256","payload","metadata"):
            if st.get(k)!=r.get(k):issues.append("start_result_mismatch:"+path.name+":"+k)
    for path,c in cc:
        if path.stem!=digest(c["logical_id"]):issues.append("call_filename_mismatch:"+path.name)
        r=results.get(c.get("attempt"))
        if r!=c:issues.append("call_not_equal_result:"+path.name)
    for path,st in ss:
        if "payload_sha256" in st and digest(st["payload"])!=st["payload_sha256"]:issues.append("payload_hash_mismatch:"+path.name)
    ids=[c["response"].get("id") for _,c in cc if c.get("status")=="ok"]
    nonnull=[x for x in ids if x is not None]
    if len(set(nonnull))!=len(nonnull):issues.append("duplicate_response_id")
    uncertain=[st for i,st in starts.items() if i not in results]
    return {"pass":not issues and not orphans,"registered_attempts":len(ss),"responses":len(rr),
      "completed_call_records":len(cc),"registered_without_result":len(uncertain),
      "unconfirmed_remote_receipt":len(uncertain),"orphan_results":orphans,"issues":issues,
      "request_errors":sum(r.get("status")!="ok" for _,r in rr),
      "length_responses":sum(c.get("response",{}).get("choices",[{}])[0].get("finish_reason")=="length" for _,c in cc),
      "uncertain_logical_ids":[x["logical_id"] for x in uncertain],
      "interpretation":"Structural consistency only; open starts do not prove remote receipt or billing."}

def _csv(path,rows):
    if not rows:return
    keys=list(dict.fromkeys(k for r in rows for k in r))
    with Path(path).open("w",newline="",encoding="utf-8-sig") as f:
        w=csv.DictWriter(f,keys);w.writeheader()
        for r in rows:w.writerow({k:json.dumps(v,ensure_ascii=False) if isinstance(v,(dict,list)) else v for k,v in r.items()})

def _sum_known(rows,key):
    vals=[x.get(key) for x in rows]
    return {"known_sum":sum(x for x in vals if isinstance(x,(int,float)) and not isinstance(x,bool)),
            "unknown_count":sum(x is None for x in vals)}

def summarize(root,billing=None):
    root=Path(root);man=read_json(root/"manifest.json");billing=billing or man.get("billing_schedule",{"enabled":False})
    lc=ledger_check(root);completions=[r for _,r in _readlist(root/"calls","*.json")]
    byid={r["logical_id"]:r for r in completions};callrows=[]
    for _,c in _readlist(root/"attempts","*_result.json"):
        usage=normalize_usage(c.get("response",{}).get("usage"));pr=price_call(c,billing);meta=c.get("metadata",{})
        callrows.append({"logical_id":c["logical_id"],"method":meta.get("method","shared_prefix"),
           "phase":meta.get("phase"),"stream":meta.get("stream"),"step":meta.get("step"),
           "status":c["status"],"finish_reason":c.get("response",{}).get("choices",[{}])[0].get("finish_reason"),
           **usage,"latency_seconds":c.get("latency_seconds"),"estimate":pr["estimate"],
           "currency":pr["currency"],"price_reason":pr["reason"]})
    rows=[];cases={}
    if (root/"private/recheck_cases.json").exists():
        cases={c["stream"]:c for c in read_json(root/"private/recheck_cases.json")}
    records=[r for _,r in _readlist(root/"records","*.json")]
    for r in records:
        e=evaluate_record(r,cases[r["stream"]],byid)
        rows.append({"stream":r["stream"],"step":r["step"],"method":r["method"],"regime":cases[r["stream"]]["regime"],
          "order_index":r.get("order_index"),"probe_count":r["probe_count"],"proxy_probe_cost_NOT_CURRENCY":r["model_probe_cost"],
          "local_planning_seconds":r["planning_seconds"],"local_probe_seconds":r["probe_seconds"],
          "local_tool_seconds":r["tool_seconds"],"plan_request_payload_sha256":digest(byid[r["logical_calls"][0]]["payload"]) if r["logical_calls"][0] in byid else None,**e})
    agg=[];methods=man["spec"].get("methods",[])
    prefix=[x for x in callrows if x["phase"]=="shared_prefix"]
    for method in methods:
        rs=[r for r in rows if r["method"]==method];cs=[c for c in callrows if c["method"]==method]
        n=len(rs)
        agg.append({"method":method,"completed_records":n,"planned_records":man["spec"]["steps"]*len(man["spec"]["streams"]),
           "successes":sum(r["end_to_end_success"] for r in rs),"success_rate_completed_only":sum(r["end_to_end_success"] for r in rs)/n if n else None,
           "independent_streams":len({r["stream"] for r in rs}),"probe_count":sum(r["probe_count"] for r in rs),
           "stale_related":sum(r["stale_related"] for r in rs),"stale_propagation_consistent":sum(r["stale_propagation_consistent"] for r in rs),
           "interface_failures":sum(r["interface_failure"] for r in rs),"response_records":len(cs),
           "output_tokens_known":_sum_known(cs,"completion_tokens")["known_sum"],
           "output_tokens_missing":_sum_known(cs,"completion_tokens")["unknown_count"],
           "llm_latency_seconds":sum(c["latency_seconds"] or 0 for c in cs),
           "list_price_estimate_excluding_prefix":sum(c["estimate"] for c in cs) if cs and all(c["estimate"] is not None for c in cs) else None,
           "local_recorded_seconds":sum(r["local_planning_seconds"]+r["local_probe_seconds"]+r["local_tool_seconds"] for r in rs)})
    paired={}
    for r in records:paired.setdefault((r["stream"],r["step"]),{})[r["method"]]=r
    equality=[]
    for (sid,t),g in sorted(paired.items()):
        if "recheck" in g and "myopic" in g:
            a,b=g["recheck"],g["myopic"]
            equality.append({"stream":sid,"step":t,"same_probe_choice":a["probed_channels"]==b["probed_channels"],
                "same_worker_view":a["worker_view"]==b["worker_view"],
                "same_plan_request":byid[a["logical_calls"][0]]["payload"]==byid[b["logical_calls"][0]]["payload"]})
    source_bad=[]
    for rel,h in man.get("source_hashes",{}).items():
        f=root/"code_snapshot"/rel
        if not f.exists() or hashlib.sha256(f.read_bytes()).hexdigest()!=h:source_bad.append(rel)
    summary={"study":man["study"],"evidence_label":man["evidence_label"],"phase":man["spec"].get("phase"),
      "scientific_gate":"PENDING_RESEARCHER_REVIEW_NOT_AUTOMATIC_PASS","ledger":lc,"methods":agg,
      "completed_records":len(rows),"planned_records":len(man["spec"].get("streams",[]))*man["spec"].get("steps",0)*len(methods),
      "source_snapshot_mismatches":source_bad,"dp_myopic_input_equality":equality,
      "shared_prefix":{"calls":len(prefix),"prompt_tokens":_sum_known(prefix,"prompt_tokens"),"completion_tokens":_sum_known(prefix,"completion_tokens"),
                       "llm_latency_seconds":sum(x["latency_seconds"] or 0 for x in prefix),
                       "list_price_estimate":sum(x["estimate"] for x in prefix) if prefix and all(x["estimate"] is not None for x in prefix) else None},
      "totals":{"prompt_tokens":_sum_known(callrows,"prompt_tokens"),"completion_tokens":_sum_known(callrows,"completion_tokens"),
                "reasoning_tokens":_sum_known(callrows,"reasoning_tokens"),"price":_sum_known(callrows,"estimate"),
                "unknown_unfinished_attempts":lc["registered_without_result"]},
      "limitations":["Prices unknown unless a model/date/currency scoped schedule was frozen; no invoices inferred.",
       "Interrupted cohorts have incomplete denominators; completed-only rates are descriptive.",
       "Four synthetic independent streams, not confirmatory evidence.",
       "Prefix is paid once in actual experiment; per-strategy deployment costing must attribute it without double-counting invoice.",
       "Latency sum excludes idle intervals; run_events.jsonl separately records whole invocation time.",
       "Proxy probe price is not API currency; do not sum unlike units."] }
    summary["controller_setup"]=read_json(root/"controller_metadata.json") if (root/"controller_metadata.json").exists() else None
    if (root/"run_events.jsonl").exists():
        events=[json.loads(x) for x in (root/"run_events.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()]
        ended=[x for x in events if x.get("event")=="invocation_ended"]
        summary["recorded_invocations_wall_seconds"]=sum(x.get("wall_seconds",0) for x in ended)
        summary["invocations_without_end"]=sum(x.get("event")=="invocation_started" for x in events)-len(ended)
    write_json(root/"summary.json",summary);_csv(root/"per_task.csv",rows);_csv(root/"per_call.csv",callrows);_csv(root/"method_summary.csv",agg)
    (root/"SUMMARY.md").write_text("# R2 offline summary\n\nResearcher review required. This is not an automatic scientific pass.\n\n```json\n"+json.dumps(summary,indent=2,ensure_ascii=False)+"\n```\n",encoding="utf-8")
    return summary

def replay_check(root):
    """Reconstruct requests and SQLite results from frozen responses; never create a network client."""
    import tempfile
    from . import experiment
    root=Path(root);m=read_json(root/"manifest.json")
    if m["study"]!="r2_recheck":
        return {"applicable":False,"new_model_calls":0}
    current={}
    for rel,sha in m["source_hashes"].items():
        f=ROOT/rel
        if not f.exists() or hashlib.sha256(f.read_bytes()).hexdigest()!=sha:current[rel]="code_mismatch"
    if current:return {"pass":False,"new_model_calls":0,"reason":"Current code differs; do not execute untrusted snapshot automatically.","mismatches":current}
    calls={c["logical_id"]:c for _,c in _readlist(root/"calls","*.json")}
    starts={c["logical_id"]:c for _,c in _readlist(root/"attempts","*_start.json")}
    cfg=m["config"];seen=[];errors=[]
    class AuditStop(Exception):pass
    class Replay:
        def complete(self,logical_id,messages,meta=None):
            body=request_payload(cfg,messages)
            known=calls.get(logical_id) or starts.get(logical_id)
            if known is None:raise AuditStop("next_call_not_started")
            seen.append(logical_id)
            if known.get("payload")!=body or known.get("metadata",{})!=(meta or {}):
                errors.append({"logical_id":logical_id,"reason":"request_or_metadata_differs"})
                raise AuditStop("request_mismatch")
            if logical_id not in calls:raise AuditStop("registered_without_response")
            r=calls[logical_id]
            body=r.get("response",{})
            identity_file=root/"endpoint_identity.json"
            if identity_file.exists():
                expected_identity=read_json(identity_file)
                got={"returned_model":body.get("model"),"system_fingerprint":body.get("system_fingerprint")}
                if got!=expected_identity:raise AuditStop("endpoint_identity_change")
            if r.get("status")!="ok":raise AuditStop("request_error")
            if r["response"]["choices"][0].get("finish_reason")!="stop":raise AuditStop("nonstop_response")
            try:strict_json_object(r["text"])
            except (ValueError,TypeError):raise AuditStop("invalid_json_response")
            return r
    stop=None
    with tempfile.TemporaryDirectory() as d:
        tmp=Path(d)
        try:experiment.run(Replay(),cfg,tmp,m["spec"])
        except AuditStop as exc:stop=str(exc)
        diffs=[]
        ignored={"planning_seconds","probe_seconds","tool_seconds"}
        for folder in ("records","prefixes","private"):
            for src in sorted((root/folder).glob("*.json")):
                expected=tmp/folder/src.name
                if not expected.exists():diffs.append(str(src.relative_to(root))+":not_rebuilt");continue
                a=read_json(src);b=read_json(expected)
                if folder=="records":a={k:v for k,v in a.items() if k not in ignored};b={k:v for k,v in b.items() if k not in ignored}
                if a!=b:diffs.append(str(src.relative_to(root))+":content_differs")
        unseen=set(calls)-set(seen)
        ok=not errors and not diffs and not unseen
        result={"pass":ok,"applicable":True,"new_model_calls":0,"request_bodies_checked":len(seen),
           "completed_calls_consumed":len(set(seen)&set(calls)),"stop_reason":stop,
           "request_mismatches":errors,"artifact_mismatches":diffs,"unconsumed_calls":sorted(unseen),
           "note":"Local reconstruction only, not provider identity or invoice authentication."}
    write_json(root/"replay_audit.json",result)
    return result
