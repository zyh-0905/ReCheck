"""Reproducible controlled stream study and executable SQL transport check."""
from pathlib import Path
import argparse
import gzip
import hashlib
import json
import time
import numpy as np
import pandas as pd
from .core import solve_refresh_dp
from .sql_environment import SQLToolWorld

ROOT=Path(__file__).resolve().parents[2]
W=np.array([[1.,0,0,0],[0,.35,0,0],[0,0,.65,0],[0,0,0,.2],[.6,.15,.25,0],[0,0,0,0]])
METHODS=['never','fresh','ttl','entropy','random','myopic','recheck','no_task']


def model(hazard:float,rho:float,weights=None):
    w=W.copy() if weights is None else np.asarray(weights,float)
    k,d=w.shape
    p=rho*np.eye(k)+(1-rho)*np.ones((k,k))/k
    factors=np.array([.5,1.,1.5,.8])[:d]
    h=np.minimum(hazard*factors,.49)
    return w,p,h


def make_stream(seed:int,p:np.ndarray,h:np.ndarray,n:int):
    r=np.random.default_rng(seed)
    tasks=np.empty(n,dtype=int); tasks[0]=r.integers(len(p))
    for t in range(1,n): tasks[t]=r.choice(len(p),p=p[tasks[t-1]])
    modes=np.empty((n+1,len(h)),dtype=np.int8);modes[0]=r.integers(0,2,size=len(h))
    for t in range(n):modes[t+1]=modes[t]^((r.random(len(h))<h).astype(np.int8))
    return tasks,modes


def run_stream(tasks,modes,w,h,price,method,parameter,solution,seed=0,trace=False):
    """Driver mediates exact receipts; policy state contains no mode labels."""
    n=len(tasks); d=w.shape[1];r=np.random.default_rng(seed+81923)
    cached=modes[0].copy()   # common, charged exact calibration prefix
    ages=np.zeros(d,dtype=int); probes=d; losses=0.; successes=0; actions=[]
    started=time.perf_counter()
    for t,k in enumerate(tasks):
        ages+=1
        q=(1-(1-2*h)**ages)/2
        if method=='never':take=np.zeros(d,dtype=bool)
        elif method=='fresh':take=w[k]>0
        elif method=='ttl':take=(ages>=int(parameter))&(w[k]>0)
        elif method=='entropy':take=(q>=float(parameter))&(w[k]>0)
        elif method=='random':take=(r.random(d)<float(parameter))&(w[k]>0)
        elif method=='myopic':take=w[k]*q>price+1e-12
        elif method in ('recheck','no_task'):take=solution.action(n-t,ages,int(k))
        else:raise ValueError(method)
        # Hidden modes are exposed only after the selected probes have been paid.
        cached[take]=modes[t+1,take];ages[take]=0;probes+=int(take.sum())
        error=(cached!=modes[t+1])
        loss=float(w[k]@error);ok=not bool(((w[k]>0)&error).any())
        losses+=loss;successes+=int(ok)
        if trace:
            actions.append({'t':t,'task':int(k),'probes':np.flatnonzero(take).tolist(),
                            'receipts':cached[take].astype(int).tolist(),'cached':cached.astype(int).tolist(),
                            'ages':ages.tolist(),'evaluation_only_loss':loss,'evaluation_only_success':ok})
    duration=(time.perf_counter()-started)*1e3
    return {'success':successes/n,'task_loss':losses/n,'probes_per_task':probes/n,
            'objective':(losses+price*probes)/n,'cpu_ms':duration,'tasks':n},actions


def calibrate(horizon:int,dev_seeds:list[int]):
    params={};records=[]
    grids={'ttl':[1,2,3,5,8,12,20,40], 'entropy':[.01,.03,.06,.1,.18,.3,.45],
           'random':[0.,.1,.25,.5,.75,1.]}
    for hazard in [.01,.05,.15]:
        for rho in [.2,.9]:
            w,p,h=model(hazard,rho)
            streams=[make_stream(s,p,h,horizon) for s in dev_seeds]
            for price in [.04,.12,.35]:
                key=f'{hazard}:{rho}:{price}';params[key]={}
                for method,grid in grids.items():
                    scored=[]
                    for x in grid:
                        score=np.mean([run_stream(a,b,w,h,price,method,x,None,seed=s)[0]['objective']
                                       for s,(a,b) in zip(dev_seeds,streams)])
                        scored.append((float(score),x))
                        records.append({'hazard':hazard,'rho':rho,'price':price,'method':method,'parameter':x,'objective':score})
                    params[key][method]=min(scored)[1]
    (ROOT/'configs/recheck_calibration.json').write_text(json.dumps(params,indent=2))
    pd.DataFrame(records).to_csv(ROOT/'results/recheck_development.csv',index=False)
    return params


def run_main(horizon=80,seeds=range(10000,10064)):
    params=json.loads((ROOT/'configs/recheck_calibration.json').read_text())
    records=[];compile_records=[]
    tracepath=ROOT/'results/recheck_traces.jsonl.gz'
    with gzip.open(tracepath,'wt',encoding='utf-8') as traces:
        for hazard in [.01,.05,.15]:
            for rho in [.2,.9]:
                w,p,h=model(hazard,rho)
                streams={s:make_stream(s,p,h,horizon) for s in seeds}
                for price in [.04,.12,.35]:
                    key=f'{hazard}:{rho}:{price}'
                    t0=time.perf_counter();sol=solve_refresh_dp(w,p,h,np.full(len(h),price),horizon)
                    comp=(time.perf_counter()-t0)*1000
                    t0=time.perf_counter();ab=solve_refresh_dp(np.tile(w.mean(0),(len(w),1)),p,h,np.full(len(h),price),horizon)
                    acomp=(time.perf_counter()-t0)*1000
                    compile_records.append({'hazard':hazard,'rho':rho,'price':price,'recheck_compile_ms':comp,'no_task_compile_ms':acomp})
                    for seed,(tasks,modes) in streams.items():
                        sid=f'h{hazard}_r{rho}_s{seed}'
                        for method in METHODS:
                            solution=ab if method=='no_task' else sol
                            out,trace=run_stream(tasks,modes,w,h,price,method,params[key].get(method),solution,seed=seed,trace=True)
                            row={'stream_id':sid,'seed':seed,'hazard':hazard,'rho':rho,'price':price,'method':method,**out}
                            records.append(row)
                            traces.write(json.dumps({'stream_id':sid,'price':price,'method':method,'initial_receipts':modes[0].tolist(),'events':trace},separators=(',',':'))+'\n')
                    print('ReCheck completed',key,flush=True)
    pd.DataFrame(records).to_csv(ROOT/'results/recheck_main.csv',index=False)
    pd.DataFrame(compile_records).to_csv(ROOT/'results/recheck_compile.csv',index=False)
    return records


def run_boundaries(horizon=80):
    rows=[]
    for true_h,assumed_h,label in [(0,0,'no_drift'),(.15,.01,'underestimated_drift'),(.01,.15,'overestimated_drift')]:
        w,p,h=model(true_h,.9);_,_,hm=model(assumed_h,.9)
        sol=solve_refresh_dp(w,p,hm,np.full(4,.12),horizon)
        for seed in range(20000,20032):
            tasks,modes=make_stream(seed,p,h,horizon)
            for method in ['never','fresh','myopic','recheck']:
                out,_=run_stream(tasks,modes,w,hm,.12,method,None,sol,seed)
                rows.append({'condition':label,'seed':seed,'method':method,**out})
    pd.DataFrame(rows).to_csv(ROOT/'results/recheck_boundaries.csv',index=False)
    # A two-bit parity task is intentionally outside the additive-loss theorem.
    parity={'prior':.5,'none_loss':.5,'one_probe_loss_plus_cost':.6,
            'two_probe_loss_plus_cost':.2,'single_probe_value_of_information':0.,
            'conclusion':'Single-step independent scores cannot capture XOR complementarity.'}
    (ROOT/'results/recheck_complementarity.json').write_text(json.dumps(parity,indent=2))


def run_sql(horizon=40):
    w=np.array([[1.,0],[0,1.],[.5,.5],[0,0]])
    w,p,h=model(.05,.8,w)
    rows=[];traces=[];price=.12
    sol=solve_refresh_dp(w,p,h,np.full(2,price),horizon)
    for seed in range(30000,30032):
        tasks,modes=make_stream(seed,p,h,horizon)
        for method in ['never','fresh','myopic','recheck']:
            with SQLToolWorld(seed) as env:
                env.set_modes(*modes[0]);cached=np.array([env.probe(j) for j in range(2)])
                ages=np.zeros(2,int);queries=2;ok=0;loss=0.;start=time.perf_counter()
                for t,k in enumerate(tasks):
                    env.set_modes(*modes[t+1]);ages+=1
                    q=(1-(1-2*h)**ages)/2
                    if method=='never': take=np.zeros(2,bool)
                    elif method=='fresh':take=w[k]>0
                    elif method=='myopic':take=w[k]*q>price
                    else:take=sol.action(horizon-t,ages,int(k))
                    for j in np.flatnonzero(take):cached[j]=env.probe(int(j));ages[j]=0;queries+=1
                    out=env.execute(int(k),cached)
                    good=env.evaluate(int(k),out);ok+=int(good)
                    loss+=float(w[k]@(cached!=modes[t+1]))
                    if seed==30000:traces.append({'method':method,'t':t,'task':int(k),'probes':np.flatnonzero(take).tolist(),'result':out,'evaluation_only_success':good})
                rows.append({'seed':seed,'method':method,'success':ok/horizon,'task_loss':loss/horizon,
                             'probes_per_task':queries/horizon,'objective':(loss+price*queries)/horizon,
                             'sql_calls':env.tool_calls,'cpu_ms':(time.perf_counter()-start)*1000,
                             'unchanged_schema':env.schema_fingerprint()==env.initial_schema_fingerprint})
    pd.DataFrame(rows).to_csv(ROOT/'results/recheck_sql.csv',index=False)
    (ROOT/'results/recheck_sql_example.json').write_text(json.dumps(traces,indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--stage',choices=['calibrate','main','boundaries','sql','all'],default='all')
    args=parser.parse_args();stage=args.stage
    if stage in ('calibrate','all'):calibrate(80,list(range(100,116)))
    if stage in ('main','all'):run_main()
    if stage in ('boundaries','all'):run_boundaries()
    if stage in ('sql','all'):run_sql()
