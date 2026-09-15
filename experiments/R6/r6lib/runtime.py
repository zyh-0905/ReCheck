"""Rule execution of paid-calibration planners. Runtime truth never enters choose."""
import time,math,numpy as np
from . import data,acquisition as a
from vendor import planner as mdl
from vendor.r4 import environment,worker

def table_for(model,method):return a.any_table() if method in ('any_exact','never') else np.asarray(model['table'],dtype=float)
def planner(p,menu,model,method):
    return mdl.Planner(table_for(model,method),hazards=p['hazards'],transition=data.transition(p['persistence']),
                       price=p['credit_price'],budget=p['budget'],step_cap=p['step_cap'],shared=menu=='shared')
def packets(menu):
    xs=[{'id':f's{j}','cover':[j],'cost':2} for j in range(3)]
    if menu=='shared':xs +=[{'id':'p01','cover':[0,1],'cost':3},{'id':'p12','cover':[1,2],'cost':3}]
    return xs

def run_one(case,p,menu,method,model,solver=None):
    tic=time.perf_counter();s=solver or planner(p,menu,model,method);setup=time.perf_counter()-tic
    w=environment.World(case['rows']);w.set_modes(data.decode(case['initial_mode']));receipt=w.initial_calibration()
    mem=environment.decode_receipts(receipt);ages=(0,0,0);bank=environment.ProbeBudget(w,packets(menu),p['budget'],p['step_cap'])
    records=[];start=time.perf_counter();policy='never' if method=='never' else 'exact';table=table_for(model,method)
    for t,e in enumerate(case['steps']):
        w.set_modes(data.decode(e['true_mode']));aa=tuple(x+1 for x in ages);m0=data.encode_memory(mem);b0=bank.remaining;q=e['q']
        ts=time.perf_counter();act=s.choose(policy,p['steps']-t,aa,q,m0,b0);pt=time.perf_counter()-ts
        ts=time.perf_counter();receipts=bank.read(act.ids);rt=time.perf_counter()-ts
        mem.update(environment.decode_receipts(receipts));m1=data.encode_memory(mem)
        ages=tuple(0 if j in act.cover else aa[j] for j in range(3));view=worker.make_view(e['task'],mem);plan=worker.rule_plan(view)
        ts=time.perf_counter();ans,trace=worker.execute(w,view,plan);tt=time.perf_counter()-ts
        # This diagnostic uses this policy's fitted kernel, not another method's table.
        probs=mdl.posterior(ages,s.hazards)[m1]
        prediction=float(math.fsum(float(probs[z])*float(table[q,m1,z]) for z in range(8)))
        records.append({'step':t,'q':q,'remaining_horizon':p['steps']-t,'ages_before':list(aa),
            'memory_before':m0,'memory_after':m1,'budget_before':b0,'budget_after':bank.remaining,
            'packets':list(act.ids),'cover':list(act.cover),'credits':act.cost,'receipts':receipts,
            'predicted_task_error_after_receipts':prediction,'view':view,'plan':plan,'trace':trace,'answer':ans,
            'planning_seconds':pt,'probe_seconds':rt,'tool_seconds':tt})
    out={'stream':case['id'],'panel':case['panel'],'condition':case['condition'],'menu':menu,'method':method,
         'case_sha256':data.digest(case),'calibration_fingerprint':model['model_fingerprint'],
         'initial_receipts':receipt,'startup_credits_equivalent':6,'startup_outside_runtime_budget':True,
         'planner_setup_seconds':setup,'execution_seconds':time.perf_counter()-start,'records':records,
         'cache_info':s.cache_info(),'llm_calls':0}
    if solver is None:s.clear()
    return out
