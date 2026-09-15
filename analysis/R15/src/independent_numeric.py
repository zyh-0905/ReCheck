"""Independent numeric checks: no import of R14 parser or R15 effect predicates."""
from __future__ import annotations
import ast,calendar,collections,json,math,zipfile
from pathlib import Path
from datetime import datetime,timedelta,timezone

def calendar_violation(anchor, actual, offset, kind):
 c=datetime.fromtimestamp(anchor,timezone.utc)+timedelta(seconds=offset)
 a=datetime.fromtimestamp(actual,timezone.utc)+timedelta(seconds=offset)
 if kind=='tomorrow':return a.date()!=c.date()+timedelta(days=1)
 # More permissive than the main filter: allow any non-past Friday and ignore hour.
 if kind=='friday':return a.date()<c.date() or a.weekday()!=4
 return None

def parsed(x):
 if not isinstance(x,str) or len(x)>20000:return None
 try:return json.loads(x)
 except ValueError:
  try:return ast.literal_eval(x)
  except (SyntaxError,ValueError,TypeError,RecursionError):return None

def unix(d):
 if not isinstance(d,dict):return None
 try:
  x=[d[k] for k in ['year','month','day']]+[d.get(k,0) for k in ['hour','minute','second']]
  if any(type(v) is not int for v in x):return None
  # Validate calendar before using the separate timegm implementation.
  datetime(*x)
  return calendar.timegm(tuple(x)+(0,0,0))
 except (ValueError,KeyError,TypeError):return None

def check_raw(s,annotation):
 flat=[m for turn in s['trajectory'] for m in turn]
 calls={}
 for m in flat:
  for c in m.get('tool_calls') or []:
   if c['id'] in calls:raise ValueError('duplicate native call id')
   calls[c['id']]=c['function']
 receipts=[m for m in flat if m.get('role')=='tool']; receiptids=[m.get('tool_call_id') for m in receipts]
 assert len(receiptids)==len(set(receiptids))
 now=[];offsets=[];native_adds=[]
 for m in receipts:
  f=calls.get(m.get('tool_call_id'))
  if not f:continue
  name=f['name'];a=parsed(f['arguments']);v=parsed(m.get('content'))
  if name=='add_reminder':native_adds.append({'id':m.get('tool_call_id'),'arguments':a,'content':m.get('content')})
  if name=='get_current_timestamp' and type(v) in (int,float):now.append(v)
  left=None;right=None
  if name=='datetime_info_to_timestamp' and type(v) in (int,float):left=unix(a);right=v
  if name=='timestamp_to_datetime_info' and type(a.get('timestamp')) in (int,float):left=unix(v);right=a['timestamp']
  if left is not None and right is not None:
   delta=left-right;n=round(delta/60)*60
   assert abs(delta-n)<=1.01 and abs(n)<=50400
   offsets.append(n)
 initial=None;last=None
 for m in flat:
  for k in ['user_details','tool_details']:
   dd=(m.get(k) or {}).get('database_update',{})
   if 'REMINDER' in dd:
    if initial is None:initial=dd['REMINDER']
    last=dd['REMINDER']
 assert initial is not None and last is not None
 oldids={r['reminder_id'] for r in initial};new=[r for r in last if r['reminder_id'] not in oldids]
 assert (s.get('metrics') or {})['progress_rates'][-1]==1
 assert all(v['is_completed'] for v in s['metrics']['subgoal_validations'])
 kind=annotation['review_class']
 result={'key':annotation['key'],'review_class':kind,'source_full':True,'new_record_count':len(new)}
 if kind=='CALENDAR_EFFECT_CONFLICT':
  assert len(new)==1 and len(set(offsets))==1 and now
  off=offsets[0];actual=new[0]['reminder_timestamp'];anchor=now[0]
  k='tomorrow' if s['sample_id']=='add_reminder_content_and_week_delta_and_time' else 'friday'
  assert calendar_violation(anchor,actual,off,k) is True
  result.update({'anchor_epoch':anchor,'actual_epoch':actual,'offset_seconds':off,
   'actual_local':(datetime.fromtimestamp(actual,timezone.utc)+timedelta(seconds=off)).replace(tzinfo=None).isoformat(),
   'anchor_local':(datetime.fromtimestamp(anchor,timezone.utc)+timedelta(seconds=off)).replace(tzinfo=None).isoformat(),
   'past_in_absolute_time':actual<anchor,'requested_time_type':k})
 elif kind=='NO_COMMIT_EXECUTOR_SYNTAX_ERROR':
  assert not new and native_adds and all('SyntaxError' in x['content'] for x in native_adds)
  result['native_add_attempts']=native_adds
 elif kind=='NO_NATIVE_ADD_TEXT_ONLY':
  assert not new and not native_adds
  assert any('add_reminder' in str(m.get('content')) for m in flat if m.get('role')=='assistant')
 else:raise ValueError('Non-adjudicated record was included as confirmed')
 result['check_pass']=True
 return result

def run(input_zip,annotations,out):
 ans=json.loads(Path(annotations).read_text());results=[]
 with zipfile.ZipFile(input_zip) as z:
  cache={}
  for a in ans:
   if not a['count_in_conservative_set']:continue
   model,persona,trial,sid=a['key'].split('/')
   path=f'raw/toolsandbox/{model}/{persona}/trial_{trial}_results.json'
   if path not in cache:cache[path]=json.loads(z.read(path))
   s=next(s for s in cache[path]['samples'] if s['sample_id']==sid)
   results.append(check_raw(s,a))
 result={'checked':len(results),'passes':sum(r['check_pass'] for r in results),'counts':dict(collections.Counter(r['review_class'] for r in results)),'records':results,'new_llm_calls':0}
 Path(out).write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
 return result

if __name__=='__main__':
 import argparse
 p=argparse.ArgumentParser();p.add_argument('--raw-zip',required=True);p.add_argument('--annotations',required=True);p.add_argument('--out',required=True);a=p.parse_args();r=run(a.raw_zip,a.annotations,a.out);print({k:v for k,v in r.items() if k!='records'})
