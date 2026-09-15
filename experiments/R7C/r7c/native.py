"""Pinned native ToolSandbox functions; private fixture data never enters actor projection.
Direct allowlisted dispatch, not upstream InteractiveConsole or Scenario.play.
"""
from __future__ import annotations
import copy,inspect,json,time,uuid,datetime
from contextlib import contextmanager
from unittest.mock import patch
from .core import ensure_upstream,canonical,digest
ensure_upstream()
from tool_sandbox.common.execution_context import ExecutionContext,DatabaseNamespace as DB,RoleType as Role,set_current_context,get_current_context
from tool_sandbox.tools import contact,messaging,reminder,setting

FAMILIES=('person_message','literal_message','reminder_retime','wifi_dependency')
CONDITIONS=('stable','unrelated','changed','observed_after','observed_before','explicit_error')
TOOLS={f.__name__:f for f in (contact.search_contacts,messaging.send_message_with_phone_number,messaging.search_messages,
 setting.get_cellular_service_status,setting.set_cellular_service_status,setting.get_wifi_status,setting.set_wifi_status,
 setting.get_low_battery_mode_status,setting.set_low_battery_mode_status,reminder.search_reminder,reminder.modify_reminder)}
NAME='Mira Chen';OTHER='Robin Shah';OLD='+12025550111';NEW='+12025550113'
TEXT='The blue folder is ready.';REMINDER='Submit the orange folder';NEW_TIME=1893492000.0
DBS=(DB.SETTING,DB.CONTACT,DB.MESSAGING,DB.REMINDER)

def specs():return [{'id':f'c{i*6+j:02d}','family':f,'condition':c} for i,f in enumerate(FAMILIES) for j,c in enumerate(CONDITIONS)]
def allowed(family):
 if family in ('person_message','literal_message'):return ('search_contacts','send_message_with_phone_number','search_messages','get_cellular_service_status','set_cellular_service_status')
 if family=='reminder_retime':return ('search_reminder','modify_reminder')
 return ('get_wifi_status','set_wifi_status','get_low_battery_mode_status','set_low_battery_mode_status')

def public_input(case,method):
 if method not in ('no_memory','memory_standard','memory_verify'):raise ValueError('Unknown arm')
 return {'task':case['task'],'historical_memory':[] if method=='no_memory' else copy.deepcopy(case['memory']),
         'ordinary_observations':copy.deepcopy(case['observations'])}

def state(ctx):return {str(ns):copy.deepcopy(ctx.get_database(ns).to_dicts()) for ns in DBS}
def mark(ctx,text,role=Role.SYSTEM):
 ctx.add_to_database(DB.SANDBOX,[{'sender':role,'recipient':role,'content':text,'visible_to':[role]}])

def tool_docs(family):
 return [{'name':n,'signature':str(inspect.signature(TOOLS[n])),'documentation':inspect.getdoc(TOOLS[n]) or ''} for n in allowed(family)]

@contextmanager
def replay_clock(module,epoch=None,uid=None):
 """Audit/fixture-only control of native UUID and clock; never controls actor choices."""
 from contextlib import ExitStack
 with ExitStack() as st:
  if epoch is not None:
   class Clock(datetime.datetime):
    @classmethod
    def now(cls,tz=None):return cls.fromtimestamp(epoch,tz or datetime.timezone.utc)
   import types
   st.enter_context(patch.object(module,'datetime',types.SimpleNamespace(datetime=Clock)))
  if uid is not None:st.enter_context(patch.object(module,'uuid4',lambda:uuid.UUID(uid)))
  yield

def local_only(fn):
 def wrapped(*a,**kw):
  import socket
  def deny(*a,**kw):raise RuntimeError('Network disabled during native tool execution')
  with patch.object(socket.socket,'connect',deny),patch.object(socket.socket,'connect_ex',deny),patch.object(socket,'create_connection',deny):
   return fn(*a,**kw)
 return wrapped

class Session:
 def __init__(self,case):
  snap=copy.deepcopy(case['snapshot'])
  if snap.get('interactive_console') is not None:raise ValueError('Serialized executable console is forbidden')
  self.ctx=ExecutionContext.from_dict(snap);self.family=case['family'];self.events=[]
  self.ctx.tool_allow_list=list(allowed(self.family));self.ctx.trace_tool=False;set_current_context(self.ctx)
 def state(self):return state(self.ctx)
 def snapshot(self):return self.ctx.to_dict(serialize_console=False)
 @local_only
 def call(self,name,args,replay_event=None):
  set_current_context(self.ctx);before=self.state();tic=time.perf_counter()
  try:
   if name not in allowed(self.family):raise ValueError('Tool not allowed in this task')
   if type(args) is not dict:raise ValueError('Arguments must be object')
   args=json.loads(canonical(args));inspect.signature(TOOLS[name]).bind(**args)
   mark(self.ctx,canonical({'tool':name,'arguments':args}),Role.AGENT)
  except (TypeError,ValueError) as e:
   response={'ok':False,'error_type':'InterfaceError','error':str(e),'value':None}
  else:
   try:
    epoch=uid=None;module=None
    if replay_event and replay_event['response'].get('ok'):
     if name=='send_message_with_phone_number':
      uid=replay_event['response']['value'];module=messaging
      row=next(r for r in replay_event['after']['MESSAGING'] if r['message_id']==uid);epoch=row['creation_timestamp']
     elif name=='modify_reminder':
      module=reminder;row=next(r for r in replay_event['after']['REMINDER'] if r['reminder_id']==args['reminder_id']);epoch=row['creation_timestamp']
    if module:
     with replay_clock(module,epoch,uid):value=TOOLS[name](**args)
    else:value=TOOLS[name](**args)
    response={'ok':True,'error_type':None,'error':None,'value':value}
   except Exception as e:response={'ok':False,'error_type':type(e).__name__,'error':str(e),'value':None}
   mark(self.ctx,canonical(response),Role.EXECUTION_ENVIRONMENT)
  event={'tool':name,'arguments':args,'response':copy.deepcopy(response),'before':before,'after':self.state(),
         'elapsed_seconds':time.perf_counter()-tic,'snapshot_index':self.ctx.max_sandbox_message_index}
  self.events.append(event)
  return response

def make_case(spec):
 f=spec['family'];c=spec['condition'];ctx=ExecutionContext();set_current_context(ctx);ctx.trace_tool=False
 setup=[];initial=[];observations=[];ids={}
 def do(fun,args,scope):
  mark(ctx,'Controlled setup: '+scope)
  v=fun(**args);e={'tool':fun.__name__,'arguments':copy.deepcopy(args),'value':copy.deepcopy(v),'scope':scope}
  setup.append(e);return v
 # UUID and clock are controlled only while creating public fixtures. No model calls.
 seq=iter(str(uuid.uuid5(uuid.NAMESPACE_URL,f'R7C/{f}/{i}')) for i in range(10))
 with patch.object(contact,'uuid4',lambda:uuid.UUID(next(seq))):
  ids['self']=do(contact.add_contact,{'name':'Alex Park','phone_number':'+12025550110','is_self':True},'initial_data')
  ids['target']=do(contact.add_contact,{'name':NAME,'phone_number':OLD,'relationship':'colleague'},'initial_data')
  ids['other']=do(contact.add_contact,{'name':OTHER,'phone_number':'+12025550112','relationship':'friend'},'initial_data')
 with replay_clock(reminder,1770000000.0,str(uuid.uuid5(uuid.NAMESPACE_URL,'R7C/reminder/target'))):
  ids['reminder']=do(reminder.add_reminder,{'content':REMINDER,'reminder_timestamp':1800000000.0},'initial_data')
 with replay_clock(reminder,1770000000.0,str(uuid.uuid5(uuid.NAMESPACE_URL,'R7C/reminder/other'))):
  ids['other_reminder']=do(reminder.add_reminder,{'content':'Buy printer paper','reminder_timestamp':1800000300.0},'initial_data')
 if f=='wifi_dependency':do(setting.set_wifi_status,{'on':False},'initial_data')
 def observe(scope):
  if f in ('person_message','literal_message'):
   value=do(contact.search_contacts,{'name':NAME},scope);return [{'tool':'search_contacts','arguments':{'name':NAME},'value':value}]
  if f=='reminder_retime':
   value=do(reminder.search_reminder,{'content':REMINDER},scope);return [{'tool':'search_reminder','arguments':{'content':REMINDER},'value':value}]
  return [{'tool':fun.__name__,'arguments':{},'value':do(fun,{},scope)} for fun in (setting.get_wifi_status,setting.get_low_battery_mode_status)]
 initial=observe('historical_memory')
 if c=='observed_before':observations=observe('ordinary_observation')
 if c=='unrelated':do(contact.modify_contact,{'person_id':ids['other'],'phone_number':'+12025550114'},'private_change')
 if c in ('changed','observed_after','observed_before','explicit_error'):
  if f in ('person_message','literal_message'):
   do(contact.modify_contact,{'person_id':ids['target'],'phone_number':NEW},'private_change')
   do(contact.modify_contact,{'person_id':ids['other'],'phone_number':OLD},'private_change')
   if c=='explicit_error':do(setting.set_cellular_service_status,{'on':False},'private_change')
  elif f=='reminder_retime':
   if c=='explicit_error':do(reminder.remove_reminder,{'reminder_id':ids['reminder']},'private_change')
   else:
    with replay_clock(reminder,1770000100.0):do(reminder.modify_reminder,{'reminder_id':ids['reminder'],'content':'Water the balcony plants'},'private_change')
   with replay_clock(reminder,1770000200.0,str(uuid.uuid5(uuid.NAMESPACE_URL,'R7C/reminder/replacement'))):
    ids['reminder_current']=do(reminder.add_reminder,{'content':REMINDER,'reminder_timestamp':1800000000.0},'private_change')
  elif c=='explicit_error':do(setting.set_wifi_status,{'on':True},'private_change')
  else:do(setting.set_low_battery_mode_status,{'on':True},'private_change')
 if c=='observed_after':observations=observe('ordinary_observation')
 task={
  'person_message':f'Send exactly one message to {NAME} at her current contact number. The message must be exactly "{TEXT}". If cellular service is off, you may enable it. Do not send to anyone else or change contacts, reminders, Wi-Fi, or location settings.',
  'literal_message':f'Send exactly one message to the phone number {OLD}. The message must be exactly "{TEXT}". Use that exact number, even if a contact now has a different number. If cellular service is off, you may enable it. Do not edit contacts, reminders, Wi-Fi, or location settings.',
  'reminder_retime':f'Find my current reminder whose content is exactly "{REMINDER}" and move it to POSIX timestamp {int(NEW_TIME)}. Preserve its content and location. Do not change any other reminders, contacts, messages, or settings.',
  'wifi_dependency':'Make sure Wi-Fi is enabled. You may turn off low-battery mode if necessary, but preserve the current cellular and location service settings. Do not edit contacts, reminders or messages.'}[f]
 goal={'family':f,'target_person_id':ids['target'],'literal_phone':OLD,'content':TEXT,
       'reminder_id':ids.get('reminder_current',ids['reminder']),'reminder_content':REMINDER,'new_time':NEW_TIME}
 return {'id':spec['id'],'family':f,'condition':c,'task':task,'memory':initial,'observations':observations,
         'snapshot':ctx.to_dict(serialize_console=False),'initial_state':state(ctx),'private_goal':goal,'setup_events':setup,
         'scope':'AUTHOR_CONSTRUCTED_EXTENSION_USING_PINNED_NATIVE_TOOLS_NOT_OFFICIAL_BENCHMARK'}
