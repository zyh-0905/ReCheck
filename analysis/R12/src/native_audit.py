"""Scripted metamorphic checks on five original ToolSandbox setting tasks.

No model or user simulator is instantiated. Actions use unchanged tools via the
original ExecutionEnvironment. Task state, policy, tool permissions, milestone
and minefield definitions are not changed. Scripts are not natural trajectories.
"""
from pathlib import Path
import copy, csv, json, sys, hashlib, attrs
from native_study import NativeSession, definitions
from contract import terminal_valid, classify, project
from tool_sandbox.common.execution_context import DatabaseNamespace as DB, RoleType
from tool_sandbox.tools import setting

CASES = {
 'cellular_off': ('cellular','set_cellular_service_status',False,'Cellular service is turned off'),
 'wifi_off': ('wifi','set_wifi_status',False,'Wifi is turned off'),
 'turn_on_wifi_low_battery_mode': ('wifi','set_wifi_status',True,'Wifi has been turned on.'),
 'turn_on_cellular_low_battery_mode': ('cellular','set_cellular_service_status',True,'Cellular service has been turned on.'),
 'turn_on_location_low_battery_mode': ('location_service','set_location_service_status',True,'Location service has been turned on.'),
}
VARIANTS=('correct','error_then_correct','correct_then_redundant_error','claim_only','achieve_then_revert','achieve_revert_repair')

def run_case(name, variant):
    if variant not in VARIANTS:raise ValueError(variant)
    scenario=copy.deepcopy({**definitions()['single'],**definitions()['multi']}[name])
    field,tool,desired,final_text=CASES[name]
    allowed={n:getattr(setting,n) for n in scenario.starting_context.tool_allow_list if hasattr(setting,n)}
    session=NativeSession(scenario,allowed)
    initial=session.rows(DB.SETTING)[0]
    initial_snapshot=session.snapshot()
    # Public original request, not private few-shot simulator instructions.
    user_requests=[row['content'] for row in session.ctx.get_database(DB.SANDBOX,get_all_history_snapshots=True).to_dicts()
                   if row['sender']==RoleType.USER and row['recipient']==RoleType.AGENT and row.get('visible_to') != [RoleType.USER]]
    states=[]
    def call(name,args):
        response=session.call(name,args)
        states.append({'event_index':len(states),'state':session.rows(DB.SETTING)[0]})
        return response
    def make_correct():
        if desired and session.rows(DB.SETTING)[0]['low_battery_mode']:
            assert call('set_low_battery_mode_status',{'on':False})['ok']
        assert call(tool,{'on':desired})['ok']
    if variant=='error_then_correct':
        # ON while low-battery is enabled -> PermissionError. OFF case: setting
        # the already-current value -> ValueError. Both are native no-write errors.
        error=call(tool,{'on':desired if desired else initial[field]})
        assert not error['ok']
        assert session.rows(DB.SETTING)[0]==initial
    if variant!='claim_only':make_correct()
    if variant=='correct_then_redundant_error':
        before=session.rows(DB.SETTING)[0]
        assert not call(tool,{'on':desired})['ok']
        assert before==session.rows(DB.SETTING)[0]
    if variant in ('achieve_then_revert','achieve_revert_repair'):
        assert call(tool,{'on':not desired})['ok']
    if variant=='achieve_revert_repair':assert call(tool,{'on':desired})['ok']
    session.finish(final_text)
    official=attrs.asdict(scenario.evaluation.evaluate(session.ctx,max_turn_count=scenario.max_messages))
    final_state=session.rows(DB.SETTING)[0]
    valid=terminal_valid(final_state,field,desired)
    return {
       'evidence_kind':'SCRIPTED_PUBLIC_TASK_EVALUATOR_DIAGNOSTIC_NOT_LLM',
       'scenario':name,'variant':variant,'user_requests':user_requests,
       'tool_allow_list':scenario.starting_context.tool_allow_list,
       'public_task_target':{'field':field,'desired':desired},
       'initial_settings':initial,'final_settings':final_state,
       'states_after_calls':states,'official_evaluation':official,
       'terminal_valid':valid,'score_terminal_relation':classify(official['similarity'],valid),
       'native_tool_calls':len(session.events),
       'native_tool_errors':sum(not e['response']['ok'] for e in session.events),
       'milestones':len(scenario.evaluation.milestone_matcher.milestones),
       'minefields':len(scenario.evaluation.minefield_matcher.milestones),
       'events':session.events,'initial_snapshot':initial_snapshot,'final_snapshot':session.snapshot(),
    }

def write_json(p,o):p.write_text(json.dumps(o,ensure_ascii=False,sort_keys=True,indent=2,allow_nan=False)+'\n')

def run(out):
    out=Path(out);out.mkdir(parents=True,exist_ok=False);(out/'trajectories').mkdir()
    records=[]
    for name in CASES:
        for variant in VARIANTS:
            r=run_case(name,variant);records.append(r)
            write_json(out/'trajectories'/f'{name}__{variant}.json',r)
    rows=[{k:r[k] for k in ['scenario','variant','terminal_valid','score_terminal_relation','native_tool_calls','native_tool_errors','milestones','minefields']} | {'official_similarity':r['official_evaluation']['similarity'],'official_turn_count':r['official_evaluation']['turn_count']} for r in records]
    with (out/'results.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    summary=[]
    for v in VARIANTS:
        subset=[r for r in records if r['variant']==v]
        summary.append({'variant':v,'cases':len(subset),'official_full_scores':sum(r['official_evaluation']['similarity']==1.0 for r in subset),'terminal_valid':sum(r['terminal_valid'] for r in subset),'full_score_terminal_mismatch':sum(r['official_evaluation']['similarity']==1.0 and not r['terminal_valid'] for r in subset),'tool_errors':sum(r['native_tool_errors'] for r in subset)})
    write_json(out/'summary.json',summary)
    # Replay scientific comparison deliberately includes every exact state, UUID,
    # public string and evaluator mapping. Only elapsed_seconds is excluded.
    write_json(out/'scientific_projection.json',project(records))
    print(json.dumps(summary,ensure_ascii=False,indent=2))
    return summary
if __name__=='__main__':run(sys.argv[1])
