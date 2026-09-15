"""Native model turns joined to the unchanged R9 per-tool event timeline."""
from pathlib import Path
import copy,time
from .common import read,write,digest,no_network
from .contract import build_payload,tool_reply,ContractError
from .prompts import initial_messages
from legacy.timeline import Timeline
from legacy.scoring import grade
MAX_REQUESTS=10
MAX_TOOLS=40

def run_episode(case,spec,client,run_root,*,replay_events=None):
 root=Path(run_root);out=root/'episodes'/(spec['episode_id']+'.json')
 if out.exists():
  old=read(out)
  if old['case_sha256']!=digest(case) or any(old.get(k)!=v for k,v in spec.items()):raise ContractError('Saved episode binding changed')
  return old
 partial=root/'partial'/spec['episode_id'];partial.mkdir(parents=True,exist_ok=True)
 with no_network():
  timeline=Timeline(case,replay_events=replay_events)
 initial=initial_messages(case,spec['arm']);messages=copy.deepcopy(initial)
 used=set();turns=[];terminated=False;final_text=None;tool_count=0;tic=time.perf_counter()
 for turn in range(MAX_REQUESTS):
  logical=spec['episode_id']+f'/turn_{turn:02d}'
  write(partial/'boundary.json',{'turn':turn,'logical_id':logical,'messages':messages,'events':timeline.events,
    'turns':turns,'world':timeline.world(),'snapshot':timeline.snapshot(),'exposure':timeline.exposure(),
    'tool_count':tool_count,'checkpoint':'before_model_request'})
  payload=build_payload(client.config,messages,client.tools)
  result=client.complete(logical,payload,{'episode_id':spec['episode_id'],'phase':spec['phase'],
    'case_id':spec['case_id'],'arm':spec['arm'],'turn':turn},client.tools,used)
  v=result['validated']
  # Whole native envelope, all schemas and IDs are checked by Client before any call.
  if tool_count+len(v['calls'])>MAX_TOOLS:raise ContractError('Per-episode tool budget exceeded before dispatch')
  messages.append(copy.deepcopy(v['message']))
  rec={'turn':turn,'logical_id':logical,'request_sha256':result['request_sha256'],
   'kind':v['kind'],'assistant_message':v['message'],'decoded_calls':v['calls'],
   'tool_messages':[],'executions':[],'event_start':len(timeline.events)}
  if v['kind']=='final':
   terminated=True;final_text=v['message']['content']
  else:
   for batch_index,c in enumerate(v['calls']):
    event_start=len(timeline.events)
    # Result captures the genuine read. Timeline inserts its scheduled update immediately
    # after that read, even if the next tool is part of this same model response.
    with no_network():response=timeline.call(c['name'],c['arguments'])
    used.add(c['id']);tool_count+=1
    message=tool_reply(c['id'],response);messages.append(message);rec['tool_messages'].append(message)
    rec['executions'].append({'batch_index':batch_index,'tool_call_id':c['id'],
      'event_start':event_start,'event_end':len(timeline.events),'outer_tool_count':tool_count})
    # Preserve every completed native call for postmortem analysis of interrupted batches.
    write(partial/'tool_progress.json',{'logical_id':logical,'current_turn':rec,'messages':messages,
     'events':timeline.events,'world':timeline.world(),'snapshot':timeline.snapshot(),
     'exposure':timeline.exposure(),'tool_count':tool_count,'checkpoint':'after_native_call'})
  rec['event_end']=len(timeline.events);turns.append(rec)
  write(partial/f'turn_{turn:02d}.json',rec,once=True)
  write(partial/'boundary.json',{'turn':turn+1,'logical_id':spec['episode_id']+f'/turn_{turn+1:02d}',
   'messages':messages,'events':timeline.events,'turns':turns,'world':timeline.world(),
   'snapshot':timeline.snapshot(),'exposure':timeline.exposure(),'tool_count':tool_count,
   'checkpoint':'after_model_turn'})
  if terminated:break
 result={**spec,'case_sha256':digest(case),'public_input_sha256':digest(case['public']),
  'initial_messages':initial,'turns':turns,'events':timeline.events,'final_messages':messages,
  'after_world':timeline.world(),'final_snapshot':timeline.snapshot(),'exposure':timeline.exposure(),
  'terminated':terminated,'done_text':final_text,'stop_reason':'final' if terminated else 'request_cap',
  'score':grade(case['contract'],case['world_before'],timeline.events,timeline.world()),
  'model_calls':len(turns),'tool_calls':tool_count,
  'environment_operations':sum(e['scope']=='environment' for e in timeline.events),
  'elapsed_seconds':time.perf_counter()-tic,'evidence_kind':'NATIVE_API_LIVE_CONTINUATION_PROTOCOL'}
 write(out,result,once=True)
 return result
