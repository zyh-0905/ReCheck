"""Re-score recorded snapshots with the unchanged original evaluator, offline."""
import json,copy,attrs,csv,datetime
from unittest.mock import patch
from pathlib import Path
from native_study import definitions
from tool_sandbox.common.execution_context import ExecutionContext,set_current_context
from evidence_check import check_record

def scenario_for_record(record):
    if record['scenario']!='modify_reminder_with_recency_latest':
        return copy.deepcopy({**definitions()['single'],**definitions()['multi']}[record['scenario']])
    # Only reconstruct the calendar input of the relative-date task for saved-
    # snapshot regrading. This does NOT alter tools or the native runs. The
    # original task/evaluator source bytes stay unchanged.
    from tool_sandbox.scenarios import multiple_tool_call_scenarios as module
    from tool_sandbox.common.tool_discovery import ToolBackend
    tomorrow=datetime.datetime.fromtimestamp(record['desired'])
    with patch.object(module,'get_tomorrow_datetime',return_value=tomorrow):
        return module.named_multiple_tool_call_scenarios(ToolBackend.DEFAULT)[record['scenario']]

def run(root,out):
    root=Path(root);out=Path(out);out.mkdir(parents=True,exist_ok=False)
    defs={**definitions()['single'],**definitions()['multi']};records=[]
    for cohort,dirname in [('settings','native_run1'),('exploratory_additional','supplement_run2')]:
        for path in sorted((root/'results'/dirname/'trajectories').glob('*.json')):
            data=json.loads(path.read_text());score=check_record(data)
            ctx=ExecutionContext.from_dict(data['final_snapshot']);set_current_context(ctx)
            scenario=scenario_for_record(data)
            original=attrs.asdict(scenario.evaluation.evaluate(ctx,max_turn_count=scenario.max_messages))
            normalized=json.loads(json.dumps(original,sort_keys=True))
            if normalized!=data['official_evaluation']:raise ValueError('Regrade mismatch: '+path.name)
            records.append({'cohort':cohort,**score,'source':path.relative_to(root).as_posix()})
    (out/'records.json').write_text(json.dumps(records,indent=2,sort_keys=True)+'\n')
    with (out/'records.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=records[0].keys());w.writeheader();w.writerows(records)
    summary={'records':len(records),'original_evaluation_exact_matches':len(records),'terminal_predicates_independently_checked':len(records),
        'original_full_scores':sum(r['official_similarity']==1 for r in records),
        'full_score_terminal_mismatch':sum(r['full_score_terminal_mismatch'] for r in records),
        'terminal_valid':sum(r['terminal_valid'] for r in records),
        'native_tool_calls':sum(r['native_tool_calls'] for r in records),'native_tool_errors':sum(r['native_tool_errors'] for r in records),
        'new_llm_calls':0,'contains_scripted_trajectories_only':True}
    (out/'summary.json').write_text(json.dumps(summary,indent=2,sort_keys=True)+'\n');print(json.dumps(summary,indent=2))
