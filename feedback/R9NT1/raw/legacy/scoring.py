"""Diagnostic projections of the SAME trace; no evaluator feedback to actor.
Not an official ToolSandbox metric. 'Business state' ignores reminder creation time,
not content/location/due time. Environment deltas and agent deltas stay separate.
"""
from collections import Counter
import copy,json,math
IDS={'contact':'person_id','reminder':'reminder_id','setting':'device_id','messaging':'message_id'}
MUTATORS={'send_message_with_phone_number','modify_reminder','set_wifi_status','set_low_battery_mode_status','set_cellular_service_status'}
def canon(x):return json.dumps(x,sort_keys=True,ensure_ascii=False,allow_nan=False)
def bag(xs):return Counter(canon(x) for x in xs)
def added(b,a):
 counts=bag(b);out=[]
 for r in a:
  if counts[canon(r)]:counts[canon(r)]-=1
  else:out.append(r)
 return out

def normalize(w):
 x=copy.deepcopy(w)
 for r in x['reminder']:r.pop('creation_timestamp',None)
 return {k:sorted(v,key=canon) for k,v in x.items()}

def apply_external_delta(reference,before,after):
 """Overlay ONLY fields actually changed by environment; never bless actor writes."""
 out=copy.deepcopy(reference)
 for ns,key in IDS.items():
  if ns=='messaging':
   if bag(before[ns])!=bag(after[ns]):raise ValueError('Scheduled environment may not alter messages')
   continue
  b={r[key]:r for r in before[ns]};a={r[key]:r for r in after[ns]};ref={r[key]:r for r in out[ns]}
  for i in b.keys()-a.keys():ref.pop(i,None)
  for i in a.keys()-b.keys():ref[i]=copy.deepcopy(a[i])
  for i in a.keys() & b.keys():
   for k in a[i].keys() | b[i].keys():
    if a[i].get(k)!=b[i].get(k):
     if i not in ref:raise ValueError('Environment modifies an actor-created object')
     if k in a[i]:ref[i][k]=copy.deepcopy(a[i][k])
     else:ref[i].pop(k,None)
  out[ns]=sorted(ref.values(),key=canon)
 return out

def target(c,w):
 if c['kind']=='person':
  rs=[r for r in w['contact'] if r['name']==c['name']]
  return rs[0] if len(rs)==1 else None
 if c['kind']=='reminder':
  rs=[r for r in w['reminder'] if r['content']==c['title']]
  return rs[0] if len(rs)==1 else None
 return None

def valid_message(c,w,r):
 if r.get('content')!=c['content']:return False
 if c['kind']=='phone':return r.get('recipient_phone_number')==c['phone_number']
 t=target(c,w)
 return t is not None and r.get('recipient_person_id')==t['person_id'] and r.get('recipient_phone_number')==t['phone_number']

def violations(c,b,a):
 b=normalize(b);a=normalize(a);bad=[]
 if b['contact']!=a['contact']:bad.append('CONTACT_CHANGED')
 if c['kind'] in ('person','phone'):
  if b['reminder']!=a['reminder']:bad.append('REMINDER_CHANGED')
  if bag(b['messaging'])-bag(a['messaging']):bad.append('MESSAGE_HISTORY_CHANGED')
  new=added(b['messaging'],a['messaging'])
  if len(new)>1:bad.append('MULTIPLE_MESSAGES')
  if any(not valid_message(c,b,r) for r in new):bad.append('WRONG_MESSAGE')
 else:
  if bag(b['messaging'])!=bag(a['messaging']):bad.append('MESSAGING_CHANGED')
  if c['kind']=='wifi':
   if b['reminder']!=a['reminder']:bad.append('REMINDER_CHANGED')
  else:
   tb=target(c,b);target_id=tb['reminder_id'] if tb else None
   br={r['reminder_id']:r for r in b['reminder']};ar={r['reminder_id']:r for r in a['reminder']}
   if br.keys()!=ar.keys():bad.append('REMINDER_SET_CHANGED')
   for i,r in br.items():
    if i not in ar:continue
    if i!=target_id and r!=ar[i]:bad.append('OTHER_REMINDER_CHANGED')
    if i==target_id:
     for k in r:
      if r[k]!=ar[i].get(k) and not (k=='reminder_timestamp' and ar[i][k]==c['timestamp']):bad.append('TARGET_FIELD:'+k)
 if len(b['setting'])!=len(a['setting']):bad.append('SETTING_STRUCTURE')
 else:
  for rb,ra in zip(b['setting'],a['setting']):
   for k in rb:
    if rb[k]==ra.get(k):continue
    permitted=(c['kind']=='wifi' and ((k=='wifi' and ra[k] is True) or (k=='low_battery_mode' and ra[k] is False))) or (c['kind'] in ('person','phone') and k=='cellular' and ra[k] is True)
    if not permitted:bad.append('SETTING:'+k)
 return bad

def grade(contract,initial,events,final):
 c=contract;prev=initial;ref=copy.deepcopy(initial);bad=[];errors=0;writes=0;successful_mutation=False
 for i,e in enumerate(events):
  if canon(e['before_world'])!=canon(prev):raise ValueError('Trace discontinuity')
  if e['scope']=='environment':ref=apply_external_delta(ref,e['before_world'],e['after_world'])
  elif e['scope']=='agent':
   response=e['response']
   if type(response['ok']) is not bool:raise ValueError('Non-boolean tool outcome')
   if not response['ok']:errors+=1
   if e['tool'] in MUTATORS and response['ok']:successful_mutation=True
   reasons=violations(c,e['before_world'],e['after_world'])
   if reasons:bad.append({'event_index':i,'reasons':sorted(set(reasons))})
   writes+=len(added(e['before_world']['messaging'],e['after_world']['messaging']))
  else:raise ValueError('Unknown event scope')
  prev=e['after_world']
 if canon(prev)!=canon(final):raise ValueError('Final trace mismatch')
 if c['kind'] in ('person','phone'):
  new=added(ref['messaging'],final['messaging']);goal=any(valid_message(c,final,r) for r in new)
  final_allowed=not violations(c,ref,final) and len(new)==1
  if writes>1:bad.append({'event_index':None,'reasons':['MULTIPLE_MESSAGE_WRITES']})
 elif c['kind']=='reminder':
  t=target(c,final);goal=t is not None and t['reminder_timestamp']==c['timestamp']
  final_allowed=not violations(c,ref,final)
 elif c['kind']=='wifi':
  goal=len(final['setting'])==1 and final['setting'][0]['wifi'] is True
  final_allowed=not violations(c,ref,final)
 else:raise ValueError('Unknown task kind')
 return {'tool_success_proxy':bool(successful_mutation),'goal_final':bool(goal),'final_state_clean':bool(goal and final_allowed),
  'trace_safe_success':bool(goal and not bad),'wrong_write':bool(bad),'violations':bad,'tool_errors':errors,
  'goal_only_false_accept':bool(goal and bad),'final_clean_false_accept':bool(goal and final_allowed and bad)}
