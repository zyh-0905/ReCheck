"""Native, scripted check/use interleavings. NOT additional LLM experiments.
Atomic contracts are reference capabilities stipulated by the single-thread event
scheduler, not a claim of thread safety of ToolSandbox or remote transactions.
"""
from __future__ import annotations
import copy, json
from collections import Counter
import bootstrap
from r7clib.native import NativeSession
from r7clib.cases import build, infer_intent, TARGET, OTHER, TITLE, OTHER_TITLE

POLICIES=('query_use','global_guard','scoped_guard','scoped_retry1')
INTENTS=('person','literal','reminder')

def exact(rows,key,value):
    rows=[x for x in rows if x[key]==value]
    return rows[0] if len(rows)==1 else None

def rowbag(rows):
    return Counter(json.dumps(x,sort_keys=True,separators=(',',':'),allow_nan=False) for x in rows)

def score_write(intent, request, before, after):
    """Independent scorer at the write linearization point (not final drifted state).
    This does not import or call the old goals/evaluate implementation.
    """
    if intent not in INTENTS: raise ValueError(intent)
    if intent in ('person','literal'):
        if any(before[n]!=after[n] for n in ('contact','reminder','setting')): return False
        old,new=rowbag(before['messaging']),rowbag(after['messaging'])
        if old-new: return False
        added=list((new-old).elements())
        if len(added)!=1: return False
        msg=json.loads(added[0])
        if msg['content']!=request['content']: return False
        if intent=='literal': return msg['recipient_phone_number']==request['phone_number']
        target=exact(before['contact'],'name',request['name'])
        return target is not None and msg['recipient_phone_number']==target['phone_number'] and msg['recipient_person_id']==target['person_id']
    if any(before[n]!=after[n] for n in ('contact','messaging','setting')): return False
    target=exact(before['reminder'],'content',request['title'])
    if target is None: return False
    old={x['reminder_id']:x for x in before['reminder']}
    new={x['reminder_id']:x for x in after['reminder']}
    if old.keys()!=new.keys(): return False
    for rid,x in old.items():
        y=new[rid]
        if rid!=target['reminder_id']:
            if x!=y:return False
        else:
            if y['reminder_timestamp']!=request['timestamp']:return False
            if any(x[k]!=y[k] for k in x if k not in ('creation_timestamp','reminder_timestamp')):return False
    return True

def resolve(session, intent, request):
    """Only legitimate native query results are used for selecting the action."""
    if intent=='literal': return ('literal',request['phone_number'])
    if intent=='person':
        result=session.call('search_contacts',{'name':request['name']},scope='resolve')
        row=exact(result['value'] or [],'name',request['name']) if result['ok'] else None
        return None if row is None else ('person',row['person_id'],row['phone_number'])
    result=session.call('search_reminder',{'content':request['title']},scope='resolve')
    row=exact(result['value'] or [],'content',request['title']) if result['ok'] else None
    return None if row is None else ('reminder',row['reminder_id'],row['content'])

def action_for(intent,request,binding):
    if intent=='reminder':return 'modify_reminder',{'reminder_id':binding[1],'reminder_timestamp':request['timestamp']}
    phone=binding[1] if intent=='literal' else binding[2]
    return 'send_message_with_phone_number',{'phone_number':phone,'content':request['content']}

def intervene(session,intent,event,index):
    """Environment-only change. Return all admin operations for audit."""
    w=session.world();ops=[]
    if event=='none':return ops
    if event=='unrelated':
        row=exact(w['contact'],'name',OTHER)
        ops=[('modify_contact',{'person_id':row['person_id'],'relationship':f'R8 unrelated state {index}'})]
    elif event=='binding':
        if intent=='reminder':
            target=exact(w['reminder'],'content',TITLE)
            other=next(x for x in w['reminder'] if x['reminder_id']!=target['reminder_id'] and x['content']==OTHER_TITLE)
            ops=[('modify_reminder',{'reminder_id':target['reminder_id'],'content':OTHER_TITLE}),
                 ('modify_reminder',{'reminder_id':other['reminder_id'],'content':TITLE})]
        else:
            target=exact(w['contact'],'name',TARGET);other=exact(w['contact'],'name',OTHER)
            phone='+12025550119' if index%2 else '+12025550118'
            if target['phone_number']==phone:phone='+12025550117'
            ops=[('modify_contact',{'person_id':target['person_id'],'phone_number':phone}),
                 ('modify_contact',{'person_id':other['person_id'],'phone_number':target['phone_number']})]
    elif event=='nonbinding':
        if intent=='reminder':
            target=exact(w['reminder'],'content',TITLE)
            ops=[('modify_reminder',{'reminder_id':target['reminder_id'],'latitude':41.0,'longitude':-70.0})]
        else:
            target=exact(w['contact'],'name',TARGET)
            ops=[('modify_contact',{'person_id':target['person_id'],'relationship':f'R8 harmless field {index}'})]
    else:raise ValueError(event)
    for tool,args in ops:session.admin(tool,args)
    return [{'tool':n,'arguments':a} for n,a in ops]

def run_case(intent='person',event='none',when='none',policy='query_use',churn=False):
    if intent not in INTENTS or policy not in POLICIES:raise ValueError('unknown intent/policy')
    if event not in ('none','binding','unrelated','nonbinding'):raise ValueError('event')
    if (event=='none' and when!='none') or (event!='none' and when not in ('before_resolve','after_resolve','after_use')):raise ValueError('timing')
    family={'person':'person_message','literal':'literal_message','reminder':'reminder_label'}[intent]
    case=build(family,'stable','r8_'+intent)
    request=infer_intent(case['public'])
    s=NativeSession(case['snapshot']);timeline=[];writes=[];rejections=0;tokens_issued=0;tokens_checked=0
    def mutate(index):
        before=s.world();ops=intervene(s,intent,event,index)
        timeline.append({'stage':'external_intervention','index':index,'operations':ops,'before_world':before,'after_world':s.world()})
    if when=='before_resolve':mutate(1)
    limit=2 if policy=='scoped_retry1' else 1
    for attempt in range(limit):
        binding=resolve(s,intent,request)
        timeline.append({'stage':'resolved','attempt':attempt,'binding':binding})
        token=None
        if policy=='global_guard':token=s.world();tokens_issued+=1
        if when=='after_resolve' and (attempt==0 or churn):mutate(attempt+1)
        if binding is None:
            rejections+=1;timeline.append({'stage':'ambiguous_resolution','attempt':attempt});break
        accepted=True
        if policy=='global_guard':
            tokens_checked+=1;accepted=token==s.world()
        elif policy in ('scoped_guard','scoped_retry1'):
            # No external scheduler event can run between this check and the write.
            accepted=resolve(s,intent,request)==binding
        timeline.append({'stage':'commit_precondition','attempt':attempt,'accepted':accepted,'contract':policy})
        if not accepted:
            rejections+=1
            if attempt+1==limit:break
            continue
        name,args=action_for(intent,request,binding)
        before=s.world();r=s.call(name,args,scope='commit');after=s.world()
        good=score_write(intent,request,before,after) if r['ok'] else False
        # A rejected native call has no wrong write; unexpected mutations are flagged.
        wrong=(before!=after) and not good
        writes.append({'tool':name,'arguments':args,'response':r,'before_world':before,'after_world':after,'correct_at_commit':good,'wrong_write':wrong})
        timeline.append({'stage':'committed','attempt':attempt,'correct_at_commit':good})
        break
    if when=='after_use':mutate(1)
    good=any(x['correct_at_commit'] for x in writes)
    wrong=any(x['wrong_write'] for x in writes)
    return {'intent':intent,'event':event,'when':when,'policy':policy,'churn':churn,
        'request':request,'public_user_request':case['public']['user_request'],
        'initial_snapshot':case['snapshot'],'preparation_tool_calls':len(case['preparation_events']),
        'safe_success':good and not wrong,'wrong_write':wrong,'rejections':rejections,
        'writes':writes,'events':s.events,'timeline':timeline,'final_world':s.world(),
        'tool_calls':len(s.events),'global_token_issuances':tokens_issued,'global_token_checks':tokens_checked,
        'invariant_error':any(e['before_world']!=e['after_world'] for e in s.events if e['tool'].startswith('search_')),'atomicity_scope':'declared_single_thread_event_schedule_not_remote_atomicity'}

def all_specs():
    for intent in INTENTS:
        for policy in POLICIES:
            yield (intent,'none','none',policy)
            for event in ('unrelated','binding','nonbinding'):
                for when in ('before_resolve','after_resolve','after_use'):
                    yield (intent,event,when,policy)
