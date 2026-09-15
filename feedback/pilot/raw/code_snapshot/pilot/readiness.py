"""RepairLens prerequisite ONLY: fixed-prefix real-LLM artifact repair readiness.

This does NOT run RepairLens's finite-model solver or test its claimed advantage.
Comparators are full regeneration, LLM-selected patching, and no repair.
Cases are generated source revisions, not naturally collected agent failures.
"""
from __future__ import annotations
import copy, json, time
from pathlib import Path
import numpy as np
from .common import write_json,read_json,digest,strict_json_object,is_number
from .recheck import ask

ARTIFACT_IDS=('cost_note','capacity_note','schedule_note')
METHODS=('full_regeneration','llm_selected_patch','keep_stale')


def protocol(cases=4):
    return {'phase':'replay_readiness_only','cases':cases,'seed_start':920001,
            'methods':list(METHODS),'max_logical_calls':cases*10,
            'prompt_version':'repair-readiness-0.1',
            'not_a_repairlens_algorithm_test':True,
            'limitations':['synthetic source revisions','explicit public computation rules','no learned dependency graph',
                           'no external benchmark','derived checks are not independent follow-up tasks']}


def make_cases(count):
    cases=[]
    for i in range(count):
        rng=np.random.default_rng(920001+i);mask=(1,3,7,0)[i%4]
        old_rate=int(rng.integers(3,8));new_rate=old_rate+int(rng.integers(2,5))
        fixed=int(rng.integers(2,8));specs=[];private=[]
        for j,name in enumerate(ARTIFACT_IDS):
            source='tariff' if mask&(1<<j) else 'archive_allowance'
            multiplier=int(rng.integers(2,8));base=int(rng.integers(1,12));threshold=int(rng.integers(15,60))
            specs.append({'id':name,'rule':f'Compute metric as {base} plus {multiplier} times the value of {source}. Set flag to high when metric is at least {threshold}, otherwise low.',
                          'output_contract':{'metric':'number','flag':'high or low'}})
            private.append({'source':source,'multiplier':multiplier,'base':base,'threshold':threshold})
        cases.append({'case':i,'specs':specs,'old_sources':{'tariff':old_rate,'archive_allowance':fixed},
                      'new_sources':{'tariff':new_rate,'archive_allowance':fixed},
                      'correction':f'The authoritative tariff changed from {old_rate} to {new_rate}. The archive allowance is unchanged.',
                      'partial_provenance':{ARTIFACT_IDS[j]:(['tariff'] if j==2 and mask&(1<<j) else []) for j in range(3)},
                      'evaluator_rules':private})
    return cases


def artifact_valid(x):
    return isinstance(x,dict) and set(x)=={'metric','flag'} and is_number(x['metric']) and x['flag'] in ('high','low')


def selected_ids(parsed):
    if not isinstance(parsed,dict) or set(parsed)!={'artifact_ids'}:return None
    ids=parsed['artifact_ids']
    if not isinstance(ids,list) or any(not isinstance(x,str) or x not in ARTIFACT_IDS for x in ids) or len(set(ids))!=len(ids):return None
    return ids


def worker(client,cfg,logical_id,spec,sources,meta):
    obj,error,record=ask(client,cfg,logical_id,'artifact',{
        'specification':spec,'current_sources':sources,
        'instructions':'Recompute this artifact from the current sources. Return exactly {"metric":number,"flag":"high" or "low"}. No other fields.'},meta)
    return obj,error,record


def run(client,cfg,run_dir,spec):
    root=Path(run_dir);cases=make_cases(spec['cases']);write_json(root/'private'/'readiness_cases.json',cases)
    for case in cases:
        i=case['case'];old={};initial_calls=[]
        for artifact in case['specs']:
            name=artifact['id'];obj,error,rec=worker(client,cfg,f'rl/{i}/shared_initial/{name}',artifact,case['old_sources'],
                    {'study':'repairlens_readiness','case':i,'phase':'shared_prefix','artifact':name})
            old[name]=obj;initial_calls.append(rec['logical_id'])
        prefix={'old_artifacts':old,'old_sources':case['old_sources'],'initial_calls':initial_calls,
                'partial_provenance':case['partial_provenance']}
        prefix_hash=digest(prefix);write_json(root/'prefixes'/f'rl_{i}.json',prefix)
        shift=i%len(METHODS);order=METHODS[shift:]+METHODS[:shift]
        for method in order:
            path=root/'records'/f'rl_{i:03d}_{method}.json'
            if path.exists():continue
            state=copy.deepcopy(old);calls=[];selection_error=None
            if method=='full_regeneration':chosen=list(ARTIFACT_IDS)
            elif method=='keep_stale':chosen=[]
            else:
                parsed,error,rec=ask(client,cfg,f'rl/{i}/{method}/select','select_repair',{
                    'specifications':case['specs'],'old_sources':case['old_sources'],'current_sources':case['new_sources'],
                    'correction':case['correction'],'old_artifacts':old,'partial_provenance':case['partial_provenance'],
                    'instructions':'Select artifacts that require recomputation after this correction, or that already violate their output contract. Missing provenance is not proof of no dependency. Return {"artifact_ids":[zero or more IDs]}. Do not compute replacement artifacts in this call.'},
                    {'study':'repairlens_readiness','case':i,'method':method,'phase':'selection'})
                calls.append(rec['logical_id']);chosen=selected_ids(parsed)
                if chosen is None:selection_error=error or 'INVALID_SELECTION_SCHEMA';chosen=[]
            for artifact in case['specs']:
                name=artifact['id']
                if name in chosen:
                    obj,error,rec=worker(client,cfg,f'rl/{i}/{method}/repair/{name}',artifact,case['new_sources'],
                        {'study':'repairlens_readiness','case':i,'method':method,'phase':'repair','artifact':name})
                    state[name]=obj;calls.append(rec['logical_id'])
            write_json(path,{'study':'repairlens_readiness','case':i,'method':method,'prefix_sha256':prefix_hash,
                    'selected_artifacts':chosen,'selection_error':selection_error,'old_artifacts':old,
                    'final_artifacts':state,'logical_calls':calls,
                    'disclosure':'Fixed-prefix generated revision pilot; not RepairLens algorithm, not natural failure recovery.'})
