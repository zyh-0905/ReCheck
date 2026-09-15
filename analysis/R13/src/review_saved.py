"""Review local scripted records; optional unchanged upstream regrading."""
import json
from pathlib import Path
from saved_check import check

def run(inputs,out,native=False):
    out=Path(out);out.mkdir(parents=True,exist_ok=False)
    results=[]
    for p in sorted(Path(inputs).glob('*.json')):
        r=json.loads(p.read_text()); row=check(r)
        if native:
            import attrs
            from tool_sandbox.common.execution_context import ExecutionContext
            from tool_sandbox.common.tool_discovery import ToolBackend
            from tool_sandbox.scenarios.multiple_user_turn_scenarios import named_multiple_user_turn_scenarios
            if r['final_snapshot']['interactive_console'] is not None:raise ValueError('No serialized console allowed')
            context=ExecutionContext.from_dict(r['final_snapshot'])
            s=named_multiple_user_turn_scenarios(ToolBackend.DEFAULT)[r['scenario']]
            grade=attrs.asdict(s.evaluation.evaluate(context,max_turn_count=s.max_messages))
            if json.loads(json.dumps(grade)) != r['official_evaluation']:raise ValueError('Native regrade mismatch')
            row['native_regrade_equal']=True
        results.append(row)
    (out/'records.json').write_text(json.dumps(results,ensure_ascii=False,sort_keys=True,indent=2)+'\n')
    summary={'records':len(results),'snapshot_checks':True,'native_regrades':len(results) if native else 0,'new_model_calls':0,'not_new_independent_samples':True}
    (out/'summary.json').write_text(json.dumps(summary,sort_keys=True,indent=2)+'\n')
    print(json.dumps(summary));return summary
