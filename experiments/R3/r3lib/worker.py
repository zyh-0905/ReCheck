"""Required-only plan schema, real bounded SQL execution, deterministic rendering.
No model-generated code or SQL is executed. Offline truth never enters make_view.
"""
import math
from pilot.recheck import World,public_task
from pilot.common import is_number

def keys_for(q):
 return {0:['amount_divisor'],1:['time_bound'],2:['amount_divisor','time_bound'],3:[]}[q]

def make_view(task,memory):
 q=task['type'];keys=keys_for(q);m={}
 if q in (0,2):m['amount_divisor']=memory.get('amount_divisor')
 if q in (1,2):m['endpoint_inclusive']=memory.get('endpoint_inclusive')
 desc={}
 if q in (0,2):desc['sum_amount']='Tool returns the raw sum of ALL orders. A trusted renderer will divide it by your selected amount_divisor.'
 if q in (1,2):desc['count_until']='Tool filters rows using an integer bound, with the endpoint convention stated in evidence. Select time_bound to implement the requested inclusive cutoff. Tool returns the final filtered count. No second arithmetic adjustment is performed.'
 if q==3:desc['count_all']='Tool returns the total order count without any arguments.'
 rules='Return one JSON object containing exactly allowed_keys. Omit all other fields; do not add unused null fields. '
 if 'amount_divisor' in keys:rules+='amount_divisor must be numeric 1 or 100. '
 if 'time_bound' in keys:rules+='time_bound must be an integer. '
 if not keys:rules+='Return {}. '
 rules+='Use only the supplied evidence; do not request a probe or give a final numeric answer.'
 return {'task':public_task(task),'evidence':m,'tools':desc,'allowed_keys':keys,'instruction':rules}

def valid_plan(plan,task):
 if not isinstance(plan,dict) or set(plan)!=set(keys_for(task['type'])):return False
 if 'amount_divisor' in plan and (not is_number(plan['amount_divisor']) or plan['amount_divisor'] not in (1,100)):return False
 if 'time_bound' in plan and (type(plan['time_bound']) is not int or not task['cutoff']-1<=plan['time_bound']<=task['cutoff']+2):return False
 return True

def execute(world,task,plan):
 if not valid_plan(plan,task):return {'error':'INVALID_TOOL_PLAN'},0
 # Old environment receives a normalized internal struct, never mutating raw LLM output.
 old={'amount_divisor':plan.get('amount_divisor'),'time_bound':plan.get('time_bound')}
 return world.execute(task,old)

def render(task,plan,tool):
 if 'error' in tool:return {'total':None,'count':None}
 q=task['type'];out={'total':None,'count':None}
 if q in (0,2):out['total']=tool['sum_amount_raw']/plan['amount_divisor']
 if q in (1,2):out['count']=tool['count_before']
 if q==3:out['count']=tool['count_all']
 return out

def freshness(task,memory,modes):
 q=task['type'];use=[q in (0,2),q in (1,2)]
 vals=[memory.get('amount_divisor'),memory.get('endpoint_inclusive')]
 legal=[is_number(vals[0]) and vals[0] in (1,100),type(vals[1]) is bool]
 truth=[100 if modes[0] else 1,bool(modes[1])]
 stale=[bool(use[j] and legal[j] and vals[j]!=truth[j]) for j in range(2)]
 return {'relevant_channels':use,'channel_legal':legal,'channel_stale':stale,
         'relevant_legal':all(legal[j] for j in range(2) if use[j]),'relevant_stale':any(stale),'semantic_mismatches':sum(stale)}

def normative_plan(task,memory):
 out={};q=task['type']
 if q in (0,2):out['amount_divisor']=memory.get('amount_divisor')
 if q in (1,2):out['time_bound']=task['cutoff']+(0 if memory.get('endpoint_inclusive') else 1)
 return out

def score(answer,task,case):
 q=task['type'];gold={'total':sum(case['cents'])/100 if q in (0,2) else None,
                    'count':sum(i<=task['cutoff'] for i in range(len(case['cents']))) if q in (1,2) else len(case['cents']) if q==3 else None}
 ok=isinstance(answer,dict) and set(answer)=={'total','count'}
 if ok:
  for k,g in gold.items():
   x=answer[k]
   if g is None:ok=ok and x is None
   elif k=='count':ok=ok and type(x) is int and x==g
   else:ok=ok and is_number(x) and math.isclose(x,g,rel_tol=1e-8,abs_tol=1e-6)
 return {'success':bool(ok),'gold':gold}
