"""Independent arithmetic, exact accounting, replay, scoped numeric audit.
Every result remains exploratory; mechanical acceptance never approves a paper.
"""
from pathlib import Path
from collections import defaultdict,Counter
import csv,json,copy,math,time
import numpy as np
from . import data,storage,acquisition as a,runtime,equivalence,selection,study

def expected_model_workflows(method,n):
    if method in ('any_exact','never'):return 0
    k=0 if method=='single_only' else 100 if method=='full_joint' else int(method.rsplit('_',1)[1])
    return (82+k+5)*n

def cost_units(failures,credits):
    if type(failures) is not int or type(credits) is not int or min(failures,credits)<0:raise ValueError('nonnegative integer cost counts')
    return failures*20+credits

def amortized(runtime_j,cal_workflows,episodes,price):
    if episodes<=0 or cal_workflows<0 or price<0:raise ValueError('cost parameters')
    return runtime_j+0.05*6+price*cal_workflows/episodes

def _trace_output(rows,z,path,args):
    bits=data.decode(z)
    if path=='/catalog/items':
        offset=args['page']-bits[0]
        if offset<0:return {'error':'PAGE_BEFORE_FIRST'}
        want=args['status_code']==1-bits[1];rs=[r for r in rows if r['active']==want];sz=args['page_size']
        return {'items':[{'sku':r['sku'],'category':r['category']} for r in rs[offset*sz:(offset+1)*sz]],
                'has_more':(offset+1)*sz<len(rs)}
    if path=='/inventory/batch':
        tab={r['sku']:r for r in rows};xs=[]
        for sku in args['skus']:
            if sku not in tab:return {'error':'UNKNOWN_SKU'}
            r=tab[sku];xs.append({'sku':sku,'stock_value':r['physical'] if bits[2] else max(0,r['physical']-r['reserved']),'reserved':r['reserved']})
        return {'items':xs}
    raise ValueError('unknown recorded path')

def check_task_trace(tr,case,p):
    issues=[]
    if tr.get('case_sha256')!=data.digest(case):issues.append('case binding')
    if len(tr.get('records',[]))!=len(case['steps']):return issues+['record count']
    budget=p['budget'];mem=case['initial_mode'];ages=[0,0,0];pack={x['id']:x for x in runtime.packets(tr['menu'])}
    for rec,e in zip(tr['records'],case['steps']):
        ids=rec['packets'];where=f'{case["id"]}/{tr["menu"]}/{tr["method"]}/{rec["step"]}'
        if len(set(ids))!=len(ids) or any(i not in pack for i in ids):issues.append(where+':bad packet');continue
        cost=sum(pack[i]['cost'] for i in ids);cover=sorted({j for i in ids for j in pack[i]['cover']});mask=sum(1<<j for j in cover)
        aa=[x+1 for x in ages];m1=(mem&(~mask&7))|(e['true_mode']&mask)
        if cost>budget or cost>p['step_cap'] or rec['credits']!=cost or rec['budget_before']!=budget or rec['budget_after']!=budget-cost:issues.append(where+':budget')
        if rec['memory_before']!=mem or rec['memory_after']!=m1 or rec['ages_before']!=aa or rec['cover']!=cover:issues.append(where+':state')
        expected=data.independent_execute(case['rows'],e['task'],m1,e['true_mode'])
        if rec['answer']!=expected:issues.append(where+':answer')
        for call in rec['trace']:
            if call['result']!=_trace_output(case['rows'],e['true_mode'],call['path'],call['args']):issues.append(where+':tool result')
        if rec['plan']!={**rec['view']['request'],**rec['view']['evidence']}:issues.append(where+':rule compiler')
        budget-=cost;mem=m1;ages=[0 if j in cover else aa[j] for j in range(3)]
    return issues

def check_ledger(result,panel,p,design):
    """Rebuild acquisitions using training-only re-execution; never use eval labels.
    Counts and discrete labels are strict, selector score is diagnostic-only.
    """
    name=result['method'];li=study.LEARNERS.index(name);seeds=data.split_ids(p)['calibration'][panel]
    budgets=[0] if name=='single' else [100] if name=='full' else p['selector_budgets']
    rebuilt=selection.learn_panel(seeds,p,design,name,budgets,p['selector_seed']+1000*panel+li)
    issues=[];count=0
    if len(result['ledger'])!=len(rebuilt['ledger']):issues.append('ledger length')
    for x,y in zip(result['ledger'],rebuilt['ledger']):
        xx={k:v for k,v in x.items() if k!='workflow_seconds'};yy={k:v for k,v in y.items() if k!='workflow_seconds'}
        if not equivalence.strict_equal(xx,yy):issues.append('ledger event '+str(x['sequence']))
        rows=data.make_rows(x['seed']);task=data.make_task(x['q'],rows,x['seed']*100+x['q'])
        expected=data.correct_answer(rows,task) if x['kind']=='reference' else data.independent_execute(rows,task,x['m'],x['z'])
        if expected!=x['answer']:issues.append('independent calibration answer')
        if x['kind']=='label' and x['failure']!=int(expected!=data.correct_answer(rows,task)):issues.append('independent calibration label')
        count+=1
    for x,y in zip(result['selection'],rebuilt['selection']):
        if {k:v for k,v in x.items() if k not in ('selection_seconds','score')}!={k:v for k,v in y.items() if k not in ('selection_seconds','score')}:issues.append('acquisition order')
        if type(x['score']) is not type(y['score']):issues.append('acquisition score type')
        elif x['score'] is not None and (type(x['score']) is not float or not math.isfinite(x['score']) or x['score']<0 or abs(x['score']-y['score'])>1e-12):issues.append('acquisition diagnostic score')
    if len(result['selection'])!=len(rebuilt['selection']):issues.append('selection count')
    for k,s in rebuilt['checkpoints'].items():
        old=result['checkpoints'].get(k,{})
        for fld in ['observed','table','model_fingerprint','selected_cells','training_seeds','oracle_event_count','selection_event_count','label_budget']:
            if not equivalence.strict_equal(old.get(fld),s.get(fld)):issues.append('checkpoint '+k+':'+fld)
        for fld in ['label_executions','reference_executions','total_workflows','tool_calls']:
            if not equivalence.strict_equal(old.get('cost',{}).get(fld),s['cost'][fld]):issues.append('checkpoint cost '+k+':'+fld)
    if result['total_physical_workflows']!=len(result['ledger']):issues.append('physical cost/event mismatch')
    return issues,count,rebuilt

def csv_write(path,rows):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    if not rows:raise ValueError('no rows')
    with path.open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)

def summaries(task_rows,p,models):
    grouped=defaultdict(list);stream=defaultdict(list)
    for r in task_rows:
        grouped[(r['condition'],r['menu'],r['method'])].append(r)
        stream[(r['stream'],r['menu'],r['method'])].append(r)
    out=[]
    for (cond,menu,method),rs in sorted(grouped.items()):
        failures=sum(x['failure'] for x in rs);credits=sum(x['credits'] for x in rs);nstreams=len({x['stream'] for x in rs})
        costs=[models[(panel,method)]['cost']['total_workflows'] for panel in range(p['calibration_panels'])]
        out.append({'condition':cond,'menu':menu,'method':method,'task_records':len(rs),'base_streams':nstreams,
                    'successes':len(rs)-failures,'failures':failures,'probe_credits':credits,'task_cost_units':cost_units(failures,credits),
                    'runtime_j_total':cost_units(failures,credits)/20,'runtime_j_per_episode':cost_units(failures,credits)/(20*nstreams),
                    'standalone_calibration_workflows_per_panel':sum(costs)/len(costs)})
    perstream={k:cost_units(sum(x['failure'] for x in xs),sum(x['credits'] for x in xs)) for k,xs in stream.items()}
    return out,perstream

def paired_stats(p,cases,perstream):
    rng=np.random.default_rng(p['statistics']['resample_seed']);B=p['statistics']['bootstrap_repetitions'];out=[]
    pairs=[('full_joint','single_only'),('decision_16','single_only'),('decision_32','single_only'),
           ('decision_16','random_16'),('decision_32','random_32'),('decision_16','occupancy_16'),
           ('decision_32','occupancy_32'),('decision_16','full_joint'),('decision_32','full_joint')]
    for cond in p['conditions']:
        ids=[[c['id'] for c in cases if c['condition']==cond['name'] and c['panel']==panel] for panel in range(p['calibration_panels'])]
        for menu in p['menus']:
            for left,right in pairs:
                arrays=[np.array([perstream[(i,menu,left)]-perstream[(i,menu,right)] for i in panel],dtype=float)/20 for panel in ids]
                boot=np.zeros(B)
                for x in arrays:boot+=x[rng.integers(0,len(x),size=(B,len(x)))].mean(axis=1)/len(arrays)
                x=np.concatenate(arrays);lo,hi=np.quantile(boot,[.025,.975])
                out.append({'condition':cond['name'],'menu':menu,'left':left,'right':right,'mean_runtime_j_delta':float(x.mean()),
                   'ci_low':float(lo),'ci_high':float(hi),'left_better_streams':int((x<0).sum()),'tied_streams':int((x==0).sum()),
                   'left_worse_streams':int((x>0).sum()),'training_panels':len(arrays),'evaluation_streams':len(x),
                   'inference':'descriptive_conditional_on_four_fitted_panels_not_confirmatory'})
    # Strict paired menu comparison, same task, data, modes, and method.
    for cond in p['conditions']:
        ids=[[c['id'] for c in cases if c['condition']==cond['name'] and c['panel']==panel] for panel in range(p['calibration_panels'])]
        for method in p['methods']:
            arrays=[np.array([perstream[(i,'shared',method)]-perstream[(i,'single',method)] for i in panel],dtype=float)/20 for panel in ids]
            boot=np.zeros(B)
            for x in arrays:boot+=x[rng.integers(0,len(x),size=(B,len(x)))].mean(axis=1)/len(arrays)
            x=np.concatenate(arrays);lo,hi=np.quantile(boot,[.025,.975])
            out.append({'condition':cond['name'],'menu':'shared_minus_single','left':method,'right':method,'mean_runtime_j_delta':float(x.mean()),
             'ci_low':float(lo),'ci_high':float(hi),'left_better_streams':int((x<0).sum()),'tied_streams':int((x==0).sum()),
             'left_worse_streams':int((x>0).sum()),'training_panels':len(arrays),'evaluation_streams':len(x),
             'inference':'descriptive_conditional_on_four_fitted_panels_not_confirmatory'})
    return out

def audit(root):
    root=Path(root);r=study.run_dir(root);p=study.get_protocol(root);out=r/'audit';out.mkdir(parents=True,exist_ok=True)
    validate_cost_protocol(p)
    issues=[];source=storage.verify_source(root)
    if not source['pass']:issues+=source['issues']
    status=storage.read(r/'status.json') if (r/'status.json').exists() else {'state':'missing'}
    if status['state']!='completed':
        report={'mechanical_pass':False,'status':status,'issues':issues+['incomplete run'],'scientific_gate':'PENDING_RESEARCHER_REVIEW','new_model_calls':0}
        storage.replace_local(out/'report.json',report);return report
    issues+=layout_issues(r,p)
    manifest=storage.read(r/'manifest.json')
    if manifest['protocol']!=p or manifest['source_manifest_sha256']!=source.get('manifest_sha256'):issues.append('run fingerprint/source')
    for name,hs in manifest['source_hashes'].items():
        f=r/'code_snapshot'/name
        if not f.is_file() or storage.sha(f.read_bytes())!=hs:issues.append('snapshot '+name)
    cases=storage.read(r/'private/cases.json')
    if cases!=data.cases(p):issues.append('private task tapes mismatch')
    if storage.read(r/'private/split_ids.json')!=data.split_ids(p):issues.append('split mismatch')
    design=selection.Design(p);models={};cal_count=0;calrows=[];physical=0
    for panel in range(p['calibration_panels']):
        print(f'Audit calibration panel {panel+1}/{p["calibration_panels"]}',flush=True)
        for name in study.LEARNERS:
            result=storage.read(r/f'calibration/panel_{panel:03d}_{name}.json')
            errs,count,rebuilt=check_ledger(result,panel,p,design);issues +=[f'panel{panel}/{name}: '+e for e in errs];cal_count+=count
            physical+=result['total_physical_workflows']
        for method in p['methods']:
            s=storage.read(r/f'models/panel_{panel:03d}_{method}.json');models[(panel,method)]=s
            if s['cost']['total_workflows']!=expected_model_workflows(method,p['calibration_catalogs_per_panel']):issues.append('model cost')
            if method in ('any_exact','never'):
                if not equivalence.strict_equal(s,study.zero_model(method,panel)):issues.append('zero model')
            else:
                learner='single' if method=='single_only' else 'full' if method=='full_joint' else method.rsplit('_',1)[0]
                k='0' if learner=='single' else '100' if learner=='full' else method.rsplit('_',1)[1]
                cp=storage.read(r/f'calibration/panel_{panel:03d}_{learner}.json')['checkpoints'][k]
                if not equivalence.strict_equal(s['observed'],cp['observed']) or s['model_fingerprint']!=cp['model_fingerprint'] or not equivalence.strict_equal(s['table'],a.expand_table(a.from_snapshot(s)).tolist()):issues.append('model/checkpoint binding')
                if s['model_fingerprint']!=data.digest({'observed':s['observed'],'training_seeds':s['training_seeds']}):issues.append('model fingerprint from evidence')
            calrows.append({'panel':panel,'method':method,'label_executions':s['cost']['label_executions'],
               'reference_executions':s['cost']['reference_executions'],'total_workflows':s['cost']['total_workflows'],
               'selector_seconds':s['selector_seconds'],'initial_fit_seconds':s['initial_fit_seconds'],
               'acquisition_elapsed_seconds':s['acquisition_elapsed_seconds'],'design_build_seconds':s['design_build_seconds'],
               'training_cost_scope':'standalone_cost; do_not_sum_nested16_and32_as_actual_runs'})
    rows=[];entries={};max_delta=0.;ref_issues=[];ref_path=root/'reference/science.json'
    ref=storage.read(ref_path) if ref_path.exists() else None
    for panel in range(p['calibration_panels']):
        print(f'Audit frozen trajectories panel {panel+1}/{p["calibration_panels"]}',flush=True)
        for menu in p['menus']:
            for method in p['methods']:
                s=models[(panel,method)];sol=runtime.planner(p,menu,s,method)
                for case in [c for c in cases if c['panel']==panel]:
                    name=f'{case["id"]:03d}_{menu}_{method}.json';tr=storage.read(r/'trajectories'/name)
                    issues+=check_task_trace(tr,case,p)
                    rebuilt=runtime.run_one(case,p,menu,method,s,sol);cmp=equivalence.compare(tr,rebuilt)
                    if not cmp['pass']:issues.append('trajectory '+name+':'+str(cmp['issues'][:3]))
                    max_delta=max(max_delta,cmp['maximum_probability_delta']);entries[name]=equivalence.reference(tr)
                    if ref:
                        if name not in ref['trajectories']:ref_issues.append('missing reference '+name)
                        else:
                            c=equivalence.check_reference(ref['trajectories'][name],tr)
                            if not c['pass']:ref_issues.append(name+':'+str(c['issues']))
                            max_delta=max(max_delta,c['maximum_probability_delta'])
                    for rec,e in zip(tr['records'],case['steps']):
                        fail=int(rec['answer']!=data.correct_answer(case['rows'],e['task']))
                        rows.append({'stream':case['id'],'panel':panel,'condition':case['condition'],'menu':menu,'method':method,
                         'step':rec['step'],'failure':fail,'credits':rec['credits'],'task_cost_units':cost_units(fail,rec['credits']),
                         'memory_before':rec['memory_before'],'memory_after':rec['memory_after'],'true_mode':e['true_mode'],
                         'predicted_failure_own_kernel':rec['predicted_task_error_after_receipts'],
                         'planning_seconds':rec['planning_seconds'],'probe_seconds':rec['probe_seconds'],'tool_seconds':rec['tool_seconds']})
                sol.clear()
    if ref and set(entries)!=set(ref['trajectories']):ref_issues.append('reference trajectory set')
    issues+=ref_issues
    summary,perstream=summaries(rows,p,models);paired=paired_stats(p,cases,perstream);frontier=[]
    for row in summary:
        for N in p['calibration_cost_sensitivity']['deployment_episodes']:
            for price in p['calibration_cost_sensitivity']['price_per_workflow']:
                frontier.append({**{k:row[k] for k in ['condition','menu','method']},'deployment_episodes':N,
                  'price_per_calibration_workflow':price,'runtime_j_per_episode':row['runtime_j_per_episode'],
                  'startup_proxy_per_episode':.3,'standalone_calibration_workflows':row['standalone_calibration_workflows_per_panel'],
                  'amortized_proxy_per_episode':amortized(row['runtime_j_per_episode'],row['standalone_calibration_workflows_per_panel'],N,price),
                  'scope':'hypothetical_cost_sensitivity_not_currency_or_measured_deployment'})
    for f,rs in [('per_task.csv',rows),('summary.csv',summary),('paired.csv',paired),('cost_frontier.csv',frontier),('calibration_costs.csv',calrows)]:csv_write(out/f,rs)
    reference_obj={'schema':'typed_discrete_hash_plus_scoped_prediction_v1','protocol_sha256':data.digest(p),'trajectories':entries}
    storage.replace_local(out/'reference_validation.json',reference_obj)
    report={'mechanical_pass':not issues,'issues':issues,'source':source,'calibration_workflow_events_checked':cal_count,
            'physical_calibration_workflows':physical,'runtime_task_records':len(rows),'trajectories':len(entries),
            'base_streams':len(cases),'training_panels':p['calibration_panels'],'scoped_probability_atol':1e-14,
            'scoped_probability_rtol':0,'max_probability_delta':max_delta,'reference_present':ref is not None,
            'reference_science_match':not ref_issues if ref else None,'hard_budget_violations':[x for x in issues if 'budget' in x],
            'new_llm_api_calls':0,'scientific_gate':'PENDING_RESEARCHER_REVIEW',
            'limits':'Conditional development experiment; same catalogs/API grammar; no public benchmark or general optimum proof.'}
    storage.replace_local(out/'report.json',report);return report


def validate_cost_protocol(p):
    if type(p['credit_price']) is not float or p['credit_price']!=0.05:
        raise ValueError('integer task-cost units bind exactly credit_price=0.05')

def layout_issues(r,p):
    r=Path(r);n=p['calibration_panels']*len(p['conditions'])*p['streams_per_condition']
    expected={
      'trajectories':{f'{i:03d}_{menu}_{method}.json' for i in range(n) for menu in p['menus'] for method in p['methods']},
      'models':{f'panel_{i:03d}_{method}.json' for i in range(p['calibration_panels']) for method in p['methods']},
      'calibration':{f'panel_{i:03d}_{name}.json' for i in range(p['calibration_panels']) for name in study.LEARNERS}}
    issues=[]
    for folder,names in expected.items():
        actual={f.name for f in (r/folder).glob('*.json')}
        if names-actual:issues.append(f'{folder}: missing {len(names-actual)} files')
        if actual-names:issues.append(f'{folder}: unexpected {len(actual-names)} files')
    return issues
