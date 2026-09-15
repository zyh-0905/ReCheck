"""Independent outcome/budget audit and descriptive paired statistics.
Never executes network calls or changes primary trajectory files.
"""
from pathlib import Path
import json,time
import numpy as np
from . import data,evaluator,storage,runtime,calibration
from .model import posterior
from .study import csv_write
from vendor.r4 import environment

def score_trajectory(record,case,p):
    errs=[];out=[];mem=case['initial_mode'];ages=(0,0,0);bank=p['budget']
    for r,e in zip(record['records'],case['steps']):
        b0=bank;cost=0;cover=set();packets={x['id']:x for x in runtime.packet_list(record['menu'])}
        if len(r['packets'])!=len(set(r['packets'])):errs.append('duplicate packet')
        for name in r['packets']:
            if name not in packets:errs.append('bad packet');continue
            pp=packets[name];cost+=pp['cost'];cover.update(pp['cover'])
        if cost>p['step_cap'] or cost>bank:errs.append('budget exceeded')
        for j in cover:mem=(mem&~(1<<j))|(e['true_mode']&(1<<j))
        bank-=cost
        expected=evaluator.correct_answer(case['rows'],e['task'])
        actual=evaluator.independently_execute(case['rows'],e['task'],mem,e['true_mode'])
        if actual!=r['answer']:errs.append('independent execution mismatch')
        if r['memory_after']!=mem or r['budget_before']!=b0 or r['budget_after']!=bank or r['credits']!=cost:
            errs.append('memory/quota mismatch')
        stale=[j for j in data.RELEVANT[e['q']] if (mem^e['true_mode'])&(1<<j)]
        failure=int(actual!=expected)
        out.append({'stream':case['id'],'condition':case['condition'],'menu':record['menu'],'method':record['method'],
          'step':r['step'],'q':e['q'],'failure':failure,'success':1-failure,'credits':cost,'budget_after':bank,
          'task_cost':failure+p['credit_price']*cost,'semantic_mismatches':len(stale),
          'stale_but_correct':int(bool(stale) and not failure),'fresh_but_wrong':int(not stale and failure),
          'page_error':int(actual.get('error')=='PAGE_BEFORE_FIRST'),
          'predicted_failure':r['predicted_task_error_after_receipts'],
          'planning_seconds':r['planning_seconds'],'probe_seconds':r['probe_seconds'],'tool_seconds':r['tool_seconds']})
    if len(record['records'])!=len(case['steps']):errs.append('missing step')
    return out,errs

def aggregate(rows):
    groups={}
    for r in rows:
        k=tuple(r[x] for x in ('condition','menu','method'))
        if k not in groups:
            groups[k]={'condition':k[0],'menu':k[1],'method':k[2],'tasks':0,'successes':0,'failures':0,
                       'credits':0,'task_cost':0.,'semantic_mismatches':0,'stale_but_correct':0,'brier_sum':0.}
        g=groups[k];g['tasks']+=1;g['successes']+=r['success'];g['failures']+=r['failure']
        for name in ('credits','task_cost','semantic_mismatches','stale_but_correct'):g[name]+=r[name]
        g['brier_sum']+=(r['predicted_failure']-r['failure'])**2
    for g in groups.values():
        g['success_rate']=g['successes']/g['tasks'];g['mean_task_cost']=g['task_cost']/g['tasks']
        g['mean_brier']=g.pop('brier_sum')/g['tasks']
    return [groups[k] for k in sorted(groups)]

def paired(rows,p):
    by={}
    for r in rows:
        key=(r['condition'],r['stream'],r['menu'],r['method'])
        by[key]=by.get(key,0.)+r['task_cost']
    rng=np.random.default_rng(p['statistics']['resample_seed']);rep=p['statistics']['bootstrap_repetitions'];out=[]
    comparisons=[('task_exact','any_exact'),('task_exact','semantic_exact'),('task_exact','single_effect_exact'),
                 ('task_rollout2','task_exact'),('task_myopic','task_exact')]
    for c in p['conditions']:
        name=c['name'];sids=sorted(set(k[1] for k in by if k[0]==name))
        for menu in p['menus']:
            for a,b in comparisons:
                vals=np.array([by[(name,i,menu,a)]-by[(name,i,menu,b)] for i in sids])
                boot=vals[rng.integers(0,len(vals),size=(rep,len(vals)))].mean(axis=1)
                lo,hi=np.quantile(boot,[.025,.975])
                out.append({'condition':name,'menu':menu,'contrast':a+' minus '+b,
                   'independent_streams':len(vals),'mean_stream_cost_difference':float(vals.mean()),
                   'ci_low':float(lo),'ci_high':float(hi),'status':'DESCRIPTIVE_NOT_CONFIRMATORY'})
        for method in p['methods']:
            vals=np.array([by[(name,i,'shared',method)]-by[(name,i,'single',method)] for i in sids])
            boot=vals[rng.integers(0,len(vals),size=(rep,len(vals)))].mean(axis=1);lo,hi=np.quantile(boot,[.025,.975])
            out.append({'condition':name,'menu':'paired_shared_minus_single','contrast':method,
               'independent_streams':len(vals),'mean_stream_cost_difference':float(vals.mean()),
               'ci_low':float(lo),'ci_high':float(hi),'status':'DESCRIPTIVE_NOT_CONFIRMATORY'})
    return out

def audit(root,replay=True):
    root=Path(root);out=root/'runs/R5_offline';p=data.load_protocol();issues=[]
    ck=storage.verify_source(root)
    if not ck['pass']:issues+=ck['issues']
    if not (out/'manifest.json').exists():raise ValueError('No prepared output to audit')
    m=storage.read(out/'manifest.json')
    if m['source_manifest_sha256']!=ck.get('manifest_sha256'):issues.append('source binding changed')
    src=storage.read(root/'SOURCE_MANIFEST.json')['files']
    for name,expected_sha in src.items():
        path=out/'code_snapshot'/name
        if not path.exists() or storage.sha(path.read_bytes())!=expected_sha:issues.append('snapshot missing/changed '+name)
    train=storage.read(out/'calibration/fitted.json')
    regenerated=calibration.fit(data.split_ids(p)['calibration'])
    if train!=regenerated:issues.append('calibration was changed or uses other data')
    val=storage.read(out/'private/validation.json')
    if val!=calibration.fit(data.split_ids(p)['validation']):issues.append('validation mismatch')
    cases=data.make_cases(p);case_map={x['id']:x for x in cases}
    if (out/'private/cases.json').exists() and storage.read(out/'private/cases.json')!=cases:issues.append('test cases changed')
    allrows=[];seen=set();replayed=0;scientific_hashes={}
    for menu in p['menus']:
        for method in p['methods']:
            solver=runtime.planner(method,p,menu,train) if replay else None
            for case in cases:
                f=out/'trajectories'/f"{case['id']:03d}_{menu}_{method}.json"
                if not f.exists():continue
                r=storage.read(f);seen.add(f.name)
                if r['case_sha256']!=storage.digest(case):issues.append(f.name+':case binding')
                rows,err=score_trajectory(r,case,p);allrows+=rows
                issues += [f.name+':'+e for e in err]
                if replay:
                    rr=runtime.run_one(case,p,menu,method,train,solver)
                    if runtime.science(rr)!=runtime.science(r):issues.append(f.name+':replay difference')
                    replayed+=len(r['records'])
                scientific_hashes[f.name]=storage.digest(runtime.science(r))
            if solver:solver.clear()
    expected=len(cases)*len(p['menus'])*len(p['methods'])
    actualfiles={f.name for f in (out/'trajectories').glob('*.json')} if (out/'trajectories').exists() else set()
    if actualfiles!=seen:issues.append('unrecognized trajectory files')
    complete=len(seen)==expected
    if not complete:issues.append(f'incomplete trajectories {len(seen)}/{expected}')
    tables=aggregate(allrows);stats=paired(allrows,p) if complete else []
    csv_write(out/'audit/per_task.csv',allrows);csv_write(out/'audit/summary.csv',tables)
    csv_write(out/'audit/paired.csv',stats)
    storage.replace_local(out/'audit/scientific_hashes.json',scientific_hashes)
    ref=root/'reference/scientific_hashes.json'
    refmatch=None
    if ref.exists():refmatch=storage.read(ref)==scientific_hashes
    if refmatch is False:issues.append('reference scientific outputs differ: preserve records for review')
    report={'mechanical_pass':not issues,'complete':complete,'issues':issues,'source':ck,'rows':len(allrows),
      'trajectories':len(seen),'expected_trajectories':expected,'replayed_task_records':replayed,
      'new_llm_calls':0,'rule_execution_only':True,'reference_science_match':refmatch,
      'scientific_gate':'PENDING_RESEARCHER_REVIEW','summary':tables,
      'calibration_only_learning':True,'validation_not_used_by_test_schedulers':True,
      'no_money_or_model_performance_claim':True}
    storage.replace_local(out/'audit/report.json',report)
    return report
