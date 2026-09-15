
"""Author-constructed, frozen problem diagnosis on the native public tools.
Three intent templates, two underlying domains, four variants + two error cases.
No claim that these are 14 independent original benchmark scenarios.
"""
from __future__ import annotations
import copy, json, random
from .native import NativeSession, jcopy
from .goals import evaluate
from tool_sandbox.common.utils import deterministic_uuid
TARGET='Fredrik Thordendal';OTHER='John Petrucci'
OLD='+12453344098';NEW='+12025550119';OTHER_NEW='+12025550117'
TEXT="The rehearsal has moved to 18:30. Please confirm when you can."
TITLE='Submit the cobalt expense report'
OTHER_TITLE='Renew the library card'
NEW_TIME=1800003600.0
VARIANTS=('stable','unrelated','changed_old_observation','changed_current_observation')
def exact(rows,key,val):
 matches=[r for r in rows if r[key]==val]
 if len(matches)!=1:raise ValueError('Expected one exact match')
 return matches[0]
def build(family,variant,cid):
 s=NativeSession()
 if family=='reminder_label':
  ids=[r['reminder_id'] for r in s.world()['reminder']]
  target,other,unrelated=ids
  s.admin('modify_reminder',{'reminder_id':target,'content':TITLE,'reminder_timestamp':1800000000.0})
  s.admin('modify_reminder',{'reminder_id':other,'content':OTHER_TITLE,'reminder_timestamp':1800000600.0})
  query=('search_reminder',{'content':TITLE})
 else:query=('search_contacts',{'name':TARGET})
 first=s.call(*query,scope='initial_memory')
 oldrow=exact(first['value'],'content' if family=='reminder_label' else 'name',TITLE if family=='reminder_label' else TARGET)
 old_memory={'reminder' if family=='reminder_label' else 'contact':copy.deepcopy(oldrow)}
 # A real previous-task lookup: same logical stage for old/current conditions.
 observation=None
 if variant!='changed_current_observation':
  observation=s.call(*query,scope='preceding_task_observation')
 if family=='reminder_label':
  if variant=='unrelated':s.admin('modify_reminder',{'reminder_id':unrelated,'content':'Check irrigation timer'})
  if variant.startswith('changed'):
   s.admin('modify_reminder',{'reminder_id':target,'content':OTHER_TITLE})
   s.admin('modify_reminder',{'reminder_id':other,'content':TITLE})
  row=exact(s.world()['reminder'],'content',TITLE)
  goal={'kind':'reminder','reminder_id':row['reminder_id'],'timestamp':NEW_TIME}
  request=f'Find the reminder that currently has the exact text "{TITLE}" and set its reminder time to POSIX timestamp {NEW_TIME:.0f}. Keep its text and location unchanged, and do not edit any other reminder.'
 else:
  if variant=='unrelated':s.admin('modify_contact',{'person_id':deterministic_uuid(payload=OTHER),'phone_number':OTHER_NEW})
  if variant.startswith('changed') or variant=='combined_error':
   s.admin('modify_contact',{'person_id':deterministic_uuid(payload=TARGET),'phone_number':NEW})
   s.admin('modify_contact',{'person_id':deterministic_uuid(payload=OTHER),'phone_number':OLD})
  if variant=='combined_error':s.admin('set_cellular_service_status',{'on':False})
  row=exact(s.world()['contact'],'name',TARGET)
  if family=='person_message':
   request=f'Text {TARGET} at the current number in his contact entry, exactly once, with this exact content: {TEXT}'
   goal={'kind':'person','name':TARGET,'person_id':row['person_id'],'phone_number':row['phone_number'],'content':TEXT,'allow_cellular':True}
  else:
   request=f'Send exactly one text to the literal phone number {OLD}, regardless of who is currently listed under that number. Do not substitute another number. The exact message content is: {TEXT}'
   goal={'kind':'phone','name':TARGET,'phone_number':OLD,'content':TEXT,'allow_cellular':True}
  request+=' If cellular service is disabled, you may enable it. Do not edit contacts, reminders, or other settings.'
 if variant=='changed_current_observation':observation=s.call(*query,scope='preceding_task_observation')
 public={'user_request':request,
   'historical_memory':old_memory,
   'preceding_task_observations':[{'tool':query[0],'arguments':query[1],'response':observation,
     'note':'A lookup from a preceding task. No guarantee it remains current.'}]}
 result={'id':cid,'family':family,'variant':variant,'public':public,'old_memory':old_memory,'goal':goal,
   'world_before':s.world(),'snapshot':s.snapshot(),'preparation_events':s.events}
 return jcopy(result)
def make_cases():
 cs=[]
 for fam in ('person_message','literal_message','reminder_label'):
  for var in VARIANTS:cs.append(build(fam,var,f'c{len(cs):02d}'))
 for fam in ('person_message','literal_message'):
  cs.append(build(fam,'combined_error',f'c{len(cs):02d}'))
 return cs
def infer_intent(public):
 text=public['user_request']
 if text.startswith('Find the reminder'):
  return {'kind':'reminder','title':text.split('"')[1],'timestamp':float(text.split('POSIX timestamp ')[1].split('.')[0])}
 if text.startswith('Send exactly one text'):
  return {'kind':'phone','phone_number':text.split('literal phone number ')[1].split(',')[0],
    'content':text.split('The exact message content is: ')[1].split(' If cellular')[0]}
 return {'kind':'person','name':text.split('Text ')[1].split(' at the current')[0],
    'content':text.split('exact content: ')[1].split(' If cellular')[0]}
def rule_action(public,history,mode='resolve'):
 """A grammar-specific baseline. Reads only the exact public input and tool history.
 No goal/variant/snapshot input. Not a general natural-language parser.
 """
 intent=infer_intent(public)
 own=[h for h in history if h.get('response',{}).get('ok')]
 mutator='modify_reminder' if intent['kind']=='reminder' else 'send_message_with_phone_number'
 if any(h['tool']==mutator for h in own):return {'done':'Requested operation completed.'}
 if history and not history[-1]['response']['ok'] and 'Cellular service is not enabled' in str(history[-1]['response'].get('error')):
  return {'tool':'set_cellular_service_status','arguments':{'on':True}}
 if intent['kind']=='phone':
  return {'tool':mutator,'arguments':{'phone_number':intent['phone_number'],'content':intent['content']}}
 qtool='search_reminder' if intent['kind']=='reminder' else 'search_contacts'
 qargs={'content':intent['title']} if intent['kind']=='reminder' else {'name':intent['name']}
 choices=[h for h in own if h['tool']==qtool and h['arguments']==qargs]
 if not choices and mode=='reuse':
  choices=[h for h in public.get('preceding_task_observations',[]) if h['tool']==qtool and h['arguments']==qargs and h['response']['ok']]
 row=None
 if choices:
  row=exact(choices[-1]['response']['value'],'content' if intent['kind']=='reminder' else 'name',
            intent.get('title',intent.get('name')))
 elif mode=='cached':
  row=public.get('historical_memory',{}).get('reminder' if intent['kind']=='reminder' else 'contact')
 if row is None:return {'tool':qtool,'arguments':qargs}
 if intent['kind']=='reminder':
  return {'tool':mutator,'arguments':{'reminder_id':row['reminder_id'],'reminder_timestamp':intent['timestamp']}}
 return {'tool':mutator,'arguments':{'phone_number':row['phone_number'],'content':intent['content']}}
def scripted(case,mode):
 s=NativeSession(case['snapshot']);history=[];finished=False
 for _ in range(8):
  a=rule_action(case['public'],history,mode)
  if 'done' in a:finished=True;break
  r=s.call(a['tool'],a['arguments']);history.append({**a,'response':r})
 return {'case_id':case['id'],'mode':mode,'events':s.events,'finished':finished,
   'score':evaluate(case['world_before'],s.world(),case['goal'],s.events),
   'runtime_tool_calls':len(s.events),'after_world':s.world()}
