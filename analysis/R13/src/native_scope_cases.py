"""A public goal-revision scenario, scripted roles, unchanged native executor.

This is an evaluator sensitivity experiment, NOT a new LLM benchmark result.
User messages instantiate the original simulator specification. No outside state
mutation occurs. Original scores are reported unchanged, alongside local checks.
"""
import copy,csv,json,attrs
from pathlib import Path
from scope_logic import verdict,combine
from native_study import NativeSession
from tool_sandbox.common.execution_context import DatabaseNamespace as DB,RoleType as Role
from tool_sandbox.common.message_conversion import Message
from tool_sandbox.roles.base_role import BaseRole
from tool_sandbox.common.tool_discovery import ToolBackend
from tool_sandbox.scenarios.multiple_user_turn_scenarios import named_multiple_user_turn_scenarios
from tool_sandbox.tools.contact import search_contacts,modify_contact
NAME='update_contact_relationship_with_relationship_twice_multiple_user_turn'
VARIANTS=('correct_revision','missing_final_revision','undo_latest_goal','no_effect','redundant_error_then_revision')

def run_case(variant):
    if variant not in VARIANTS:raise ValueError(variant)
    sc=copy.deepcopy(named_multiple_user_turn_scenarios(ToolBackend.DEFAULT)[NAME])
    session=NativeSession(sc,{'search_contacts':search_contacts,'modify_contact':modify_contact})
    initial=session.snapshot();contacts=session.rows(DB.CONTACT)
    target_ids=sorted(r['person_id'] for r in contacts if r['relationship']=='friend')
    if len(target_ids)!=2:raise ValueError('Pinned task expected two original friends')
    states=[]
    def observe(label):
        states.append({'label':label,'snapshot_index':session.ctx.max_sandbox_message_index,'contacts':session.rows(DB.CONTACT)})
    def message(role,text):BaseRole.add_messages([Message(sender=role,recipient=Role.USER if role==Role.AGENT else Role.AGENT,content=text)]);observe('message:'+str(role))
    def call(tool,args):
        result=session.call(tool,args);observe('tool:'+tool);return result
    observe('initial')
    result=call('search_contacts',{'relationship':'friend'})
    if not result['ok'] or sorted(r['person_id'] for r in result['value'])!=target_ids:raise ValueError('Unexpected native lookup')
    message(Role.AGENT,'Your friends are Fredrik Thordendal and John Petrucci.')
    message(Role.USER,'Make all of these friends my enemies.')
    activation_first=len(states)-1
    if variant=='redundant_error_then_revision':
        before=session.rows(DB.CONTACT)
        res=call('modify_contact',{'person_id':'00000000-0000-0000-0000-000000000000','relationship':'enemy'})
        if res['ok'] or before!=session.rows(DB.CONTACT):raise ValueError('Expected no-write missing-ID error')
    if variant!='no_effect':
        for uid in target_ids:
            if not call('modify_contact',{'person_id':uid,'relationship':'enemy'})['ok']:raise ValueError('Unexpected write error')
    message(Role.AGENT,'Fredrik Thordendal and John Petrucci are now your enemies')
    end_first=len(states)-1
    message(Role.USER,'Now update those same people back to my friends.')
    activation_second=len(states)-1
    if variant not in ('no_effect','missing_final_revision'):
        for uid in target_ids:
            if not call('modify_contact',{'person_id':uid,'relationship':'friend'})['ok']:raise ValueError('Unexpected write error')
    if variant=='undo_latest_goal':
        for uid in target_ids:
            if not call('modify_contact',{'person_id':uid,'relationship':'enemy'})['ok']:raise ValueError('Unexpected undo error')
    session.finish('Fredrik Thordendal and John Petrucci are now your friends again.')
    observe('terminated')
    def relation(st,val):
        index={r['person_id']:r for r in st['contacts']}
        return all(uid in index and index[uid]['relationship']==val for uid in target_ids)
    enemy=[relation(st,'enemy') for st in states];friend=[relation(st,'friend') for st in states]
    def protected(st):
        previous={r['person_id']:r for r in contacts};current={r['person_id']:r for r in st['contacts']}
        if previous.keys()!=current.keys():return False
        for uid,row in previous.items():
            for key,v in row.items():
                if uid in target_ids and key=='relationship':continue
                if current[uid][key]!=v:return False
        return True
    invariant=[protected(st) for st in states]
    first=verdict(enemy,'terminal',activation_first,end_first)
    second=verdict(friend,'terminal',activation_second)
    inv=verdict(invariant,'always')
    official=attrs.asdict(sc.evaluation.evaluate(session.ctx,max_turn_count=sc.max_messages))
    final_snapshot=session.snapshot()
    return {'evidence_kind':'SCRIPTED_ORIGINAL_PUBLIC_USER_REVISION_NOT_LLM','scenario':NAME,'variant':variant,
            'target_ids_bound_at_initial_friend_query':target_ids,'initial_snapshot':initial,'final_snapshot':final_snapshot,
            'states':states,'events':session.events,'official_evaluation':official,
            'first_goal_active_interval':[activation_first,end_first],
            'second_goal_active_interval':[activation_second,len(states)-1],
            'enemy_predicate':enemy,'friend_predicate':friend,'protected_predicate':invariant,
            'first_scoped_goal':first,'latest_terminal_only':second,'protected_invariant':inv,
            'scoped_contract':combine([first,second,inv]),
            'blanket_all_goals_terminal':combine([verdict(enemy,'terminal'),verdict(friend,'terminal'),inv]),
            'native_tool_calls':len(session.events),'tool_errors':sum(not e['response']['ok'] for e in session.events)}

def run(out):
    out=Path(out);out.mkdir(parents=True,exist_ok=False);(out/'trajectories').mkdir()
    results=[]
    for v in VARIANTS:
        r=run_case(v);(out/'trajectories'/f'{v}.json').write_text(json.dumps(r,ensure_ascii=False,sort_keys=True,indent=2,allow_nan=False)+'\n')
        row={k:r[k] for k in ('scenario','variant','first_scoped_goal','latest_terminal_only','protected_invariant','scoped_contract','blanket_all_goals_terminal','native_tool_calls','tool_errors')}
        row['official_similarity']=r['official_evaluation']['similarity'];results.append(row)
    with (out/'results.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=results[0]);w.writeheader();w.writerows(results)
    (out/'summary.json').write_text(json.dumps(results,indent=2,sort_keys=True)+'\n')
    print(json.dumps(results,indent=2));return results
