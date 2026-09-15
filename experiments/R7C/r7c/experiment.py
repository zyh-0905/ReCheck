"""Bounded tool loop. Policy inputs are constructed only by actor.messages."""
import copy,random
from pathlib import Path
from .core import MAX_STEPS,METHODS,action,digest,write,read
from .actor import messages
from .native import Session
from .score import grade
from .journal import Paused

def schedule(cases,seed=701301):
 out=[];rng=random.Random(seed);ids=list(range(len(cases)));rng.shuffle(ids)
 for position,i in enumerate(ids):
  arms=list(METHODS);offset=position%3;arms=arms[offset:]+arms[:offset]
  out.extend((cases[i]['id'],m) for m in arms)
 return out

def episode(case,method,client,output=None,replay_events=None):
 s=Session(case);history=[];steps=[];finished=False;reason='decision_cap';summary=''
 def record():
  r={'case_id':case['id'],'family':case['family'],'condition':case['condition'],'method':method,
     'case_sha256':digest(case),'steps':copy.deepcopy(steps),'events':copy.deepcopy(s.events),
     'final_state':s.state(),'finished':finished,'termination':reason,'summary':summary,
     'score':grade(case,s.events,s.state(),finished)}
  if output:write(output,r)
  return r
 for n in range(MAX_STEPS):
  ident=f'{case["id"]}/{method}/{n}';meta={'case_id':case['id'],'method':method,'step':n}
  try:obj,call=client.complete(ident,messages(case,method,history),meta)
  except Paused:
   reason='paused';record();raise
  step={'logical_id':ident,'payload_sha256':call['payload_sha256'],'model_object':obj}
  try:a=action(obj)
  except (ValueError,TypeError):
   step['contract_error']=True;steps.append(step);reason='model_contract_error';return record()
  if a['action']=='finish':
   finished=True;reason='model_finish';summary=a['summary'];steps.append(step);return record()
  event_ref=replay_events[len(s.events)] if replay_events is not None and len(s.events)<len(replay_events) else None
  observation=s.call(a['name'],a['arguments'],replay_event=event_ref)
  step['observation']=observation;steps.append(step)
  history.append({'action':a,'observation':observation})
  record()
 return record()

class Replay:
 def __init__(self,records,protocol):self.records=records;self.protocol=protocol;self.used=[];self.expected=[]
 def complete(self,logical_id,msgs,meta):
  from .journal import payload,validate_response
  self.expected.append(logical_id)
  r=self.records.get(logical_id)
  if r is None:raise Paused('No saved response; partial episode')
  if r['payload']!=payload(msgs,self.protocol) or r['metadata']!=meta:raise ValueError('Replay request mismatch: '+logical_id)
  x,_=validate_response(r['response'],None);self.used.append(logical_id);return x,r
