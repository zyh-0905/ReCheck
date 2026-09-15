"""Offline audit; all scientific conclusions require researcher review."""
from pathlib import Path
from collections import defaultdict
import hashlib,json,csv
from pilot.common import read_json,write_json,digest,canonical,strict_json_object,request_payload
from .accounting import normalize_usage,price_call
from . import worker,protocol
ROOT=Path(__file__).resolve().parents[1]
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

def replay_check(root):
    """Reconstruct requests and SQLite results from frozen responses; never create a network client."""
    import tempfile
    from . import experiment
    root=Path(root);m=read_json(root/"manifest.json")
    if m["study"]!="r4_recheck":
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


def evaluate_record(r,case,byid):
    from .environment import World,gold
    task=case['tasks'][r['step']];view=r['worker_view'];plan=r['plan']
    # Truth only enters this offline evaluator after collection.
    expected=gold(case['rows'],task);f=worker.freshness(task,r['memory_audit'],task['modes'])
    schema=worker.valid_plan(plan,view);answer_ok=r['answer']==expected
    call=byid.get(r['logical_calls'][0]);finish=call.get('response',{}).get('choices',[{}])[0].get('finish_reason') if call else None
    world=World(case['rows']);world.set_modes(task['modes']);rp=worker.rule_plan(view);rule_answer,_=worker.execute(world,view,rp)
    actual_answer,trace=worker.execute(world,view,plan)
    success=bool(answer_ok and schema and call and call.get('status')=='ok' and finish=='stop')
    follows=schema and plan==rp
    return {**f,'success':success,'interface_failure':not schema,'plan_follows_evidence':follows,
        'answer_value_correct':answer_ok,'tool_trace_recomputed_equal':trace==r['tool_trace'] and actual_answer==r['answer'],
        'normative_reference_success_NOT_LLM':rule_answer==expected,'stale_propagation_consistent':bool(f['semantic_mismatches'] and follows and not answer_ok),
        'stale_but_answer_correct':bool(f['semantic_mismatches'] and answer_ok),'missing_call':call is None,'finish_reason':finish}


def summarize(root):
    root=Path(root);man=read_json(root/'manifest.json');lc=ledger_check(root)
    byid={c['logical_id']:c for _,c in _readlist(root/'calls','*.json')};cs=[]
    for _,c in _readlist(root/'attempts','*_result.json'):
        u=normalize_usage(c.get('response',{}).get('usage'));pr=price_call(c,man.get('billing_schedule',{}));m=c.get('metadata',{})
        cs.append({'logical_id':c['logical_id'],'method':m.get('method'),'replicate':m.get('replicate'),'stream':m.get('stream'),'step':m.get('step'),
          'status':c['status'],'finish_reason':c.get('response',{}).get('choices',[{}])[0].get('finish_reason'),**u,
          'latency_seconds':c.get('latency_seconds'),'estimate':pr['estimate'],'currency':pr['currency'],'price_reason':pr['reason']})
    cases={c['stream']:c for c in read_json(root/'private/recheck_cases.json')} if (root/'private/recheck_cases.json').exists() else {}
    records=[r for _,r in _readlist(root/'records','*.json')];rows=[]
    for r in records:
        rows.append({k:r[k] for k in ('stream','condition','step','method','replicate','probe_count','credits_spent','budget_before','budget_after','planning_seconds','probe_seconds','tool_seconds')}|
          {'model_probe_cost_NOT_CURRENCY':r['model_probe_cost'],'payload_sha256':digest(byid[r['logical_calls'][0]]['payload']) if r['logical_calls'][0] in byid else None,
           **evaluate_record(r,cases[r['stream']],byid)})
    primary=[r for r in rows if r['replicate']=='primary'];rep=[r for r in rows if r['replicate']=='repeat'];agg=[]
    for cond in ['ALL_DESCRIPTIVE_ONLY']+sorted({r['condition'] for r in primary}):
        for method in man['spec'].get('methods',[]):
            rs=[r for r in primary if r['method']==method and (cond=='ALL_DESCRIPTIVE_ONLY' or r['condition']==cond)]
            ids={r['logical_calls'][0] for r in records if r['replicate']=='primary' and r['method']==method and (cond=='ALL_DESCRIPTIVE_ONLY' or r['condition']==cond)}
            calls=[c for c in cs if c['logical_id'] in ids]
            agg.append({'condition':cond,'method':method,'completed_primary':len(rs),'successes':sum(r['success'] for r in rs),
              'success_rate_completed_only':sum(r['success'] for r in rs)/len(rs) if rs else None,'independent_streams':len({r['stream'] for r in rs}),
              'probe_count':sum(r['probe_count'] for r in rs),'credit_units_NOT_CURRENCY':sum(r['credits_spent'] for r in rs),
              'semantic_loss_count':sum(r['semantic_mismatches'] for r in rs),'proxy_J_NOT_CURRENCY':sum(r['semantic_mismatches']+r['model_probe_cost_NOT_CURRENCY'] for r in rs),
              'interfaces_failed':sum(r['interface_failure'] for r in rs),'rule_compiler_successes_NOT_LLM':sum(r['normative_reference_success_NOT_LLM'] for r in rs),
              'stale_but_answer_correct':sum(r['stale_but_answer_correct'] for r in rs),
              'primary_prompt_tokens':_sum_known(calls,'prompt_tokens'),'primary_completion_tokens':_sum_known(calls,'completion_tokens'),
              'primary_model_latency_seconds':sum(c['latency_seconds'] or 0 for c in calls),'planning_seconds':sum(r['planning_seconds'] for r in rs),
              'price_estimate':sum(c['estimate'] for c in calls) if calls and all(c['estimate'] is not None for c in calls) else None})
    grouped=defaultdict(dict)
    for r in records:grouped[(r['stream'],r['step'],r['replicate'])][r['method']]=r
    paired=[]
    for (sid,t,replicate),g in sorted(grouped.items()):
        if 'recheck_joint' not in g:continue
        a=g['recheck_joint']
        for name,b in g.items():
            if name=='recheck_joint':continue
            paired.append({'stream':sid,'condition':a['condition'],'step':t,'replicate':replicate,'comparison_method':name,
              'packet_difference':a['packet_ids']!=b['packet_ids'],'coverage_difference':a['coverage']!=b['coverage'],
              'payload_difference':a['worker_view']!=b['worker_view'],
              'relevant_semantic_difference':a['worker_view']['evidence']!=b['worker_view']['evidence'],
              'joint_success':evaluate_record(a,cases[sid],byid)['success'],'comparison_success':evaluate_record(b,cases[sid],byid)['success']})
    flat={(r['stream'],r['step'],r['method'],r['replicate']):r for r in records};repeats=[]
    for r in records:
        if r['replicate']!='repeat':continue
        a=flat.get((r['stream'],r['step'],r['method'],'primary'))
        if a:
            c1=byid.get(a['logical_calls'][0],{});c2=byid.get(r['logical_calls'][0],{})
            repeats.append({'stream':r['stream'],'step':r['step'],'method':r['method'],'same_payload':c1.get('payload')==c2.get('payload'),
              'same_plan':a['plan']==r['plan'],'same_answer':a['answer']==r['answer'],'same_visible_text':c1.get('text')==c2.get('text')})
    budget_errors=[]
    for (sid,method) in sorted({(r['stream'],r['method']) for r in primary}):
        rest=man['spec']['episode_budget']
        for r in sorted((r for r in primary if r['stream']==sid and r['method']==method),key=lambda x:x['step']):
            if r['budget_before']!=rest or r['budget_after']!=rest-r['credits_spent'] or r['credits_spent']>man['spec']['step_cap'] or r['budget_after']<0:
                budget_errors.append([sid,method,r['step']])
            rest=r['budget_after']
    for r in rep:
        if r['credits_spent']!=0 or r['probe_count']!=0:budget_errors.append(['repeat_charged',r['stream'],r['step'],r['method']])
    bad=[]
    for path,h in man['source_hashes'].items():
        f=root/'code_snapshot'/path
        if not f.exists() or hashlib.sha256(f.read_bytes()).hexdigest()!=h:bad.append(path)
    events=[json.loads(x) for x in (root/'run_events.jsonl').read_text().splitlines() if x.strip()] if (root/'run_events.jsonl').exists() else []
    s={'study':man['study'],'evidence_label':man['evidence_label'],'scientific_gate':'PENDING_RESEARCHER_REVIEW','ledger':lc,
       'source_snapshot_mismatches':bad,'budget_violations':budget_errors,'completed_records':len(rows),'completed_primary_records':len(primary),
       'completed_repeat_records':len(rep),'planned_primary_records':man['spec'].get('primary_records',0),'planned_repeat_records':man['spec'].get('repeat_records',0),
       'methods':agg,'paired_treatments':paired,'repeat_diagnostics':repeats,
       'total_tokens':{k:_sum_known(cs,k) for k in ['prompt_tokens','completion_tokens','reasoning_tokens']},
       'total_model_latency_seconds':sum(c['latency_seconds'] or 0 for c in cs),
       'repeat_overhead':{'calls':sum(c['replicate']=='repeat' for c in cs),'completion_tokens':_sum_known([c for c in cs if c['replicate']=='repeat'],'completion_tokens')},
       'shared_calibration':{'streams':len(list((root/'prefixes').glob('*.json'))),'per_stream_channel_checks':3,'per_policy_startup_credit_equivalent':6,'startup_excluded_from_runtime_budget':True},
       'recorded_invocation_wall_seconds':sum(e.get('wall_seconds',0) for e in events if e.get('event')=='invocation_ended'),
       'limitations':['Twelve independent streams, three per condition; not 384 independent samples.',
          'Own controlled composite JSON API; not an external benchmark or public agent evaluation.',
          'Joint DP and base-tail rollout are finite-model references, not a new general theorem.',
          'Deterministic compiler uses identical public input; its diagnostic is not an extra LLM experiment.',
          'Credit budgets and objective prices are not currency. Negative results remain included.']}
    write_json(root/'summary.json',s);_csv(root/'per_task.csv',rows);_csv(root/'per_call.csv',cs);_csv(root/'method_summary.csv',agg);_csv(root/'paired.csv',paired)
    (root/'SUMMARY.md').write_text('# R4 local audit\n\nResearcher review required.\n\n```json\n'+json.dumps(s,ensure_ascii=False,indent=2)+'\n```\n')
    return s


def regression_checks():
    from .legacy_r2_audit import evaluate_record as old_evaluate
    src=read_json(ROOT/'regression/r2_failures.json');checks=[]
    for x in src['examples']:
        e=old_evaluate(x['record'],x['case'],x['calls_finish_only'])
        checks.append({'source_record':x['source_record'],'pass':all(e[k]==v for k,v in x['expected'].items()),'observations':e})
    return {'pass':all(x['pass'] for x in checks),'new_llm_calls':0,'old_responses_changed':False,'checks':checks}
