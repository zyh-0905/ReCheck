"""Fixed no-network study; models frozen before evaluation cases are generated."""
from pathlib import Path
import time,sys,platform,copy,json
import numpy as np
from . import data,storage,selection,acquisition as a,runtime

LEARNERS=('single','full','random','occupancy','decision')
def run_dir(root):return Path(root)/'runs/R6_offline'
def get_protocol(root):return storage.read(Path(root)/'configs/protocol.json')

def prepare(root):
    root=Path(root);check=storage.verify_source(root)
    if not check['pass']:raise ValueError('SOURCE_INTEGRITY: '+str(check['issues']))
    p=get_protocol(root);run=run_dir(root)
    if (run/'manifest.json').exists():
        m=storage.read(run/'manifest.json')
        if m['source_manifest_sha256']!=check['manifest_sha256'] or m['protocol']!=p:raise ValueError('frozen run/source mismatch')
        return {'existing':True,'status':storage.read(run/'status.json')['state']}
    if run.exists() and any(run.iterdir()):raise ValueError('nonempty unbound run')
    with storage.lock(run):
        m={'protocol':p,'protocol_sha256':data.digest(p),'source_manifest_sha256':check['manifest_sha256'],
           'source_hashes':storage.read(root/'SOURCE_MANIFEST.json')['files'],
           'created_at_utc':storage.now(),'environment':{'platform':platform.platform(),'machine':platform.machine(),
             'python':platform.python_version(),'numpy':np.__version__},'new_llm_api_calls':0}
        m['fingerprint']=data.digest({k:m[k] for k in ['protocol_sha256','source_manifest_sha256']})
        storage.write_once(run/'manifest.json',m)
        for name in list(m['source_hashes'])+['SOURCE_MANIFEST.json']:
            target=run/'code_snapshot'/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes((root/name).read_bytes())
        storage.replace_local(run/'status.json',{'state':'prepared','time_utc':storage.now()})
    return {'prepared':True,'protocol':p['id']}

def zero_model(method,panel):
    t=a.any_table().tolist()
    return {'learner':method,'panel':panel,'observed':{},'table':t,'selected_cells':[],
            'model_fingerprint':data.digest({'method':method,'table':t}),
            'cost':{'total_workflows':0,'label_executions':0,'reference_executions':0,'tool_calls':0,
                    'label_execution_seconds':0.,'reference_execution_seconds':0.},
            'selector_seconds':0.,'initial_fit_seconds':0.,'acquisition_elapsed_seconds':0.,'design_build_seconds':0.}

def run(root):
    root=Path(root);prepare(root);p=get_protocol(root);r=run_dir(root)
    status=storage.read(r/'status.json')
    if status['state']=='completed':return {'completed_run_no_resampling':True}
    if status['state']!='prepared':raise ValueError('RUN_PAUSED_OR_UNFINISHED: export evidence, do not restart')
    with storage.lock(r):
        storage.replace_local(r/'status.json',{'state':'running','time_utc':storage.now()})
        started=storage.now();tic=time.perf_counter();physical=0;timing=[]
        try:
            design=selection.Design(p)
            storage.write_once(r/'design_metadata.json',{'states':design.states,'design_build_seconds':design.build_seconds,
                'feature_bytes':design.X.nbytes,'basis_cells':[list(x) for x in design.cells],
                'scope':'hypothetical public states, not sampled evaluation worlds or true deployment distribution'})
            ids=data.split_ids(p);storage.write_once(r/'private/split_ids.json',ids)
            for panel,seeds in enumerate(ids['calibration']):
                print(f'Calibration panel {panel+1}/{len(ids["calibration"])}',flush=True)
                for li,learner in enumerate(LEARNERS):
                    budgets=[0] if learner=='single' else [100] if learner=='full' else p['selector_budgets']
                    results=selection.learn_panel(seeds,p,design,learner,budgets,p['selector_seed']+1000*panel+li)
                    storage.write_once(r/f'calibration/panel_{panel:03d}_{learner}.json',results)
                    physical+=results['total_physical_workflows']
                    for k,s in results['checkpoints'].items():
                        name='single_only' if learner=='single' else 'full_joint' if learner=='full' else f'{learner}_{k}'
                        s=copy.deepcopy(s);s['panel']=panel;s['standalone_cost_not_added_across_nested_checkpoints']=True
                        storage.write_once(r/f'models/panel_{panel:03d}_{name}.json',s)
                for method in ['any_exact','never']:storage.write_once(r/f'models/panel_{panel:03d}_{method}.json',zero_model(method,panel))
            fitted_at=time.perf_counter();cases=data.cases(p);storage.write_once(r/'private/cases.json',cases)
            count=0
            for panel in range(p['calibration_panels']):
                print(f'Frozen-policy evaluation panel {panel+1}/{p["calibration_panels"]}',flush=True)
                local=[c for c in cases if c['panel']==panel]
                for menu in p['menus']:
                    for method in p['methods']:
                        model=storage.read(r/f'models/panel_{panel:03d}_{method}.json')
                        ts=time.perf_counter();sol=runtime.planner(p,menu,model,method);setup=time.perf_counter()-ts
                        ts=time.perf_counter();sol.values('never' if method=='never' else 'exact',p['steps'],(1,1,1),p['budget']);compile_s=time.perf_counter()-ts
                        ci={'panel':panel,'method':method,'menu':menu,'setup_seconds':setup,'cold_compile_seconds':compile_s,
                            'initial_cache_info':sol.cache_info(),'shared_across_this_panel_only':True}
                        for c in local:
                            tr=runtime.run_one(c,p,menu,method,model,sol)
                            storage.write_once(r/f'trajectories/{c["id"]:03d}_{menu}_{method}.json',tr);count+=1
                        ci['final_cache_info']=sol.cache_info();timing.append(ci);sol.clear()
            storage.write_once(r/'compilation.json',timing)
            summary={'started_at_utc':started,'finished_at_utc':storage.now(),'run_seconds':time.perf_counter()-tic,
                     'training_and_design_seconds':fitted_at-tic,'physical_training_workflows':physical,
                     'base_streams':len(cases),'trajectories':count,'task_records':count*p['steps'],
                     'new_llm_api_calls':0,'network_allowed':False,'independent_training_panels':p['calibration_panels'],
                     'counts_note':'budgets16/32 are nested checkpoints, not independent training runs'}
            storage.write_once(r/'execution_summary.json',summary)
            storage.replace_local(r/'status.json',{'state':'completed','time_utc':storage.now()})
            return summary
        except BaseException as exc:
            storage.replace_local(r/'status.json',{'state':'paused','time_utc':storage.now(),'error_type':type(exc).__name__,
                'error':str(exc),'action':'export evidence; no automatic restart or lock deletion'})
            raise
