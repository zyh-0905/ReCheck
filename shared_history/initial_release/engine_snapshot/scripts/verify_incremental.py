#!/usr/bin/env python3
"""Resumable same-environment replication for execution tools with time limits.

A completed ReCheck rerun can be adopted only after all scientific CSV columns
and uncompressed trace bytes are compared. RepairLens is re-executed and checked
one instance at a time; checkpoint updates never alter published first-run data.
"""
from pathlib import Path
import argparse,gzip,hashlib,json,sys,tempfile,time,datetime
import pandas as pd
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'scripts'))
from verify_reproduction import compare_scientific_frames
from src.repairlens.experiment import make_problem,run_case,FAMILIES,METHODS
from src.repairlens.core import Probe,RepairProblem

STATE=ROOT/'results/reproduction_progress.json'

def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def load_progress():
    inputs={str(p.relative_to(ROOT)):digest(p) for p in [ROOT/'configs/frozen_protocol.json',ROOT/'results/recheck_main.csv',ROOT/'results/repairlens_main.csv',ROOT/'results/repairlens_support_stress.csv']}
    if STATE.exists():
        state=json.loads(STATE.read_text());assert state['input_sha256']==inputs,'Inputs changed; do not reuse a stale verification checkpoint.'
    else:state={'input_sha256':inputs,'checks':{},'repair_seeds':[],'stress_seeds':[],'replication_rows':[],'elapsed_seconds':0.}
    return state

def save(state):
    temp=STATE.with_suffix('.tmp');temp.write_text(json.dumps(state,indent=2));temp.replace(STATE)

def adopt_recheck(workdir,state):
    workdir=Path(workdir)
    for f,keys in {
      'recheck_development.csv':['hazard','rho','price','method','parameter'],
      'recheck_main.csv':['seed','hazard','rho','price','method'],
      'recheck_boundaries.csv':['condition','seed','method'],
      'recheck_sql.csv':['seed','method']}.items():
        state['checks'][f]=compare_scientific_frames(pd.read_csv(ROOT/'results'/f),pd.read_csv(workdir/'results'/f),keys)
    assert json.loads((ROOT/'configs/recheck_calibration.json').read_text())==json.loads((workdir/'configs/recheck_calibration.json').read_text())
    with gzip.open(ROOT/'results/recheck_traces.jsonl.gz','rb') as a,gzip.open(workdir/'results/recheck_traces.jsonl.gz','rb') as b:
        aa=a.read();bb=b.read();assert aa==bb
        state['checks']['recheck_traces.jsonl.gz']={'match':True,'decompressed_sha256':hashlib.sha256(aa).hexdigest()}
    state['recheck_rerun_origin']='Completed ReCheck stages recovered from a time-limited full rerun; all scientific outputs compared, not merely accepted.'
    save(state);print('ReCheck rerun verified',flush=True)

def verify_repair_batch(state,count):
    original=pd.read_csv(ROOT/'results/repairlens_main.csv')
    with gzip.open(ROOT/'results/repairlens_traces.jsonl.gz','rt') as f:
        traces={(x['seed'],x['method']):x['events'] for x in map(json.loads,f)}
    done=set(state['repair_seeds']);todo=[(10000+fi*100+x,f) for fi,f in enumerate(FAMILIES) for x in range(20) if 10000+fi*100+x not in done][:count]
    for seed,family in todo:
        start=time.perf_counter();p,truth,meta=make_problem(seed,family);rows=[]
        with tempfile.TemporaryDirectory(prefix='repair-check-') as tmp:
            for method in METHODS:
                row,trace=run_case(p,truth,meta,method,Path(tmp)/method)
                compare_scientific_frames(original[(original.seed==seed)&(original.method==method)],pd.DataFrame([row]),['seed','method'])
                assert trace==traces[(seed,method)],'Replay event ledger mismatch'
                rows.append(row)
        state['repair_seeds'].append(seed);state['replication_rows'].extend(rows);state['elapsed_seconds']+=time.perf_counter()-start
        save(state);print('Verified RepairLens',seed,len(state['repair_seeds']),'/120',flush=True)

def verify_stress_batch(state,count):
    original=pd.read_csv(ROOT/'results/repairlens_support_stress.csv')
    todo=[s for s in range(20000,20060) if s not in state['stress_seeds']][:count]
    for seed in todo:
        start=time.perf_counter();p,truth,meta=make_problem(seed,'general');keep=[i for i,m in enumerate(p.required_masks) if m!=meta['true_mask']];den=sum(p.prior[i] for i in keep)
        reduced=RepairProblem(tuple(p.required_masks[i] for i in keep),tuple(p.prior[i]/den for i in keep),p.artifact_costs,
             tuple(Probe(u.name,u.cost,tuple(u.outcomes[i] for i in keep),u.produces) for u in p.probes))
        with tempfile.TemporaryDirectory(prefix='stress-check-') as tmp:
            for label,pp in [('covered',p),('truth_omitted',reduced)]:
                row,_=run_case(pp,truth,meta,'exact',Path(tmp)/label);row={'condition':label,**row}
                compare_scientific_frames(original[(original.seed==seed)&(original.condition==label)],pd.DataFrame([row]),['condition','seed','method'])
        state['stress_seeds'].append(seed);state['elapsed_seconds']+=time.perf_counter()-start;save(state)
        print('Verified support stress',seed,len(state['stress_seeds']),'/60',flush=True)

def finalize(state):
    assert len(state['repair_seeds'])==120 and len(state['stress_seeds'])==60
    assert 'recheck_traces.jsonl.gz' in state['checks']
    state['checks']['repairlens_main.csv']={'match':True,'rows':1320,'method':'per-instance paired scientific columns and exact replay event ledgers; runtime excluded'}
    state['checks']['repairlens_support_stress.csv']={'match':True,'rows':120,'method':'per-instance paired scientific columns; runtime excluded'}
    out={'passed':True,'timestamp_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
         'scope':'Full same-environment deterministic replication, completed in resumable batches. NOT independent review or new samples.',
         'checks':state['checks'],'timing_policy':'Published first-run timings retained; repetition times may differ.',
         'execution_note':'Two monolithic attempts hit the tool wall-time limit. Complete ReCheck files were verified; RepairLens and stress cases were then verified in checkpointed batches.'}
    (ROOT/'results/reproduction_audit.json').write_text(json.dumps(out,indent=2));save(state);print(json.dumps(out,indent=2))

if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('--adopt-recheck');a.add_argument('--repair-batch',type=int,default=0);a.add_argument('--stress-batch',type=int,default=0);a.add_argument('--finalize',action='store_true');args=a.parse_args();state=load_progress()
    if args.adopt_recheck:adopt_recheck(args.adopt_recheck,state)
    if args.repair_batch:verify_repair_batch(state,args.repair_batch)
    if args.stress_batch:verify_stress_batch(state,args.stress_batch)
    if args.finalize:finalize(state)
