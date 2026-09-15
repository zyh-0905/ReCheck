
"""Multi-turn model diagnosis. Every episode starts at a frozen native snapshot.
No score, private goal, fixture labels, future state or script oracle enters model inputs.
"""
import copy,json,time
from pathlib import Path
from .native import NativeSession
from .goals import evaluate
from .prompts import initial_messages,decode_action,tool_result_message,strict_object
from pilot.common import write_json,read_json,digest
def run_episode(case,spec,client,run_root):
 root=Path(run_root);out=root/'episodes'/(spec['episode_id']+'.json')
 if out.exists():return read_json(out)
 partial=root/'partial'/spec['episode_id'];partial.mkdir(parents=True,exist_ok=True)
 s=NativeSession(case['snapshot']);messages=initial_messages(case['public'],spec['arm'])
 turns=[];terminated=False;done_text=None;tic=time.perf_counter()
 for n in range(8):
  logical=spec['episode_id']+f'/turn_{n:02d}'
  # Persist the pre-call boundary even when the transport pauses.
  write_json(partial/'boundary.json',{'turn':n,'logical_id':logical,'messages':messages,'world':s.world(),'events':s.events,'turns':turns,'snapshot':s.snapshot()})
  call=client.complete(logical,messages,meta={'episode_id':spec['episode_id'],'phase':spec['phase'],'turn':n})
  text=call['text'];strict_object(text) # syntax is a global pause gate in the transport
  turn={'turn':n,'logical_id':logical,'request_sha256':call['request_sha256'],'response_text':text}
  messages.append({'role':'assistant','content':text})
  try:kind,action=decode_action(text)
  except ValueError:
   response={'ok':False,'value':None,'error':'ACTION_SCHEMA: return exactly tool/arguments or done'}
   turn.update(kind='schema_error',observation=response)
   messages.append(tool_result_message(response))
  else:
   turn.update(kind=kind,action=action)
   if kind=='done':
    terminated=True;done_text=action['done'];turns.append(turn);write_json(partial/f'{n:02d}.json',turn);break
   response=s.call(action['tool'],action['arguments'])
   turn.update(observation=response,event_index=len(s.events)-1)
   messages.append(tool_result_message(response))
  turns.append(turn);write_json(partial/f'{n:02d}.json',turn)
 result={**spec,'case_sha256':digest(case),'public_input_sha256':digest(case['public']),
   'initial_messages':initial_messages(case['public'],spec['arm']),'turns':turns,
   'events':s.events,'after_world':s.world(),'final_snapshot':s.snapshot(),
   'terminated':terminated,'done_text':done_text,'stop_reason':'done' if terminated else 'turn_cap',
   'score':evaluate(case['world_before'],s.world(),case['goal'],s.events),
   'model_calls':len(turns),'tool_calls':len(s.events),'elapsed_seconds':time.perf_counter()-tic}
 write_json(out,result)
 return result
