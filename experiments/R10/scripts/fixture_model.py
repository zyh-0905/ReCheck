"""Local test model; never describes real LLM performance or usage."""
import re,json
from core.contract import canonical

def build_exchange(mode='rule'):
 count=[0]
 def respond(payload):
  count[0]+=1;msgs=payload['messages'];user=json.loads(msgs[1]['content']);task=user['task'];mem=user['historical_observation']
  routing='max_attempts' in task;literal=(' exactly,' in task)
  key=(re.search(r'service ([\w-]+)',task) if routing else re.search(r'lane ([\w-]+)',task))
  ident=re.search(r'(?:configuration|batch) ([\w-]+) exactly',task)
  if literal:query=('get_config' if routing else 'get_batch',{'id':ident.group(1)})
  elif routing:query=('resolve_service',{'service':key.group(1)})
  else:query=('select_batch',{'lane':key.group(1),'min_units':4})
  calls=[]
  tool_results=[m for m in msgs if m['role']=='tool']
  if mode=='cap':calls=[query]*4
  elif mode=='late_bad' and tool_results:calls=[('not_allowed',{})]
  elif mode=='prose':calls=[]
  elif not tool_results:calls=[query]
  else:
   last=json.loads(tool_results[-1]['content']);prior=[m for m in msgs if m['role']=='assistant'][-1]['tool_calls'][-1]['function']['name']
   if prior.startswith('update_'):
    if not last['ok']:calls=[query]
    else:calls=[('get_config' if routing else 'get_batch',{'id':last['value']['id']})]
   elif prior in ('get_config','get_batch') and any(c['function']['name'].startswith('update_') for m in msgs if m['role']=='assistant' for c in m.get('tool_calls',[])) and last['ok']:
    # This GET is verification after a successful update, not a recovery GET.
    field='max_attempts' if routing else 'ready_after';want=5 if routing else 1800120000
    if last['value'][field]==want:calls=[('finish_task',{'status':'completed','message':'Local software fixture only'})]
    else:calls=[query]
   else:
    value=last['value'];rec=value if literal else value['record'];a={'id':rec['id'],'max_attempts' if routing else 'ready_after':5 if routing else 1800120000,'expected_version':rec['version']}
    if not literal:
     a['expected_selection_token']=value['selection_token']
     if routing:a['service']=key.group(1)
     else:a.update(lane_query=key.group(1),min_units_query=4)
    calls=[('update_config' if routing else 'update_batch',a)]
  message={'role':'assistant','content':None if calls else 'Software fixture: no tool executed.','reasoning_content':'Software fixture, not a real model.'}
  if calls:message['tool_calls']=[{'id':f'fixture_{count[0]}_{j}','type':'function','function':{'name':n,'arguments':canonical(a)}} for j,(n,a) in enumerate(calls)]
  result={'id':f'fixture_response_{count[0]}','model':'deepseek-flash','system_fingerprint':'software_fixture_r10','choices':[{'index':0,'message':message,'finish_reason':'tool_calls' if calls else 'stop'}],'usage':{'prompt_tokens':100,'completion_tokens':20,'total_tokens':120,'completion_tokens_details':{'reasoning_tokens':5}}}
  return 200,canonical(result).encode()
 return respond,count
