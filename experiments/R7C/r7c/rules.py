"""Scripted diagnostic controls, not language-model results or novel algorithms."""
import re
from .native import Session
from .score import grade
from .core import MAX_STEPS

def run_rule(case,policy):
 s=Session(case);task=case['task'];family=case['family'];steps=[]
 memory=case['memory'];observations=case['observations']
 def call(n,a):
  if len(steps)>=MAX_STEPS-1:raise RuntimeError('script exceeds same decision budget')
  out=s.call(n,a);steps.append({'action':'tool','name':n,'arguments':a});return out
 def exact(rows,key,val):
  match=[r for r in rows if r.get(key)==val]
  if len(match)!=1:raise ValueError('Public evidence does not uniquely identify target')
  return match[0]
 def observed(tool):
  arr=observations if policy=='reuse_observed' and observations else memory
  return next((e['value'] for e in reversed(arr) if e['tool']==tool),None)
 if family in ('person_message','literal_message'):
  literal=re.search(r'the phone number (\+\d+)',task)
  name=re.search(r'message to (.*?) at her current',task)
  body=re.search(r'exactly "(.*?)"',task).group(1)
  def resolve():return exact(call('search_contacts',{'name':name.group(1)})['value'],'name',name.group(1))['phone_number']
  if literal:phone=literal.group(1)
  elif policy in ('always_resolve','no_memory'):phone=resolve()
  else:phone=exact(observed('search_contacts'),'name',name.group(1))['phone_number']
  result=call('send_message_with_phone_number',{'phone_number':phone,'content':body})
  if not result['ok']:
   if result['error_type']=='ConnectionError':call('set_cellular_service_status',{'on':True})
   if policy=='on_error_resolve' and name:phone=resolve()
   call('send_message_with_phone_number',{'phone_number':phone,'content':body})
 elif family=='reminder_retime':
  name=re.search(r'content is exactly "(.*?)"',task).group(1);t=float(re.search(r'timestamp (\d+)',task).group(1))
  def resolve():return exact(call('search_reminder',{'content':name})['value'],'content',name)['reminder_id']
  if policy in ('always_resolve','no_memory'):rid=resolve()
  else:rid=exact(observed('search_reminder'),'content',name)['reminder_id']
  result=call('modify_reminder',{'reminder_id':rid,'reminder_timestamp':t})
  if not result['ok']:
   rid=resolve();call('modify_reminder',{'reminder_id':rid,'reminder_timestamp':t})
 else:
  current=call('get_wifi_status',{})['value'] if policy in ('always_resolve','no_memory') else observed('get_wifi_status')
  if not current:
   result=call('set_wifi_status',{'on':True})
   if not result['ok']:
    # Ordinary error is sufficient to resolve an already-enabled state.
    if result['error_type']=='PermissionError':
     call('set_low_battery_mode_status',{'on':False});call('set_wifi_status',{'on':True})
    elif result['error_type']=='ValueError':call('get_wifi_status',{})
 steps.append({'action':'finish','summary':'Scripted completion; score checks native state.'})
 return {'case_id':case['id'],'family':family,'condition':case['condition'],'policy':policy,
         'evidence_kind':'SCRIPTED_NATIVE_TOOL_DIAGNOSTIC_NOT_LLM_RESULT','actions':steps,'events':s.events,
         'final_state':s.state(),'score':grade(case,s.events,s.state(),True),'decision_count':len(steps),
         'runtime_tool_calls':len(s.events),'historical_queries':len(memory),'ordinary_queries':len(observations)}
