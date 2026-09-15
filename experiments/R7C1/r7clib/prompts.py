
"""Frozen natural-language interface. No gold labels or fixture variant is serialized."""
import copy,json,random
from .native import tool_descriptions
ARMS=('stateless','inherited','resolve_rule')
BASE="""You control only a simulated contact book, text-message store, device settings, and reminders.
Follow the user's literal request. Historical evidence can be outdated; do not invent facts.
Only the listed tools exist. Return one JSON object per turn:
{"tool":"listed_name","arguments":{...}} for one call, or {"done":"brief completion or inability statement"} to stop.
Do not output Python, shell commands, code fences, analysis, or multiple actions.
A TOOL_RESULT is the actual result of your preceding call. Tool errors are observations; recover within the available turns when permitted.
You may stop without changing state when the task cannot be completed. Do not claim completion without performing the requested operation.
No hidden evaluator, correct answer, change label, or future state is available.
"""
RESOLVE="""Before a state-changing call whose target is a person or a reminder identified by its current description, resolve that target using a current read tool; reuse a matching read obtained during this same episode rather than querying redundantly. Historical ids and addresses are not proof of current ownership. If the user explicitly specifies a literal phone number, follow that number instead of replacing it with a contact's number. Respect all requested scope and side-effect limits."""
def initial_messages(public,arm):
 if arm not in ARMS:raise ValueError('unknown arm')
 p=copy.deepcopy(public)
 if arm=='stateless':
  p={'user_request':p['user_request']}
 instruction=BASE+('\n'+RESOLVE if arm=='resolve_rule' else '')
 instruction+='\nAvailable native tool documentation:\n'+json.dumps(tool_descriptions(),ensure_ascii=False,sort_keys=True)
 return [{'role':'system','content':instruction},{'role':'user','content':json.dumps(p,ensure_ascii=False,sort_keys=True)}]
def strict_object(text):
 def pairs(xs):
  d={}
  for k,v in xs:
   if k in d:raise ValueError('Duplicate JSON key')
   d[k]=v
  return d
 def bad(x):raise ValueError('Non-finite JSON constant')
 obj=json.loads(text,object_pairs_hook=pairs,parse_constant=bad)
 if type(obj) is not dict:raise ValueError('JSON root must be an object')
 import math
 def finite(x):
  if type(x) is float and not math.isfinite(x):raise ValueError('Non-finite number')
  if isinstance(x,dict):
   for v in x.values():finite(v)
  elif isinstance(x,list):
   for v in x:finite(v)
 finite(obj)
 return obj
def decode_action(text):
 obj=strict_object(text)
 if set(obj)=={'done'} and type(obj['done']) is str:return 'done',obj
 if set(obj)=={'tool','arguments'} and type(obj['tool']) is str and type(obj['arguments']) is dict:return 'tool',obj
 raise ValueError('Expected one tool/arguments or done object')
def episode_schedule():
 rng=random.Random(714031);out=[]
 cases=list(range(14));rng.shuffle(cases)
 for i in cases:
  arms=list(ARMS);rng.shuffle(arms)
  for a in arms:out.append({'episode_id':f'primary_c{i:02d}_{a}','phase':'primary','case_id':f'c{i:02d}','arm':a})
 reps=[(i,a) for i in (2,10) for a in ARMS];rng.shuffle(reps)
 for i,a in reps:out.append({'episode_id':f'repeat_c{i:02d}_{a}','phase':'repeat','case_id':f'c{i:02d}','arm':a})
 return out
def tool_result_message(response):
 return {'role':'user','content':'TOOL_RESULT '+json.dumps(response,ensure_ascii=False,sort_keys=True)}
