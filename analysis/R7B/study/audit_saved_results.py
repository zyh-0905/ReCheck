"""Recheck saved native snapshots without importing ToolSandbox or a model client."""
import json,sys
from pathlib import Path
from collections import Counter
from score import assess

def latest(snapshot,namespace):
 rows=snapshot['_dbs'][namespace]
 top=max(r['sandbox_message_index'] for r in rows)
 return [{k:v for k,v in r.items() if k!='sandbox_message_index'} for r in rows
         if r['sandbox_message_index']==top and any(v is not None for k,v in r.items() if k!='sandbox_message_index')]

def audit(root):
 root=Path(root);checked=0;issues=[];public_by_case={};by_method={};feedback_age_cases=[]
 for p in sorted((root/'controlled_extensions').glob('*.json')):
  d=json.loads(p.read_text());checked+=1
  before=latest(d['before_policy_snapshot'],'MESSAGING');after=latest(d['after_policy_snapshot'],'MESSAGING')
  contacts=latest(d['after_policy_snapshot'],'CONTACT')
  target=[c for c in contacts if c['name']==d['public_input']['public_task']['target_name']]
  assert len(target)==1
  s=assess(before,after,target_id=target[0]['person_id'],target_phone=target[0]['phone_number'],content=d['public_input']['public_task']['content'])
  if any(d['score'][k]!=v for k,v in s.items()):issues.append([p.name,'score mismatch'])
  for db,key in [('CONTACT','contacts_unchanged_by_policy'),('REMINDER','reminders_unchanged_by_policy')]:
   if latest(d['before_policy_snapshot'],db)!=latest(d['after_policy_snapshot'],db):issues.append([p.name,db+' changed'])
  counts=Counter(e['scope'] for e in d['events'])
  if counts['runtime']!=d['runtime_calls'] or counts['ordinary_task_observation']!=d['ordinary_observation_calls']:issues.append([p.name,'call counts'])
  sends=[e for e in d['events'] if e['scope']=='runtime' and e['tool']=='send_message_with_phone_number' and e['response']['ok']]
  new_ids=set(r['message_id'] for r in after)-set(r['message_id'] for r in before)
  if {e['response']['value'] for e in sends}!=new_ids:issues.append([p.name,'send IDs mismatch'])
  if any(e['arguments']['phone_number']!=d['policy_return']['used_phone'] for e in sends):issues.append([p.name,'plan phone mismatch'])
  key=d['regime'],d['observation_timing']
  val=d['public_input']
  if key in public_by_case and public_by_case[key]!=val:issues.append([p.name,'input differs by method'])
  public_by_case[key]=val
  m=d['method'];by_method.setdefault(m,Counter()).update({'cases':1,'safe_successes':int(s['safe_success']),'wrong_writes':s['wrong_writes'],'runtime_calls':counts['runtime'],'ordinary_observation_calls':counts['ordinary_task_observation'],'startup_calls':counts['startup_calibration']})
 summary=json.loads((root/'summary.json').read_text())
 for m,c in by_method.items():
  for k in ('safe_successes','runtime_calls','ordinary_observation_calls','startup_calls'):
   if c[k]!=summary['by_method'][m][k]:issues.append([m,'summary mismatch',k])
 if checked!=48 or len(public_by_case)!=12:issues.append(['fixture coverage'])
 return {'pass':not issues,'records_checked':checked,'paired_cases':len(public_by_case),'issues':issues,'by_method':{k:dict(v) for k,v in by_method.items()},'method':'independent snapshot/multiset score and tool-ledger check; no model calls','limits':'Does not authenticate provider or establish statistical generalization.'}
if __name__=='__main__':
 r=audit(sys.argv[1]);p=Path(sys.argv[2]);p.write_text(json.dumps(r,indent=2));print(json.dumps(r,indent=2));raise SystemExit(0 if r['pass'] else 2)
