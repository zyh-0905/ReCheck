"""Offline-only evaluator and allowlisted exporter. Never imported by a study runner."""
from __future__ import annotations
import csv, hashlib, json, math, zipfile
from collections import defaultdict
from pathlib import Path
import numpy as np
from .common import read_json,write_json,digest,is_number,utcnow


def reference_artifact(rule,sources):
    value=rule['base']+rule['multiplier']*sources[rule['source']]
    return {'metric':value,'flag':'high' if value>=rule['threshold'] else 'low'}


def artifact_correct(actual,expected):
    return isinstance(actual,dict) and set(actual)=={'metric','flag'} and is_number(actual.get('metric')) and abs(actual['metric']-expected['metric'])<=1e-8 and actual.get('flag')==expected['flag']


def recheck_correct(row,case):
    if not row['plan_schema_valid']:return False
    ans=row.get('answer');task=case['tasks'][row['step']];q=task['type']
    if not isinstance(ans,dict) or set(ans)!={'total','count'}:return False
    if q in (0,2):
        if not is_number(ans['total']) or abs(ans['total']-sum(case['cents'])/100)>1e-6:return False
    elif ans['total'] is not None:return False
    if q in (1,2,3):
        expected=len(case['cents']) if q==3 else sum(i<=task['cutoff'] for i in range(len(case['cents'])))
        if not is_number(ans['count']) or ans['count']!=expected:return False
    elif ans['count'] is not None:return False
    return True


def _csv(path,rows):
    if not rows:return
    keys=list(dict.fromkeys(k for row in rows for k in row))
    with Path(path).open('w',newline='',encoding='utf-8-sig') as f:
        wr=csv.DictWriter(f,keys);wr.writeheader();wr.writerows(rows)


def summarize(run_dir):
    root=Path(run_dir);manifest=read_json(root/'manifest.json');study=manifest['study'];spec=manifest['spec']
    attempt_starts=[read_json(p) for p in sorted((root/'attempts').glob('*_start.json'))]
    attempt_results=[read_json(p) for p in sorted((root/'attempts').glob('*_result.json'))]
    completions=[read_json(p) for p in sorted((root/'calls').glob('*.json'))]
    by_id={x['logical_id']:x for x in completions}
    costs=defaultdict(list);latencies=defaultdict(float)
    for result in attempt_results:
        costs[result['logical_id']].append(result.get('estimated_cost'))
        latencies[result['logical_id']]+=result.get('latency_seconds',0.)
    def resource(ids):
        items=[v for k in ids for v in costs[k]]
        return {'llm_calls':len(ids),'llm_attempts':sum(len(costs[k]) for k in ids),
                'llm_latency_seconds':sum(latencies[k] for k in ids),
                'estimated_cost':sum(items) if all(x is not None for x in items) else None,
                'prompt_tokens':sum((by_id.get(k,{}).get('response',{}).get('usage') or {}).get('prompt_tokens',0) or 0 for k in ids),
                'completion_tokens':sum((by_id.get(k,{}).get('response',{}).get('usage') or {}).get('completion_tokens',0) or 0 for k in ids),
                'missing_usage_calls':sum(not by_id.get(k,{}).get('response',{}).get('usage') for k in ids)}
    rows=[]
    if study=='recheck':
        cases={x['stream']:x for x in read_json(root/'private'/'recheck_cases.json')}
        for p in sorted((root/'records').glob('rc_*.json')):
            r=read_json(p);rows.append({'unit':r['stream'],'step':r['step'],'method':r['method'],
                'regime':cases[r['stream']]['regime'],'correct':int(recheck_correct(r,cases[r['stream']])),
                'plan_valid':int(r['plan_schema_valid']),'answer_json_error':int(r['answer_json_error'] is not None),
                'probe_count':r['probe_count'],'model_probe_cost_not_currency':r['model_probe_cost'],
                'planning_seconds':r['planning_seconds'],'local_tool_seconds':r['probe_seconds']+r['tool_seconds'],**resource(r['logical_calls'])})
        expected=spec['streams']*spec['steps']*len(spec['methods'])
    elif study=='repairlens_readiness':
        cases={x['case']:x for x in read_json(root/'private'/'readiness_cases.json')}
        for p in sorted((root/'records').glob('rl_*.json')):
            r=read_json(p);c=cases[r['case']]
            gold_old={s['id']:reference_artifact(rule,c['old_sources']) for s,rule in zip(c['specs'],c['evaluator_rules'])}
            gold_new={s['id']:reference_artifact(rule,c['new_sources']) for s,rule in zip(c['specs'],c['evaluator_rules'])}
            initial_ok=all(artifact_correct(r['old_artifacts'].get(k),v) for k,v in gold_old.items())
            stale_wrong=not all(artifact_correct(r['old_artifacts'].get(k),v) for k,v in gold_new.items())
            final_ok=all(artifact_correct(r['final_artifacts'].get(k),v) for k,v in gold_new.items()) and r['selection_error'] is None
            rows.append({'unit':r['case'],'method':r['method'],'correct':int(final_ok),
                'initial_correct':int(initial_ok),'old_state_invalid_after_revision':int(stale_wrong),
                'repair_eligible':int(initial_ok and stale_wrong),'selected_count':len(r['selected_artifacts']),
                'selection_invalid':int(r['selection_error'] is not None),**resource(r['logical_calls'])})
        expected=spec['cases']*len(spec['methods'])
    else:expected=1
    groups=defaultdict(list)
    for r in rows:groups[r['method']].append(r)
    methods=[]
    for name,rs in sorted(groups.items()):
        methods.append({'method':name,'completed_records':len(rs),'independent_units':len({x['unit'] for x in rs}),
            'success_rate':sum(x['correct'] for x in rs)/len(rs),
            'llm_calls_excluding_shared_prefix':sum(x['llm_calls'] for x in rs),
            'llm_attempts_excluding_shared_prefix':sum(x['llm_attempts'] for x in rs),
            'llm_latency_seconds_excluding_shared_prefix':sum(x['llm_latency_seconds'] for x in rs),
            'estimated_cost_excluding_shared_prefix':sum(x['estimated_cost'] for x in rs) if all(x['estimated_cost'] is not None for x in rs) else None})
    prefix_calls=[c['logical_id'] for c in completions if c.get('metadata',{}).get('phase')=='shared_prefix']
    snapshot_issues=[]
    for rel,sha in manifest['source_hashes'].items():
        p=root/'code_snapshot'/rel
        if not p.exists() or hashlib.sha256(p.read_bytes()).hexdigest()!=sha:snapshot_issues.append(rel)
    returned_models=sorted({str(x.get('response',{}).get('model')) for x in completions})
    all_cost=[r.get('estimated_cost') for r in attempt_results]
    summary={'study':study,'evidence_label':manifest['evidence_label'],'phase':spec['phase'],
             'expected_records':expected,'completed_records':len(rows) if study!='smoke' else len(completions),
             'request_attempts':len(attempt_starts),'completed_logical_calls':len(completions),
             'request_errors':sum(r['status']!='ok' for r in attempt_results),
             'uncertain_interrupted_attempts':len(attempt_starts)-len(attempt_results),
             'unknown_cost_attempts':sum(v is None for v in all_cost)+len(attempt_starts)-len(attempt_results),
             'known_estimated_spend':sum(x for x in all_cost if x is not None),
             'currency':manifest['config']['prices']['currency'],'returned_model_ids':returned_models,
             'source_snapshot_mismatches':snapshot_issues,'methods':methods,
             'shared_prefix_resources':resource(prefix_calls),
             'limitations':['Pilot only; no confirmatory p values or manuscript updates.',
                 'Token totals exclude missing usage; missing_usage_calls must be inspected.',
                 'Provider invoice overrides all local list-price estimates.',
                 'Shared prefix paid once in this run; include its cost in each strategy for deployment comparisons, but do not sum those attributed costs into the actual invoice.',
                 'Synthetic task generation; no natural-failure or public-benchmark claim.']}
    if study=='recheck':summary['initial_calibration_probes_actual']=2*spec['streams']
    write_json(root/'summary.json',summary);_csv(root/'per_task.csv',rows);_csv(root/'method_summary.csv',methods)
    text=['# Pilot results','',f"Study: {study}",f"Evidence label: {manifest['evidence_label']}",'',
          '**Development pilot only. Do not use these results as final paper evidence.**','',
          f"Completed records: {summary['completed_records']}/{expected}; HTTP attempts: {len(attempt_starts)}.",
          '','```json',json.dumps(summary,ensure_ascii=False,indent=2),'```']
    (root/'SUMMARY.md').write_text('\n'.join(text)+'\n',encoding='utf-8')
    print(json.dumps({'study':study,'records':f"{summary['completed_records']}/{expected}",'methods':methods},ensure_ascii=False,indent=2))
    return summary


ALLOWED_TOP={'manifest.json','status.json','summary.json','SUMMARY.md','per_task.csv','method_summary.csv','controller_metadata.json','smoke_result.json'}
ALLOWED_DIR={'calls','attempts','records','prefixes','private','code_snapshot'}


def export(run_dir,out,secret=''):
    root=Path(run_dir).resolve();out=Path(out).resolve()
    if root==out or root in out.parents:raise ValueError('Write upload ZIP outside the run directory')
    manifest=read_json(root/'manifest.json')
    files=[]
    for p in sorted(root.rglob('*')):
        if not p.is_file() or p.is_symlink():continue
        rel=p.relative_to(root)
        if rel.as_posix() not in ALLOWED_TOP and rel.parts[0] not in ALLOWED_DIR:continue
        if any(x.startswith('.') for x in rel.parts) or p.suffix in ('.tmp','.pyc','.key','.pem'):continue
        # A shared secret should never be present; refuse rather than silently alter evidence.
        data=p.read_bytes()
        if secret and secret.encode() in data:raise ValueError('Known credential found in export allowlist; export blocked.')
        if rel.parts[0]=='code_snapshot':
            inner=Path(*rel.parts[1:]).as_posix()
            if inner not in manifest['source_hashes']:continue
        files.append((p,rel.as_posix()))
    out.parent.mkdir(parents=True,exist_ok=True)
    checks={r:hashlib.sha256(p.read_bytes()).hexdigest() for p,r in files}
    with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as z:
        for p,rel in files:z.write(p,rel)
        z.writestr('EXPORT_MANIFEST.json',json.dumps({'created_utc':utcnow(),'run_fingerprint':manifest['fingerprint'],
                    'evidence_label':manifest['evidence_label'],'sha256':checks},indent=2))
    print('Upload bundle:',out.name,'| files:',len(files),'| bytes:',out.stat().st_size)
    return out
