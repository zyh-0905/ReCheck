from contextlib import contextmanager
from datetime import datetime
from types import SimpleNamespace
from uuid import UUID
import math
from .scoring import added
@contextmanager
def replay_nondeterminism(e):
 import tool_sandbox.tools.messaging as mm
 import tool_sandbox.tools.reminder as rm
 restore=[]
 if e.get('response',{}).get('ok'):
  ts=None;mod=None
  if e['tool']=='send_message_with_phone_number':
   identifier=e['response']['value'];UUID(identifier)
   rows=added(e['before_world']['messaging'],e['after_world']['messaging'])
   row=next(x for x in rows if x['message_id']==identifier)
   ts=row['creation_timestamp'];mod=mm
   restore.append((mm,'uuid4',mm.uuid4));mm.uuid4=lambda:UUID(identifier)
  elif e['tool']=='modify_reminder':
   row=next(x for x in e['after_world']['reminder'] if x['reminder_id']==e['arguments']['reminder_id'])
   ts=row['creation_timestamp'];mod=rm
  if mod is not None:
   if type(ts) not in (int,float) or not math.isfinite(ts):raise ValueError('Invalid clock fixture')
   class Clock(datetime):
    @classmethod
    def now(cls,tz=None):return datetime.fromtimestamp(ts,tz)
   restore.append((mod,'datetime',mod.datetime));mod.datetime=SimpleNamespace(datetime=Clock)
 try:yield
 finally:
  for mod,n,x in reversed(restore):setattr(mod,n,x)

