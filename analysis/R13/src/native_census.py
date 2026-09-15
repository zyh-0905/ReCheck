"""Enumerate unchanged public factories without executing a model or user simulator."""
import inspect,json,functools,csv,hashlib
from pathlib import Path
from collections import Counter
from census_rules import classify,constraint_kind
from tool_sandbox.common.execution_context import DatabaseNamespace as DB, RoleType
from tool_sandbox.common.tool_discovery import ToolBackend
from tool_sandbox.scenarios import named_scenarios
from tool_sandbox.scenarios.single_tool_call_scenarios import named_single_tool_call_scenarios
from tool_sandbox.scenarios.multiple_tool_call_scenarios import named_multiple_tool_call_scenarios
from tool_sandbox.scenarios.multiple_user_turn_scenarios import named_multiple_user_turn_scenarios
from tool_sandbox.scenarios.insufficient_information_scenarios import named_insufficient_information_scenarios

def fname(f):
    while isinstance(f,functools.partial): f=f.func
    return f.__name__
def write(p,x):p.write_text(json.dumps(x,ensure_ascii=False,sort_keys=True,indent=2,allow_nan=False)+'\n')
def run(out):
    out=Path(out);out.mkdir(parents=True,exist_ok=False)
    factories=[named_single_tool_call_scenarios,named_multiple_tool_call_scenarios,named_multiple_user_turn_scenarios,named_insufficient_information_scenarios]
    records=[]
    for f in factories:
        defs=f(ToolBackend.DEFAULT)
        for name,sc in sorted(defs.items()):
            constraints=[];guards=0;interaction=0
            for idx,m in enumerate(sc.evaluation.milestone_matcher.milestones):
                for c in m.snapshot_constraints:
                    kind=constraint_kind(str(c.database_namespace),fname(c.snapshot_constraint))
                    if kind=='preservation_guardrail': guards+=1
                    elif kind=='interaction_constraint': interaction+=1
                    else:
                        constraints.append({'milestone':idx,'db':str(c.database_namespace),'function':fname(c.snapshot_constraint),'reference':c.reference_milestone_node_index,'target':c.target_dataframe.to_dicts() if c.target_dataframe is not None else None})
            msgs=sc.starting_context.get_database(DB.SANDBOX,get_all_history_snapshots=True).to_dicts()
            user=[m['content'] for m in msgs if m['sender']==RoleType.USER and m['recipient']==RoleType.AGENT and m.get('visible_to')!=[RoleType.USER]]
            spec=[m['content'] for m in msgs if m['sender']==RoleType.SYSTEM and m['recipient']==RoleType.USER]
            source=Path(inspect.getsourcefile(f));txt=source.read_text();line=next((i+1 for i,l in enumerate(txt.splitlines()) if '"'+name+'"' in l),None)
            rec={'name':name,'factory':f.__name__,'source_path':'tool_sandbox/scenarios/'+source.name,'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'literal_name_line':line,'initial_public_user_messages':user,'simulator_spec_offline_only':spec[-1:] if spec else [],'categories':[str(c) for c in sc.categories],'allowed_tools':sc.starting_context.tool_allow_list,'milestones':len(sc.evaluation.milestone_matcher.milestones),'minefields':len(sc.evaluation.minefield_matcher.milestones),'explicit_state_constraints':constraints,'automatic_guardrail_constraints':guards,'interaction_constraints':interaction,'semantic_review_status':'candidate_source_rule_not_independent_human_gold'}
            rec['candidate_class']=classify(rec);records.append(rec)
    if len({r['name'] for r in records})!=len(records):raise ValueError('duplicate base names')
    # Actual factory construction rather than assuming that eight augmentations exist.
    all_defs=named_scenarios(ToolBackend.DEFAULT)
    expanded=sorted(all_defs)
    rows=[{'name':r['name'],'factory':r['factory'],'candidate_class':r['candidate_class'],'initial_request':' | '.join(r['initial_public_user_messages']),'source_path':r['source_path'],'literal_name_line':r['literal_name_line'],'milestones':r['milestones'],'minefields':r['minefields'],'explicit_state_constraints':len(r['explicit_state_constraints']),'automatic_guardrails':r['automatic_guardrail_constraints'],'setting_is_prerequisite':bool(any(c['db']=='SETTING' for c in r['explicit_state_constraints']) and r['candidate_class'] not in ('terminal_setting_candidate','insufficient_information_policy')),'independent_human_review':False} for r in records]
    with (out/'task_census.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=rows[0]);w.writeheader();w.writerows(rows)
    write(out/'task_census.json',records);write(out/'expanded_names.json',expanded)
    summary={'base_registered_items':len(records),'expanded_registered_items':len(expanded),'factory_counts':dict(Counter(r['factory'] for r in records)),'candidate_class_counts':dict(Counter(r['candidate_class'] for r in records)),'has_explicit_state_constraint':sum(bool(r['explicit_state_constraints']) for r in records),'with_setting_prerequisite_candidates':sum(r['setting_is_prerequisite'] for r in rows),'independent_human_semantic_labels':0,'executed_model_episodes':0,'counts_are_not_independent_task_families':True}
    write(out/'summary.json',summary);print(json.dumps(summary,indent=2))
