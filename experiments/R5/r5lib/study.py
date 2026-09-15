"""Offline experiment orchestration. No LLM/client/secret configuration exists."""
from pathlib import Path
import platform,sys,time,copy,gc,tracemalloc,csv
import numpy as np
from . import data,calibration,storage,runtime

def csv_write(path,rows):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    if not rows:return
    with path.open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)

def prepare(root):
    root=Path(root);check=storage.verify_source(root)
    if not check['pass']:raise ValueError(str(check))
    p=data.load_protocol();out=root/'runs/R5_offline'
    out.mkdir(parents=True,exist_ok=True)
    fingerprint=storage.digest({'protocol':p,'source':check['manifest_sha256']})
    manifest={'protocol_id':p['id'],'protocol':p,'source_manifest_sha256':check['manifest_sha256'],
       'fingerprint':fingerprint,'remote_llm_calls':0,'study_type':'offline_rule_execution',
       'python':sys.version.split()[0],'numpy':np.__version__,'platform':platform.platform(),
       'no_old_experiments_modified':True}
    if (out/'manifest.json').exists():
        old=storage.read(out/'manifest.json')
        if old['fingerprint']!=fingerprint:raise ValueError('prepared source/protocol mismatch; do not overwrite this run')
        return out
    ids=data.split_ids(p)
    allids=sum(ids.values(),[])
    if len(set(allids))!=len(allids):raise ValueError('split leakage')
    with storage.lock(out):
        start=time.perf_counter();train=calibration.fit(ids['calibration']);train_time=time.perf_counter()-start
        start=time.perf_counter();val=calibration.fit(ids['validation']);val_time=time.perf_counter()-start
        storage.write_once(out/'calibration/fitted.json',train)
        storage.write_once(out/'private/validation.json',val)
        storage.write_once(out/'calibration/split_ids.json',ids)
        storage.write_once(out/'calibration/diagnostic.json',calibration.residual_tables(train,val))
        storage.write_once(out/'calibration/timing.json',{'fit_seconds':train_time,'validation_seconds':val_time,
          'training_tool_executions':len(ids['calibration'])*5*64,'validation_tool_executions':len(ids['validation'])*5*64,
          'amortization':'one fitted table shared identically by all calibrated policies; not free production maintenance'})
        storage.write_once(out/'manifest.json',manifest)
        for f in storage.source_files(root)+[root/'SOURCE_MANIFEST.json']:
            rel=f.relative_to(root);dest=out/'code_snapshot'/rel;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(f.read_bytes())
        storage.replace_local(out/'status.json',{'state':'prepared','at':storage.now()})
    return out

def check_prepared(root):
    root=Path(root);out=root/'runs/R5_offline'
    if not (out/'manifest.json').exists():raise ValueError('run prepare first')
    p=data.load_protocol();ck=storage.verify_source(root);m=storage.read(out/'manifest.json')
    if not ck['pass'] or m['fingerprint']!=storage.digest({'protocol':p,'source':ck['manifest_sha256']}):
        raise ValueError('frozen source/protocol changed')
    return out,p

def model_diagnostics(p,train,val):
    """Disjoint validation risk is only evaluated after all policies are defined."""
    rows=[]
    for menu in p['menus']:
        for method in p['methods']:
            s=runtime.planner(method,p,menu,train);kind=runtime.METHODS[method][1]
            model=s.evaluate(kind,p['steps'],(1,1,1),p['budget'],train['table'],p['hazards'])
            validation=s.evaluate(kind,p['steps'],(1,1,1),p['budget'],val['table'],p['hazards'])
            # Protocol stratification: 16 starts modulo five, not assumed uniform.
            starts=np.bincount(np.arange(p['streams_per_condition'])%5,minlength=5)/p['streams_per_condition']
            rows.append({'menu':menu,'method':method,
              'calibration_model_expected_task_cost':float(starts@model.mean(axis=1)),
              'validation_model_expected_task_cost':float(starts@validation.mean(axis=1)),
              'label':'MODEL_EXPECTATION_NOT_LIVE_RESULTS'})
            s.clear()
    return rows

def scale(p,train):
    rows=[]
    for h in p['scale_horizons']:
        for method in ('task_exact','task_rollout2','task_myopic'):
            for rep in range(p['scale_repeats']):
                gc.collect();start=time.perf_counter();s=runtime.planner(method,p,'shared',train)
                s._indices(runtime.METHODS[method][1],h,(1,1,1),p['scale_budget'])
                elapsed=time.perf_counter()-start;ci=s.cache_info();s.clear();del s;gc.collect()
                # Memory tracing is a separate pass so timing isn't tracer-inflated.
                tracemalloc.start()
                s=runtime.planner(method,p,'shared',train)
                s._indices(runtime.METHODS[method][1],h,(1,1,1),p['scale_budget'])
                _,peak=tracemalloc.get_traced_memory();tracemalloc.stop();s.clear()
                rows.append({'horizon':h,'channels':3,'mode_states':8,'method':method,'repeat':rep,
                   'cold_initial_policy_seconds':elapsed,'peak_traced_python_bytes':peak,**ci,
                   'scope':'fresh model/first policy table; memory separate pass; not process RSS or large-n result'})
    return rows

def run(root):
    out,p=check_prepared(root)
    if (out/'status.json').exists() and storage.read(out/'status.json')['state']=='completed':
        print('Already completed: no new experiment or timing samples created.');return
    train=storage.read(out/'calibration/fitted.json')
    val=storage.read(out/'private/validation.json')
    cases=data.make_cases(p)
    start_wall=storage.now();start=time.perf_counter()
    with storage.lock(out):
        storage.replace_local(out/'status.json',{'state':'running','at':start_wall})
        try:
            storage.write_once(out/'private/cases.json',cases)
            compile_rows=[]
            for menu in p['menus']:
                for method in p['methods']:
                    # Each policy has its OWN precompiled cache. Shared across its
                    # evaluation streams, never borrowed from another policy.
                    begin=time.perf_counter();s=runtime.planner(method,p,menu,train)
                    s._indices(runtime.METHODS[method][1],p['steps'],(1,1,1),p['budget'])
                    ct=time.perf_counter()-begin
                    compile_rows.append({'menu':menu,'method':method,'compile_seconds':ct,**s.cache_info()})
                    for case in cases:
                        target=out/'trajectories'/f"{case['id']:03d}_{menu}_{method}.json"
                        if target.exists():
                            old=storage.read(target)
                            if old['case_sha256']!=storage.digest(case) or old['calibration_fingerprint']!=train['fingerprint']:
                                raise ValueError('Existing trajectory binding mismatch')
                            continue
                        result=runtime.run_one(case,p,menu,method,train,s)
                        storage.write_once(target,result)
                    s.clear();del s;gc.collect()
                    print('completed',menu,method,flush=True)
            storage.write_once(out/'compilation.json',compile_rows)
            ref=model_diagnostics(p,train,val)
            storage.write_once(out/'model_validation.json',ref)
            storage.write_once(out/'scaling.json',scale(p,train))
            storage.write_once(out/'execution_summary.json',{'streams':len(cases),'menus':len(p['menus']),
              'methods':len(p['methods']),'trajectories':len(cases)*len(p['menus'])*len(p['methods']),
              'task_evaluations':len(cases)*len(p['menus'])*len(p['methods'])*p['steps'],
              'remote_calls':0,'wall_started':start_wall,'wall_finished':storage.now(),'wall_seconds':time.perf_counter()-start,
              'resumption_note':'Existing complete trajectory files retained, no new statistical units'})
            storage.replace_local(out/'status.json',{'state':'completed','at':storage.now()})
        except BaseException as e:
            storage.replace_local(out/'status.json',{'state':'paused','exception_type':type(e).__name__,
                      'message':str(e)[:1000],'at':storage.now()})
            raise
