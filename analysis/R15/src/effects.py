"""Offline, tri-valued local effect checks. No native tool execution or LLM calls.
Clock mappings are inferred only from paired conversion receipts, not judge prose.
This module does not read TED labels and does not equate a local predicate with
complete task correctness. Source-collection runtime is not independently trusted.
"""
from __future__ import annotations
import ast, json, math, unicodedata, re
from datetime import datetime, timedelta, timezone
from typing import Any

REMINDERS={'add_reminder_content_and_date_and_time','add_reminder_content_and_week_delta_and_time','add_reminder_content_and_weekday_delta_and_time'}
MESSAGES={'send_message_with_phone_number_and_content','send_message_with_contact_content_cellular_off'}
TASKS=REMINDERS|MESSAGES|{'modify_contact_with_message_recency'}

def normalized(x: Any) -> str:
 if not isinstance(x,str):return ''
 return ' '.join(unicodedata.normalize('NFKC',x).replace('’',"'").replace('‘',"'").casefold().split()).strip(' \t\r\n.!?')

def reminder_content(x):
 text=normalized(x)
 if re.fullmatch(r"(?:(?:reminder|remember) to )?(?:(?:buy|buying|get|purchase|pick up) (?:some )?)?chocolate milk",text):return True
 # An unrecognized paraphrase is not a certified content failure.
 return None

def message_content(x):
 text=normalized(x)
 if "new album" in text and re.search(r"\bhow(?:'s| is| your| his| the)\b",text) and re.search(r"coming along|going|progress",text) and not re.search(r"\bnot\b|don't|do not",text):return True
 return None

def literal(x: Any) -> Any:
 if not isinstance(x,str) or len(x)>20000:return None
 try:return json.loads(x)
 except (ValueError,TypeError):pass
 try:
  tree=ast.parse(x,mode='eval')
  if sum(1 for _ in ast.walk(tree))>2500:return None
  return ast.literal_eval(tree)
 except (ValueError,TypeError,SyntaxError,MemoryError,RecursionError):return None

def finite(x: Any) -> bool:return type(x) in (int,float) and math.isfinite(x)

def combine(*values):
 if any(v is False for v in values):return False
 if all(v is True for v in values):return True
 return None

def new_rows(initial,final,id_field):
 if not isinstance(initial,list) or not isinstance(final,list):return None
 if any(not isinstance(r,dict) or not isinstance(r.get(id_field),str) for r in initial+final):return None
 # Existing duplicate message IDs occur in the source; retain rows, not a map.
 ids={r[id_field] for r in initial}
 return [r for r in final if r[id_field] not in ids]

def latest_outgoing_target(initial):
 contacts=initial.get('CONTACT');messages=initial.get('MESSAGING')
 if not isinstance(contacts,list) or not isinstance(messages,list):return None
 selfs=[r.get('person_id') for r in contacts if r.get('is_self') is True]
 if len(selfs)!=1:return None
 outgoing=[r for r in messages if r.get('sender_person_id')==selfs[0] and finite(r.get('creation_timestamp'))]
 if not outgoing:return None
 latest=max(r['creation_timestamp'] for r in outgoing)
 hits=[r for r in outgoing if r['creation_timestamp']==latest]; ids=set()
 for r in hits:
  pid=r.get('recipient_person_id')
  if pid is None:
   pp=[c.get('person_id') for c in contacts if c.get('phone_number')==r.get('recipient_phone_number')]
   if len(pp)!=1:return None
   pid=pp[0]
  ids.add(pid)
 if len(ids)!=1:return None
 pid=next(iter(ids))
 if sum(c.get('person_id')==pid for c in contacts)!=1 or pid==selfs[0]:return None
 return pid

def wall(d):
 if not isinstance(d,dict):return None
 try:
  vals=[d[k] for k in ('year','month','day')]+[d.get(k,0) for k in ('hour','minute','second')]
  if any(type(x) is not int for x in vals):return None
  return datetime(*vals,tzinfo=timezone.utc)
 except (ValueError,TypeError,KeyError):return None

def paired_calls(rec):
 for bi,b in enumerate(rec['batches']):
  for c in b['calls']:
   rs=[r for r in b['receipts'] if r.get('tool_call_id')==c.get('id')]
   if len(rs)!=1:continue
   f=c.get('function') or {}; args=literal(f.get('arguments'))
   if not isinstance(args,dict):continue
   yield bi,c['id'],f.get('name'),args,literal(rs[0].get('content'))

def clock_context(rec,sid):
 offsets=[];current=[];evidence=[]
 for bi,cid,name,args,result in paired_calls(rec):
  epoch=None;dt=None
  if name=='get_current_timestamp' and finite(result):current.append((bi,float(result)))
  if name=='datetime_info_to_timestamp' and finite(result):epoch=float(result);dt=wall(args)
  if name=='timestamp_to_datetime_info' and finite(args.get('timestamp')):epoch=float(args['timestamp']);dt=wall(result)
  if epoch is not None and dt is not None:
   diff=dt.timestamp()-epoch;rounded=round(diff/60)*60
   if abs(diff-rounded)<=1.01 and abs(rounded)<=14*3600:
    offsets.append(int(rounded));evidence.append({'call_id':cid,'offset_seconds':int(rounded),'batch':bi})
   else:offsets.append('INVALID');evidence.append({'call_id':cid,'offset_seconds':'INVALID','batch':bi})
 valid=len(set(offsets))==1 and offsets[0]!='INVALID' if offsets else False
 off=offsets[0] if valid else None
 targets=None;dates=[];anchor=current[0][1] if current else None
 reason='receipt_clock_mapping' if valid else 'missing_or_inconsistent_clock_mapping'
 if off is not None:
  if sid=='add_reminder_content_and_date_and_time': dates=[datetime(2024,3,22,17,tzinfo=timezone.utc)]
  elif anchor is not None:
   date=(datetime.fromtimestamp(anchor,timezone.utc)+timedelta(seconds=off)).date()
   if sid=='add_reminder_content_and_week_delta_and_time':dates=[datetime.combine(date+timedelta(days=1),datetime.min.time(),tzinfo=timezone.utc).replace(hour=17)]
   elif sid=='add_reminder_content_and_weekday_delta_and_time':
    delta=(4-date.weekday())%7 or 7
    dates=[datetime.combine(date+timedelta(days=delta+d),datetime.min.time(),tzinfo=timezone.utc).replace(hour=17) for d in (0,7)]
  else:reason='missing_current_timestamp_anchor'
  if dates:targets=[d.timestamp()-off for d in dates]
 return {'offset_seconds':off,'target_epochs':targets,'target_wall_dates':[x.isoformat() for x in dates], 'current_epoch':anchor,'reason':reason,'evidence':evidence}

def effect_at(sid,state,initial,clock,target):
 out={'effect':None,'content':None,'time':None,'matching_ids':[],'new_ids':[]}
 if sid in REMINDERS:
  rows=new_rows(initial.get('REMINDER'),state.get('REMINDER'),'reminder_id')
  if rows is None:return out
  out['new_ids']=[r['reminder_id'] for r in rows]
  content=[r for r in rows if reminder_content(r.get('content')) is True]
  out['content']=True if content else (False if not rows else None)
  times=clock.get('target_epochs')
  if times is not None:
   matches=[r for r in content if finite(r.get('reminder_timestamp')) and any(abs(r['reminder_timestamp']-t)<1 for t in times)]
   out['time']=bool(matches) if content else None
   out['matching_ids']=[r['reminder_id'] for r in matches]
  else:out['matching_ids']=[r['reminder_id'] for r in content]
  out['effect']=combine(out['content'],out['time'])
 elif sid in MESSAGES:
  rows=new_rows(initial.get('MESSAGING'),state.get('MESSAGING'),'message_id')
  contacts=initial.get('CONTACT')
  if rows is None or not isinstance(contacts,list):return out
  selfs=[r['person_id'] for r in contacts if r.get('is_self') is True]
  if len(selfs)!=1:return out
  target_ids=[r['person_id'] for r in contacts if normalized(r.get('name'))=='fredrik thordendal']
  if sid.endswith('cellular_off') and len(target_ids)!=1:return out
  out['new_ids']=[r['message_id'] for r in rows]
  matches=[r for r in rows if r.get('sender_person_id')==selfs[0] and message_content(r.get('content')) is True and
    (r.get('recipient_phone_number')=='+12453344098' if sid=='send_message_with_phone_number_and_content' else r.get('recipient_person_id')==target_ids[0])]
  eligible=[r for r in rows if r.get('sender_person_id')==selfs[0] and (r.get('recipient_phone_number')=='+12453344098' if sid=='send_message_with_phone_number_and_content' else r.get('recipient_person_id')==target_ids[0])]
  out['effect']=out['content']=True if matches else (None if eligible else False);out['matching_ids']=[r['message_id'] for r in matches]
 elif sid=='modify_contact_with_message_recency':
  rows=state.get('CONTACT')
  if target is None or not isinstance(rows,list):return out
  found=[r for r in rows if r.get('person_id')==target]
  if len(found)>1:return out
  out['effect']=bool(found and found[0].get('phone_number')=='+10293847563')
  out['matching_ids']=[target] if out['effect'] else []
 return out
