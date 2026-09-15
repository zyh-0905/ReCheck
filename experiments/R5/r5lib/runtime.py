"""Actual R4 reference API execution; no gold scoring during policy decisions."""
import copy,time
import numpy as np
from . import data,calibration,storage
from .model import Planner,posterior
from vendor.r4 import environment,worker

METHODS={'task_exact':('full','exact'),'task_rollout2':('full','rollout2'),'task_myopic':('full','myopic'),
         'single_effect_exact':('single','exact'),'any_exact':('any','exact'),
         'semantic_exact':('sum','exact'),'age_paced':('sum','age_paced'),'never':('sum','never')}

def get_table(method,fitted):
    kind=METHODS[method][0]
    if kind=='full':return np.asarray(fitted['table'])
    if kind=='single':return calibration.single_effect(fitted['table'])
    return calibration.semantic_table(binary=(kind=='any'))

def planner(method,p,menu,fitted):
    if method not in METHODS or menu not in ('single','shared'):raise ValueError('method/menu')
    return Planner(get_table(method,fitted),hazards=p['hazards'],transition=data.transition(p['persistence']),
                   price=p['credit_price'],budget=p['budget'],step_cap=p['step_cap'],shared=menu=='shared')

def packet_list(menu):
    out=[{'id':f's{j}','cover':[j],'cost':2} for j in range(3)]
    if menu=='shared':out +=[{'id':'p01','cover':[0,1],'cost':3},{'id':'p12','cover':[1,2],'cost':3}]
    return out

def science(obj):
    if isinstance(obj,dict):
        return {k:science(v) for k,v in obj.items() if not k.endswith('_seconds') and k not in ('cache_info','wall_started','wall_finished')}
    if isinstance(obj,list):return [science(v) for v in obj]
    return obj

def run_one(case,p,menu,method,fitted,solver=None):
    tic=time.perf_counter();s=solver or planner(method,p,menu,fitted);setup=time.perf_counter()-tic
    # Environment and its private rows remain outside the scheduler's interface.
    w=environment.World(case['rows']);w.set_modes(data.decode(case['initial_mode']))
    receipt=w.initial_calibration();mem=environment.decode_receipts(receipt);ages=(0,0,0)
    bank=environment.ProbeBudget(w,packet_list(menu),p['budget'],p['step_cap'])
    records=[];policy_kind=METHODS[method][1];cal=np.asarray(fitted['table'])
    start=time.perf_counter()
    for t,entry in enumerate(case['steps']):
        w.set_modes(data.decode(entry['true_mode']))
        a0=tuple(x+1 for x in ages);m0=data.encode_memory(mem);b0=bank.remaining;q=entry['q']
        ts=time.perf_counter();action=s.choose(policy_kind,p['steps']-t,a0,q,m0,b0);planning=time.perf_counter()-ts
        ts=time.perf_counter();receipts=bank.read(action.ids);probe_time=time.perf_counter()-ts
        mem.update(environment.decode_receipts(receipts));m1=data.encode_memory(mem)
        ages=tuple(0 if j in action.cover else a0[j] for j in range(3))
        view=worker.make_view(entry['task'],mem);plan=worker.rule_plan(view)
        ts=time.perf_counter();answer,trace=worker.execute(w,view,plan);tool_time=time.perf_counter()-ts
        prediction=float(posterior(ages,s.hazards)[m1]@cal[q,m1,:])
        records.append({'step':t,'q':q,'remaining_horizon':p['steps']-t,'ages_before':list(a0),
           'memory_before':m0,'memory_after':m1,'budget_before':b0,'budget_after':bank.remaining,
           'packets':list(action.ids),'cover':list(action.cover),'credits':action.cost,'receipts':receipts,
           'predicted_task_error_after_receipts':prediction,
           'view':view,'plan':plan,'trace':trace,'answer':answer,
           'planning_seconds':planning,'probe_seconds':probe_time,'tool_seconds':tool_time})
    out={'stream':case['id'],'condition':case['condition'],'menu':menu,'method':method,
       'case_sha256':storage.digest(case),'calibration_fingerprint':fitted['fingerprint'],
       'initial_receipts':receipt,'startup_credits_equivalent':6,'startup_outside_runtime_budget':True,
       'planner_setup_seconds':setup,'execution_seconds':time.perf_counter()-start,
       'records':records,'cache_info':s.cache_info(),'llm_calls':0}
    if solver is None:s.clear()
    return out
