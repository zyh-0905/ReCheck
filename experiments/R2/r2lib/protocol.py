
"""Frozen, outcome-blind R2 protocol and public policy preflight."""
from pathlib import Path
import json,copy
import numpy as np
from vendor.recheck_core import solve_refresh_dp,mismatch_probability
ROOT=Path(__file__).resolve().parents[1]

def validate_protocol(s):
    required={"recheck","myopic","ttl","always","never"}
    if set(s["methods"])!=required or len(s["methods"])!=5:
        raise ValueError("R2 requires exactly the five declared methods.")
    if type(s["steps"]) is not int or not 1<=s["steps"]<=40:
        raise ValueError("Invalid horizon")
    n=len(s["streams"])*(1+s["steps"]*len(s["methods"])*2)
    if s["logical_calls"]!=n:raise ValueError("Declared call cap does not match design")
    if len({c["stream"] for c in s["streams"]})!=len(s["streams"]):raise ValueError("Duplicate stream")
    return s

def load_protocol():
    return validate_protocol(json.loads((ROOT/"configs/r2_protocol.json").read_text(encoding="utf-8")))

def public_task_types(cell,s):
    rng=np.random.default_rng(cell["task_seed"]);q=int(rng.integers(4));out=[]
    for t in range(s["steps"]):
        if t:q=int(rng.choice(4,p=s["transition"][q]))
        out.append(q)
    return out

def solution(cell,s):
    return solve_refresh_dp(np.array(s["weights"]),np.array(s["transition"]),
       np.array(s["assumed_hazards"]),np.array(cell["probe_price"]),s["steps"])

def choose(method,age,q,remaining,dp,cell,s):
    if method=="recheck":return dp.action(remaining,age,q)
    if method=="myopic":
        risk=np.array([mismatch_probability(int(x),float(h)) for x,h in zip(age,s["assumed_hazards"])])
        return np.array(s["weights"])[q]*risk>np.array(cell["probe_price"])
    if method=="ttl":return age>=s["ttl_age"]
    if method=="always":return np.ones(len(age),bool)
    if method=="never":return np.zeros(len(age),bool)
    raise ValueError("Unknown method")

def preflight(s=None):
    """Reads NO world state, flip seed, outcome labels or model responses."""
    s=s or load_protocol();rows=[]
    for cell in s["streams"]:
        dp=solution(cell,s);age={m:np.zeros(2,int) for m in ("recheck","myopic")}
        differing=[];timing_differing=[];stamp={m:[0,0] for m in age}
        seq=public_task_types(cell,s)
        for t,q in enumerate(seq):
            act={}
            for m in age:
                age[m]+=1;act[m]=choose(m,age[m],q,s["steps"]-t,dp,cell,s)
                for j in np.flatnonzero(act[m]):stamp[m][int(j)]=t+1
                age[m][act[m]]=0
            if not np.array_equal(act["recheck"],act["myopic"]):differing.append(t)
            if stamp["recheck"]!=stamp["myopic"]:timing_differing.append(t)
        state_diff=0
        for remaining in range(1,s["steps"]+1):
            for a in range(1,s["steps"]-remaining+2):
                ag=np.array([a,a])
                for q in range(4):
                    x=choose("recheck",ag,q,remaining,dp,cell,s);y=choose("myopic",ag,q,remaining,dp,cell,s)
                    state_diff+=int(np.count_nonzero(x!=y))
        rows.append({"stream":cell["stream"],"task_seed":cell["task_seed"],"probe_price":cell["probe_price"],
          "task_types":seq,"same_age_state_action_disagreements":state_diff,
          "trajectory_probe_disagreements":len(differing),"differing_steps":differing,
          "public_evidence_timestamp_differences":len(timing_differing)})
    eq=s["preflight"]["same_age_equivalence_price"];sep=s["preflight"]["same_age_separation_price"]
    equivalent=all(r["same_age_state_action_disagreements"]==0 for r in rows if r["probe_price"]==[eq,eq])
    distinct=sum(r["trajectory_probe_disagreements"] for r in rows if r["probe_price"]==[sep,sep])
    return {"protocol_id":s["protocol_id"],"pass":equivalent and distinct>=s["preflight"]["minimum_trajectory_probe_disagreements"],
      "outcome_labels_inspected":0,"hidden_modes_constructed":0,"new_model_calls":0,
      "logical_calls":s["logical_calls"],"streams":rows,
      "interpretation":"Treatment opportunity only; no prediction of accuracy improvement or statistical significance.",
      "selection_disclosure":s["selection_disclosure"]}

def make_cases(s=None):
    s=s or load_protocol();cases=[]
    for cell in s["streams"]:
        # Independent randomness prevents world changes affecting public task construction.
        dr=np.random.default_rng(cell["data_seed"]);wr=np.random.default_rng(cell["world_seed"])
        cents=dr.integers(100,10001,size=20).tolist()
        modes=wr.integers(0,2,size=2);initial=modes.tolist();tasks=[]
        for q in public_task_types(cell,s):
            modes=modes ^ (wr.random(2)<cell["actual_hazard"]).astype(int)
            tasks.append({"type":q,"cutoff":int(dr.integers(5,15)),"modes":modes.tolist()})
        cases.append({"stream":cell["stream"],"seed":cell["task_seed"],"regime":cell["regime"],
                      "cents":cents,"initial_modes":initial,"tasks":tasks})
    return cases


def policy_spec(s):
    """Only model assumptions and action prices, never generation state or seeds."""
    return {k:copy.deepcopy(s[k]) for k in ("steps","weights","transition","assumed_hazards","ttl_age")}
