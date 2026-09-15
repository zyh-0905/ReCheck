"""Pinned ToolSandbox native-integration fixtures, not an LLM benchmark run.

Upstream functions, decorators, Polars storage, execution environment and evaluator
are used unchanged. Policies access only a query interface, cached evidence and
explicit tool observations. Fixture changes / gold evaluation are separate.
"""
from __future__ import annotations
import ast,copy,csv,hashlib,inspect,json,time
from collections import Counter
from functools import lru_cache
from pathlib import Path
from typing import Any
import attrs
from tool_sandbox.common.execution_context import DatabaseNamespace as DB, ExecutionContext, RoleType as Role, get_current_context, set_current_context, new_context_with_attribute
from tool_sandbox.common.message_conversion import Message
from tool_sandbox.common.tool_discovery import ToolBackend
from tool_sandbox.common.utils import deterministic_uuid
from tool_sandbox.roles.base_role import BaseRole
from tool_sandbox.roles.execution_environment import ExecutionEnvironment
from tool_sandbox.scenarios.base_scenarios import named_base_scenarios
from tool_sandbox.scenarios.single_tool_call_scenarios import named_single_tool_call_scenarios
from tool_sandbox.scenarios.multiple_tool_call_scenarios import named_multiple_tool_call_scenarios
from tool_sandbox.tools.contact import search_contacts, modify_contact
from tool_sandbox.tools.messaging import search_messages, send_message_with_phone_number
from tool_sandbox.tools.setting import get_cellular_service_status, set_cellular_service_status, set_wifi_status, set_low_battery_mode_status
from tool_sandbox.common.evaluation import Evaluation
from score import assess

TARGET='Fredrik Thordendal'
TARGET_ID=deterministic_uuid(payload=TARGET)
OTHER_ID=deterministic_uuid(payload='John Petrucci')
OLD_PHONE='+12453344098'
NEW_PHONE='+12025550119'
CONTENT="How's the new album coming along"
METHODS=('cached_reactive','query_on_error','always_resolve','reuse_observed_then_resolve')
REGIMES=('stable','unrelated','moved','reassigned')
TIMINGS=('none','pre_change','post_change')
OFFICIAL_CASES=('wifi_off','send_message_with_phone_number_and_content','turn_on_wifi_low_battery_mode','send_message_with_contact_content_cellular_off')
POLICY_TOOLS={f.__name__:f for f in (search_contacts,send_message_with_phone_number,search_messages,get_cellular_service_status,set_cellular_service_status)}
WALKTHROUGH_TOOLS={**POLICY_TOOLS,**{f.__name__:f for f in (set_wifi_status,set_low_battery_mode_status)}}

def capabilities():
 return {'native_context':ExecutionContext.__module__=='tool_sandbox.common.execution_context',
         'native_execution':ExecutionEnvironment.__module__=='tool_sandbox.roles.execution_environment',
         'native_evaluation':Evaluation.__module__=='tool_sandbox.common.evaluation'}

def jbytes(obj):return (json.dumps(obj,ensure_ascii=False,sort_keys=True,indent=2,allow_nan=False)+'\n').encode()
def sha_obj(obj):return hashlib.sha256(jbytes(obj)).hexdigest()

def select_exact_contact(rows,name):
 matches=[r for r in rows if r.get('name')==name]
 if len(matches)!=1:raise ValueError('Exact target name is absent or ambiguous')
 return copy.deepcopy(matches[0])

@lru_cache(None)
def definitions():
 return {'base':named_base_scenarios(ToolBackend.DEFAULT),
         'single':named_single_tool_call_scenarios(ToolBackend.DEFAULT),
         'multi':named_multiple_tool_call_scenarios(ToolBackend.DEFAULT)}

class NativeSession:
 def __init__(self,scenario=None,allowed=None):
  self.allowed=POLICY_TOOLS if allowed is None else allowed
  self.events=[]
  base=scenario or definitions()['base']['base']
  # Local trusted state serialization; no untrusted pickle is loaded.
  ctx=ExecutionContext.from_dict(base.starting_context.to_dict(serialize_console=False))
  if scenario is None:ctx.tool_allow_list=list(self.allowed)+['end_conversation']
  set_current_context(ctx);self.env=ExecutionEnvironment()
  last=ctx.max_sandbox_message_index
  rows=ctx.get_database(DB.SANDBOX,get_all_history_snapshots=True,drop_sandbox_message_index=False).to_dicts()
  for row in rows:
   if row['sender']==Role.SYSTEM and row['recipient']==Role.EXECUTION_ENVIRONMENT:
    self.env.respond(ending_index=row['sandbox_message_index'])
  assert self.ctx.max_sandbox_message_index==last
 @property
 def ctx(self):return get_current_context()
 def rows(self,db):return copy.deepcopy(self.ctx.get_database(db).to_dicts())
 def snapshot(self):return self.ctx.to_dict(serialize_console=False)
 def call(self,name,args,scope='runtime'):
  if name not in self.allowed:raise ValueError('Tool is outside explicitly allowed native interface')
  if not isinstance(args,dict) or any(not isinstance(k,str) for k in args):raise ValueError('Invalid arguments')
  clean=json.loads(json.dumps(args,allow_nan=False))
  inspect.signature(self.allowed[name]).bind(**clean)
  code=f'print(repr({name}(**{clean!r})))'
  BaseRole.add_messages([Message(sender=Role.AGENT,recipient=Role.EXECUTION_ENVIRONMENT,content=code)])
  started=time.perf_counter();self.env.respond();elapsed=time.perf_counter()-started
  message=BaseRole.get_messages()[-1]
  if message.sender!=Role.EXECUTION_ENVIRONMENT:raise RuntimeError('Missing native tool response')
  response={'ok':message.tool_call_exception is None,'error':message.tool_call_exception,
            'value':None if message.tool_call_exception else ast.literal_eval(message.content)}
  self.events.append({'scope':scope,'tool':name,'arguments':clean,'response':copy.deepcopy(response),
                      'native_response':attrs.asdict(message),'elapsed_seconds':elapsed,
                      'snapshot_index':self.ctx.max_sandbox_message_index})
  return response
 def admin(self,name,args):
  # Fixture-only changes never passed to policy input. Preserve native snapshots.
  if name not in ('modify_contact','set_cellular_service_status'):raise ValueError(name)
  BaseRole.add_messages([Message(sender=Role.SYSTEM,recipient=Role.SYSTEM,
      content='Private controlled fixture event',visible_to=[Role.SYSTEM])])
  f=modify_contact if name=='modify_contact' else set_cellular_service_status
  with new_context_with_attribute(trace_tool=False):f(**args)
  self.events.append({'scope':'fixture_admin','tool':name,'arguments':args,'snapshot_index':self.ctx.max_sandbox_message_index})
 def finish(self,text):
  BaseRole.add_messages([Message(sender=Role.AGENT,recipient=Role.USER,content=text),
    Message(sender=Role.USER,recipient=Role.AGENT,content='Done.',conversation_active=False)])


def run_original(name):
 all_defs={**definitions()['single'],**definitions()['multi']}
 scenario=all_defs[name]
 session=NativeSession(scenario,allowed={k:v for k,v in WALKTHROUGH_TOOLS.items() if k in scenario.starting_context.tool_allow_list})
 if name=='wifi_off':
  assert session.call('set_wifi_status',{'on':False})['ok'];final='Wifi is turned off'
 elif name=='turn_on_wifi_low_battery_mode':
  assert session.call('set_low_battery_mode_status',{'on':False})['ok']
  assert session.call('set_wifi_status',{'on':True})['ok'];final='Wifi has been turned on.'
 elif name=='send_message_with_phone_number_and_content':
  assert session.call('send_message_with_phone_number',{'phone_number':OLD_PHONE,'content':CONTENT})['ok']
  final=f'Your message to {OLD_PHONE} has been sent saying: {CONTENT}'
 elif name=='send_message_with_contact_content_cellular_off':
  assert session.call('set_cellular_service_status',{'on':True})['ok']
  row=select_exact_contact(session.call('search_contacts',{'name':TARGET})['value'],TARGET)
  assert session.call('send_message_with_phone_number',{'phone_number':row['phone_number'],'content':CONTENT})['ok']
  final=f'Your message to {TARGET} has been sent saying: {CONTENT}'
 else:raise ValueError(name)
 session.finish(final)
 evaluation=scenario.evaluation.evaluate(session.ctx,max_turn_count=scenario.max_messages)
 return {'evidence_kind':'SCRIPTED_ORIGINAL_SCENARIO_INTEGRATION_NOT_LLM_RESULT','scenario':name,
         'official_evaluation':attrs.asdict(evaluation),'events':session.events,'state':session.snapshot(),
         'uses_native_scenario_state':True,'uses_native_execution_environment':True,'uses_native_evaluation':True}


def policy(method,public_task,cached,feedback,call):
 """No fixture label, time of drift, current DB, gold ID or result is an input."""
 if method not in METHODS:raise ValueError(method)
 name=public_task['target_name']; phone=cached['phone_number']
 def resolve():
  r=call('search_contacts',{'name':name})
  if not r['ok']:raise RuntimeError('Contact query failed')
  return select_exact_contact(r['value'],name)['phone_number']
 if method=='always_resolve':phone=resolve()
 elif method=='reuse_observed_then_resolve':
  matching=[item for item in feedback if item['tool']=='search_contacts' and item['arguments']=={'name':name} and item['response']['ok']]
  phone=select_exact_contact(matching[-1]['response']['value'],name)['phone_number'] if matching else resolve()
 result=call('send_message_with_phone_number',{'phone_number':phone,'content':public_task['content']})
 if not result['ok'] and 'ConnectionError' in result['error']:
  if method=='query_on_error':phone=resolve()
  enabled=call('set_cellular_service_status',{'on':True})
  if enabled['ok']:result=call('send_message_with_phone_number',{'phone_number':phone,'content':public_task['content']})
 return {'reported_sent':result['ok'],'returned_id':result['value'] if result['ok'] else None,'used_phone':phone,'error':result['error']}


def run_fixture(regime,timing,method,posthoc=False):
 if regime not in REGIMES+('cellular_off','combined'):raise ValueError(regime)
 if timing not in TIMINGS:raise ValueError(timing)
 session=NativeSession()
 initial=select_exact_contact(session.call('search_contacts',{'name':TARGET},scope='startup_calibration')['value'],TARGET)
 session.call('get_cellular_service_status',{},scope='startup_calibration')
 cached={'name':TARGET,'phone_number':initial['phone_number']};feedback=[]
 def task_lookup():
  result=session.call('search_contacts',{'name':TARGET},scope='ordinary_task_observation')
  # Same explicit observation is provided to each policy; no private fixture metadata.
  feedback.append({'tool':'search_contacts','arguments':{'name':TARGET},'response':copy.deepcopy(result)})
 if timing=='pre_change':task_lookup()
 if regime=='unrelated':session.admin('modify_contact',{'person_id':OTHER_ID,'phone_number':NEW_PHONE})
 if regime in ('moved','reassigned','combined'):
  session.admin('modify_contact',{'person_id':TARGET_ID,'phone_number':NEW_PHONE})
 if regime in ('reassigned','combined'):session.admin('modify_contact',{'person_id':OTHER_ID,'phone_number':OLD_PHONE})
 if regime in ('cellular_off','combined'):session.admin('set_cellular_service_status',{'on':False})
 if timing=='post_change':task_lookup()
 public_task={'target_name':TARGET,'content':CONTENT,'request':f'Send {TARGET} the following message at his current contact number: {CONTENT}'}
 input_record={'public_task':public_task,'cached':cached,'observations':copy.deepcopy(feedback)}
 before=session.rows(DB.MESSAGING); before_state=session.snapshot()
 before_world={str(n):session.rows(n) for n in (DB.CONTACT,DB.SETTING,DB.REMINDER)}
 started=time.perf_counter();presult=policy(method,public_task,copy.deepcopy(cached),copy.deepcopy(feedback),session.call);elapsed=time.perf_counter()-started
 if posthoc:session.call('search_contacts',{'name':TARGET},scope='posthoc_diagnostic')
 after=session.rows(DB.MESSAGING)
 target_now=select_exact_contact(session.rows(DB.CONTACT),TARGET)
 result=assess(before,after,target_id=initial['person_id'],target_phone=target_now['phone_number'],content=CONTENT)
 newrows=[r for r in after if r['message_id'] not in {x['message_id'] for x in before}]
 # State mutations outside fixture setup and messaging are not permitted except cellular repair.
 result['contacts_unchanged_by_policy']=session.rows(DB.CONTACT)==before_world[str(DB.CONTACT)]
 result['reminders_unchanged_by_policy']=session.rows(DB.REMINDER)==before_world[str(DB.REMINDER)]
 result['settings_only_cellular_changed_by_policy']=[{k:v for k,v in row.items() if k!='cellular'} for row in session.rows(DB.SETTING)]==[{k:v for k,v in row.items() if k!='cellular'} for row in before_world[str(DB.SETTING)]]
 result['safe_success']=result['safe_success'] and result['contacts_unchanged_by_policy'] and result['reminders_unchanged_by_policy'] and result['settings_only_cellular_changed_by_policy']
 counts=Counter(e['scope'] for e in session.events)
 return {'evidence_kind':'NATIVE_TOOL_CONTROLLED_EXTENSION_NOT_LLM_OR_OFFICIAL_BENCHMARK_SCORE',
         'regime':regime,'observation_timing':timing,'method':method,'public_input':input_record,
         'public_input_sha256':sha_obj(input_record),'policy_return':presult,'score':result,
         'recipient_ids':[r['recipient_person_id'] for r in newrows],'recipient_phones':[r['recipient_phone_number'] for r in newrows],
         'runtime_calls':counts['runtime'],'ordinary_observation_calls':counts['ordinary_task_observation'],
         'startup_calls':counts['startup_calibration'],'policy_elapsed_seconds':elapsed,
         'events':session.events,'before_policy_snapshot':before_state,'after_policy_snapshot':session.snapshot()}


def check_snapshot_roundtrip():
 s=NativeSession();original_ctx=s.ctx;raw=s.snapshot();clone=ExecutionContext.from_dict(copy.deepcopy(raw))
 if clone.to_dict(serialize_console=False)!=raw:return False
 set_current_context(clone)
 with new_context_with_attribute(trace_tool=False):modify_contact(person_id=TARGET_ID,phone_number=NEW_PHONE)
 return original_ctx.to_dict(serialize_console=False)==raw and raw==safely_initial_snapshot(raw) and clone.to_dict(serialize_console=False)!=raw

def safely_initial_snapshot(raw):
 # Reconstruct original serialized snapshot rather than reading the modified current context.
 return ExecutionContext.from_dict(copy.deepcopy(raw)).to_dict(serialize_console=False)

def check_invalid_call(name,args):return NativeSession().call(name,args)

def run_explicit_phone_boundary():
 s=NativeSession();before=s.rows(DB.MESSAGING)
 s.admin('modify_contact',{'person_id':TARGET_ID,'phone_number':NEW_PHONE})
 s.admin('modify_contact',{'person_id':OTHER_ID,'phone_number':OLD_PHONE})
 r=s.call('send_message_with_phone_number',{'phone_number':OLD_PHONE,'content':CONTENT})
 after=s.rows(DB.MESSAGING)
 return {'evidence_kind':'GOAL_SEMANTICS_BOUNDARY_NOT_METHOD_RESULT','tool_success':r['ok'],
    'phone_goal':assess(before,after,target_id=TARGET_ID,target_phone=OLD_PHONE,content=CONTENT,goal_kind='phone'),
    'person_goal':assess(before,after,target_id=TARGET_ID,target_phone=NEW_PHONE,content=CONTENT),
    'events':s.events,'state':s.snapshot()}


def scientific_projection(r):
 return {k:r[k] for k in ('regime','observation_timing','method','public_input_sha256','recipient_ids','recipient_phones','runtime_calls','ordinary_observation_calls','startup_calls')} | {
   'score':{k:v for k,v in r['score'].items() if k not in ('correct_ids','wrong_ids')},
   'policy_return':{k:v for k,v in r['policy_return'].items() if k!='returned_id'},
   'event_actions':[{'scope':e['scope'],'tool':e['tool'],'arguments':e['arguments'],
       'ok':e.get('response',{}).get('ok'),'error':e.get('response',{}).get('error')} for e in r['events']]}


def run_all(out):
 originals=out/'original_walkthroughs';originals.mkdir()
 for name in OFFICIAL_CASES:
  r=run_original(name);(originals/f'{name}.json').write_bytes(jbytes(r))
  if abs(r['official_evaluation']['similarity']-1)>1e-12:raise RuntimeError('Original scripted walkthrough not accepted: '+name)
 results=out/'controlled_extensions';results.mkdir();rows=[];projected=[]
 for regime in REGIMES:
  for timing in TIMINGS:
   for method in METHODS:
    r=run_fixture(regime,timing,method)
    fname=f'{regime}__{timing}__{method}.json'
    (results/fname).write_bytes(jbytes(r));projected.append(scientific_projection(r))
    rows.append({k:r[k] for k in ('regime','observation_timing','method','runtime_calls','ordinary_observation_calls','startup_calls')} | {k:r['score'][k] for k in ('safe_success','target_reached','wrong_writes','new_writes')})
 with (out/'per_fixture.csv').open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
 boundaries=[]
 for regime in ('cellular_off','combined'):
  for method in METHODS:
   r=run_fixture(regime,'none',method);boundaries.append(r)
 r=run_fixture('reassigned','none','cached_reactive',posthoc=True);boundaries.append(r)
 (out/'boundaries.json').write_bytes(jbytes({'runs':boundaries,'explicit_phone':run_explicit_phone_boundary(),'snapshot_roundtrip':check_snapshot_roundtrip()}))
 summary={'label':'NATIVE_INTEGRATION_AND_CONSTRUCTED_MECHANISMS_NOT_LLM_BENCHMARK',
  'source_commit':'c8571d7854316d2e1c5f288e59fe1e34e53f6dd1','original_walkthroughs':4,
  'constructed_cases':12,'policy_comparisons':48,'boundary_runs':9,'new_llm_calls':0,
  'by_method':{m:{'safe_successes':sum(r['safe_success'] for r in rows if r['method']==m),'denominator':12,
                   'runtime_calls':sum(r['runtime_calls'] for r in rows if r['method']==m),
                   'ordinary_observation_calls':sum(r['ordinary_observation_calls'] for r in rows if r['method']==m),
                   'startup_calls':sum(r['startup_calls'] for r in rows if r['method']==m)} for m in METHODS},
  'warning':'Deterministic policies and hand-constructed perturbations; counts are fixture coverage, not inferential success rates. Underlying settings are not shared with policies.'}
 (out/'summary.json').write_bytes(jbytes(summary));(out/'scientific_projection.json').write_bytes(jbytes(projected))
 print(json.dumps(summary,ensure_ascii=False,indent=2))
