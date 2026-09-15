
"""Native ToolSandbox bridge. No arbitrary model code is evaluated.
Calls use a fixed name whitelist, JSON-only values and Python's repr of those values.
Each action executes the original decorated native function through ExecutionEnvironment.
"""
from __future__ import annotations
import ast, copy, inspect, json, time
from functools import lru_cache
import attrs
from tool_sandbox.common.execution_context import ExecutionContext, DatabaseNamespace as DB, RoleType as Role, set_current_context, get_current_context, new_context_with_attribute
from tool_sandbox.common.message_conversion import Message
from tool_sandbox.common.tool_discovery import ToolBackend
from tool_sandbox.roles.base_role import BaseRole
from tool_sandbox.roles.execution_environment import ExecutionEnvironment
from tool_sandbox.scenarios.base_scenarios import named_base_scenarios
from tool_sandbox.tools.contact import search_contacts, modify_contact
from tool_sandbox.tools.messaging import send_message_with_phone_number,search_messages
from tool_sandbox.tools.setting import get_cellular_service_status,set_cellular_service_status,get_low_battery_mode_status,set_low_battery_mode_status,get_wifi_status,set_wifi_status
from tool_sandbox.tools.reminder import search_reminder,modify_reminder,add_reminder
FUNCTIONS={f.__name__:f for f in (
 search_contacts,send_message_with_phone_number,get_cellular_service_status,
 set_cellular_service_status,search_messages,search_reminder,modify_reminder,
 get_low_battery_mode_status,set_low_battery_mode_status,get_wifi_status,set_wifi_status)}
ADMIN={f.__name__:f for f in (modify_contact,set_cellular_service_status,modify_reminder,add_reminder,set_low_battery_mode_status,set_wifi_status)}
WORLDS=(DB.CONTACT,DB.MESSAGING,DB.REMINDER,DB.SETTING)

@lru_cache(None)
def base_snapshot():
 return named_base_scenarios(ToolBackend.DEFAULT)['base'].starting_context.to_dict(serialize_console=False)

def jcopy(x):return json.loads(json.dumps(x,ensure_ascii=False,allow_nan=False))
def world_of(ctx):
 return {n.name.lower():sorted(jcopy(ctx.get_database(n).to_dicts()),key=lambda r:json.dumps(r,sort_keys=True)) for n in WORLDS}

class NativeSession:
 def __init__(self,snapshot=None):
  raw=copy.deepcopy(snapshot if snapshot is not None else base_snapshot())
  if raw.get('interactive_console') is not None:raise ValueError('Serialized executable consoles are forbidden')
  self.context=ExecutionContext.from_dict(raw)
  self.context.tool_allow_list=list(FUNCTIONS)+['end_conversation']
  self.events=[];set_current_context(self.context);self.env=ExecutionEnvironment()
  # Rebuild only the trusted callable namespace; do not replay historical messages.
  # Native respond() would consume stale trace metadata when restoring a non-empty history.
  self.context.interactive_console.locals.update(FUNCTIONS)
 def world(self):return world_of(self.context)
 def snapshot(self):return jcopy(self.context.to_dict(serialize_console=False))
 def call(self,name,args,scope='agent'):
  set_current_context(self.context);before=self.world();tic=time.perf_counter()
  try:
   if name not in FUNCTIONS:raise ValueError('Tool not in allowlist')
   if type(args) is not dict or any(type(k) is not str for k in args):raise ValueError('Arguments must be an object')
   clean=jcopy(args)
   if len(json.dumps(clean))>12000:raise ValueError('Arguments too large')
   inspect.signature(FUNCTIONS[name]).bind(**clean)
  except Exception as exc:
   result={'ok':False,'value':None,'error':type(exc).__name__+': '+str(exc)}
   self.events.append({'scope':scope,'tool':str(name),'arguments':args if type(args) is dict and all(type(v) in (str,int,float,bool,type(None),dict,list) for v in args.values()) else {},
      'response':result,'before_world':before,'after_world':before,'elapsed_seconds':time.perf_counter()-tic,'rejected_before_native':True})
   return result
  code=f'print(repr({name}(**{clean!r})))'
  BaseRole.add_messages([Message(sender=Role.AGENT,recipient=Role.EXECUTION_ENVIRONMENT,content=code)])
  self.env.respond()
  self.context=get_current_context()
  msg=BaseRole.get_messages()[-1]
  if msg.sender!=Role.EXECUTION_ENVIRONMENT:raise RuntimeError('Native response missing')
  result={'ok':msg.tool_call_exception is None,'value':None,'error':None}
  if msg.tool_call_exception:result['error']=msg.tool_call_exception
  else:result['value']=ast.literal_eval(msg.content)
  result=jcopy(result)
  self.events.append({'scope':scope,'tool':name,'arguments':clean,'response':result,
       'before_world':before,'after_world':self.world(),'elapsed_seconds':time.perf_counter()-tic,
       'native_message':jcopy(attrs.asdict(msg)),'rejected_before_native':False})
  return result
 def admin(self,name,args):
  if name not in ADMIN:raise ValueError('Invalid fixture operation')
  set_current_context(self.context)
  BaseRole.add_messages([Message(sender=Role.SYSTEM,recipient=Role.SYSTEM,content='Private fixture setup',visible_to=[Role.SYSTEM])])
  with new_context_with_attribute(trace_tool=False):result=ADMIN[name](**args)
  self.context=get_current_context()
  return result

def tool_descriptions():
 return [{'name':name,'signature':str(inspect.signature(f)),'description':inspect.getdoc(f)}
         for name,f in sorted(FUNCTIONS.items())]
