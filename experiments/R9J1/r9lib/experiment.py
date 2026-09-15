"""On-policy continuation after real native feedback, including scheduled changes."""
from pathlib import Path
import time
from pilot.common import read_json,write_json,digest
from .timeline import Timeline
from .scoring import grade
from .prompts import initial_messages,decode_action,tool_result_message,strict_object
SCHEMA_ERROR={'ok':False,'value':None,'error':'ACTION_SCHEMA: return exactly tool/arguments or done'}
def run_episode(case,spec,client,run_root):
 root=Path(run_root);out=root/'episodes'/(spec['episode_id']+'.json')
 if out.exists():return read_json(out)
 partial=root/'partial'/spec['episode_id'];partial.mkdir(parents=True,exist_ok=True)
 t=Timeline(case);messages=initial_messages(case['public'],spec['arm']);turns=[];terminated=False;done_text=None;tic=time.perf_counter()
 for n in range(10):
  logical=spec['episode_id']+f'/turn_{n:02d}'
  write_json(partial/'boundary.json',{'turn':n,'logical_id':logical,'messages':messages,'world':t.world(),
   'events':t.events,'turns':turns,'snapshot':t.snapshot(),'exposure':t.exposure()})
  call=client.complete(logical,messages,meta={'episode_id':spec['episode_id'],'phase':spec['phase'],'turn':n})
  text=call['text'];strict_object(text)
  turn={'turn':n,'logical_id':logical,'request_sha256':call['request_sha256'],'response_text':text}
  messages.append({'role':'assistant','content':text})
  try:kind,action=decode_action(text)
  except ValueError:
   turn.update(kind='schema_error',observation=SCHEMA_ERROR);messages.append(tool_result_message(SCHEMA_ERROR))
  else:
   turn.update(kind=kind,action=action)
   if kind=='done':
    terminated=True;done_text=action['done'];turns.append(turn);write_json(partial/f'{n:02d}.json',turn);break
   start=len(t.events);r=t.call(action['tool'],action['arguments'])
   turn.update(observation=r,event_start=start,event_end=len(t.events));messages.append(tool_result_message(r))
  turns.append(turn);write_json(partial/f'{n:02d}.json',turn)
 result={**spec,'case_sha256':digest(case),'public_input_sha256':digest(case['public']),
  'initial_messages':initial_messages(case['public'],spec['arm']),'turns':turns,'events':t.events,
  'after_world':t.world(),'final_snapshot':t.snapshot(),'exposure':t.exposure(),'terminated':terminated,
  'done_text':done_text,'stop_reason':'done' if terminated else 'turn_cap',
  'score':grade(case['contract'],case['world_before'],t.events,t.world()),'model_calls':len(turns),
  'tool_calls':sum(e['scope']=='agent' for e in t.events),'environment_operations':sum(e['scope']=='environment' for e in t.events),
  'elapsed_seconds':time.perf_counter()-tic}
 write_json(out,result);return result
