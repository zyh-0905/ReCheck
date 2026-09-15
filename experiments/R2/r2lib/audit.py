
"""Independent OFFLINE scoring. Never import this module into online policy logic."""
from pilot.common import is_number
from pilot.recheck import valid_plan

def _answer_schema(ans,q):
    if not isinstance(ans,dict) or set(ans)!={"total","count"}:return False
    if q in (0,2):
        if not is_number(ans["total"]):return False
    elif ans["total"] is not None:return False
    if q in (1,2,3):
        if type(ans["count"]) is not int:return False
    elif ans["count"] is not None:return False
    return True

def evaluate_record(r,case,by_id=None):
    """Truth is only available after collection; stale exposure is not automatically a cause."""
    task=case["tasks"][r["step"]];q=task["type"];mem=r["worker_view"]["memory"]
    amount=mem.get("amount_divisor");endpoint=mem.get("endpoint_inclusive")
    am_ok=is_number(amount) and amount in (1,100);ep_ok=type(endpoint) is bool
    am_current=100 if task["modes"][0] else 1;ep_current=bool(task["modes"][1])
    ast="missing_or_invalid" if not am_ok else ("fresh" if amount==am_current else "stale")
    est="missing_or_invalid" if not ep_ok else ("fresh" if endpoint==ep_current else "stale")
    relevant=[ast] if q==0 else [est] if q==1 else [ast,est] if q==2 else []
    plan=r.get("plan");ans=r.get("answer");tool=r.get("tool_result",{})
    pv=valid_plan(plan,task);av=_answer_schema(ans,q)
    expected_total=sum(case["cents"])/100 if q in (0,2) else None
    expected_count=(len(case["cents"]) if q==3 else sum(i<=task["cutoff"] for i in range(len(case["cents"])))) if q in (1,2,3) else None
    value_shape=isinstance(ans,dict) and set(ans)=={"total","count"}
    value_ok=bool(value_shape and
        ((ans["total"] is None) if expected_total is None else (is_number(ans["total"]) and abs(ans["total"]-expected_total)<=1e-6)) and
        ((ans["count"] is None) if expected_count is None else (is_number(ans["count"]) and ans["count"]==expected_count)))
    plan_follows=False;answer_follows=False
    if pv and all(x!="missing_or_invalid" for x in relevant):
        plan_follows=((q not in (0,2) or plan["amount_divisor"]==amount) and
           (q not in (1,2) or plan["time_bound"]==task["cutoff"]+(not endpoint)))
    if av and pv and "error" not in tool:
        calc=tool.get("sum_amount_raw")
        answer_follows=((q not in (0,2) or (is_number(calc) and abs(ans["total"]-calc/plan["amount_divisor"])<=1e-6)) and
                        (q not in (1,2,3) or ans["count"]==tool.get("count_before",tool.get("count_all"))))
    calls=by_id or {};reasons=[];missing=0
    for k in r.get("logical_calls",[]):
        if k not in calls:missing+=1;continue
        reasons.append(calls[k].get("response",{}).get("choices",[{}])[0].get("finish_reason"))
    truncated="length" in reasons
    parse_bad=r.get("plan_json_error") is not None or r.get("answer_json_error") is not None
    success=bool(value_ok and av and pv and "error" not in tool and not truncated and not parse_bad and missing==0)
    stale="stale" in relevant
    # Offline deterministic diagnostic: obey the supplied memory exactly, not a paid LLM method.
    reference_correct=None
    if all(x!="missing_or_invalid" for x in relevant):
        ref_total=None;ref_count=None
        if q in (0,2):ref_total=(sum(case["cents"]) if task["modes"][0] else sum(case["cents"])/100)/amount
        if q in (1,2):
            bound=task["cutoff"]+(not endpoint)
            ref_count=sum((i<=bound if ep_current else i<bound) for i in range(len(case["cents"])))
        elif q==3:ref_count=len(case["cents"])
        reference_correct=bool((expected_total is None or abs(ref_total-expected_total)<=1e-6) and
                               (expected_count is None or ref_count==expected_count))
    return {"amount_status":ast,"endpoint_status":est,"stale_related":stale,
       "missing_related":"missing_or_invalid" in relevant,"plan_schema_valid_recomputed":pv,
       "answer_schema_valid":av,"interface_failure":not pv or "error" in tool,
       "json_parse_failure":parse_bad,"truncated":truncated,"missing_call_records":missing,
       "answer_value_correct":bool(value_ok),"end_to_end_success":success,"reference_executor_correct":reference_correct,
       "plan_follows_supplied_memory":bool(plan_follows),"answer_follows_tool_and_plan":bool(answer_follows),
       "stale_propagation_consistent":bool(stale and not value_ok and plan_follows and answer_follows and not parse_bad),
       "diagnostic_note":"Axes are observational; coincident staleness and error do not by themselves prove causality."}
