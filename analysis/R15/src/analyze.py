"""R15 extension. Selected tasks only, effects computed before reading source labels."""
from __future__ import annotations
import argparse,csv,json,hashlib,sys,collections
from pathlib import Path
from effects import TASKS,REMINDERS,MESSAGES,clock_context,effect_at,latest_outgoing_target,normalized
from record_parser_r14 import rebuild,csvout,dump,temporal

def initial_preserved(initial,state,ns,target=None):
 before=initial.get(ns);after=state.get(ns)
 if not isinstance(before,list) or not isinstance(after,list):return None
 key={'CONTACT':'person_id','REMINDER':'reminder_id','MESSAGING':'message_id'}[ns]
 # Message history may have duplicated IDs: compare a multiset, never map it.
 if ns=='MESSAGING':
  a=collections.Counter(json.dumps(r,sort_keys=True) for r in before);b=collections.Counter(json.dumps(r,sort_keys=True) for r in after)
  return all(b[k]>=n for k,n in a.items())
 for r in before:
  rows=[s for s in after if s.get(key)==r.get(key)]
  if len(rows)!=1:return False
  original={k:v for k,v in r.items() if not(ns=='CONTACT' and r.get(key)==target and k=='phone_number')}
  actual={k:v for k,v in rows[0].items() if not(ns=='CONTACT' and r.get(key)==target and k=='phone_number')}
  if original!=actual:return False
 return True

def summarize(rows):
 def counts(rs):
  return {'records':len(rs),'effect_true':sum(r['effect_final'] is True for r in rs),'effect_false':sum(r['effect_final'] is False for r in rs),'effect_unknown':sum(r['effect_final'] is None for r in rs),
   'source_full':sum(r['source_full'] for r in rs),'source_full_known':sum(r['source_full'] and r['effect_final'] is not None for r in rs),
   'source_full_effect_false_candidates':sum(r['source_full'] and r['effect_final'] is False for r in rs),
   'observed_goal_regressions':sum(r['observed_regression'] for r in rs),'ever_true_final_false':sum(r['ever_true_final_false'] is True for r in rs),
   'initial_preservation_false':sum(r['initial_preserved_final'] is False for r in rs),'source_full_initial_preservation_false':sum(r['source_full'] and r['initial_preserved_final'] is False for r in rs),
   'extra_new_object_candidates':sum(r['new_object_count']>1 for r in rs),'new_llm_calls':0}
 return {'total':counts(rows),'by_task':{sid:counts([r for r in rows if r['sample_id']==sid]) for sid in sorted(TASKS)},
 'by_split':{sp:counts([r for r in rows if r['split']==sp]) for sp in sorted({r['split'] for r in rows})}}

def run(raw,out,split):
 out.mkdir(parents=True,exist_ok=False);rows=[];details=[]
 for p in sorted(raw.glob('toolsandbox/*/*/trial_*_results.json')):
  trial=int(p.name.split('_')[1])
  if split=='dev' and trial>1 or split=='later' and trial<2:continue
  d=json.loads(p.read_bytes());assert d['trial_id']==trial
  model,persona=p.parts[-3:-1];rel=p.relative_to(raw).as_posix()
  for si,s in enumerate(d['samples']):
   sid=s['sample_id']
   if sid not in TASKS:continue
   key=f'{model}/{persona}/{trial}/{sid}';rec=rebuild(s)
   clock=clock_context(rec,sid) if sid in REMINDERS else {}
   target=latest_outgoing_target(rec['initial']) if sid=='modify_contact_with_message_recency' else None
   ns='REMINDER' if sid in REMINDERS else ('MESSAGING' if sid in MESSAGES else 'CONTACT')
   states=[]
   for pt in rec['points']:
    v=effect_at(sid,pt['state'],rec['initial'],clock,target)
    states.append({'kind':pt['kind'],'turn':pt['turn'],'message':pt['message'],'effect':v,
     'initial_preserved':initial_preserved(rec['initial'],pt['state'],ns,target),'rows':pt['state'].get(ns)})
   active=[p for p in states if p['kind']!='user']
   end=active[-1] if active else {'effect':{'effect':None,'content':None,'time':None,'new_ids':[]},'initial_preserved':None}
   structural=[x for x in rec['issues'] if x.startswith(('duplicate_','missing_receipt:','orphan_receipt:','bad_'))]
   vals=[p['effect']['effect'] for p in active];tt=temporal(vals)
   final=end['effect']['effect'] if not structural else None
   # Read labels only after state predicates have been computed.
   metrics=s.get('metrics') or {};rates=metrics.get('progress_rates') or [];progress=rates[-1] if rates else None
   row={'key':key,'source':rel,'sample_index':si,'sample_id':sid,'model':model,'persona':persona,'trial':trial,'split':'dev' if trial<2 else 'later',
    'namespace':ns,'target_id':target,'structural_issues':';'.join(structural),'state_issues':';'.join(x for x in rec['issues'] if x not in structural),
    'clock_reason':clock.get('reason'),'clock_offset':clock.get('offset_seconds'),'target_epochs':json.dumps(clock.get('target_epochs')),
    'content_final':end['effect']['content'],'time_final':end['effect']['time'],'effect_final':final,
    'effect_ever_true':tt['ever_true'],'observed_regression':tt['observed_regression'],'ever_true_final_false':tt['ever_true_final_false'],
    'initial_preserved_final':end['initial_preserved'],'initial_preservation_ever_false':any(p['initial_preserved'] is False for p in active),
    'new_object_count':len(set(end['effect']['new_ids'])) if sid in REMINDERS|MESSAGES else 0,
    'source_status':s.get('status'),'source_progress':progress,'source_full':progress==1.0,'source_full_effect_false_candidate':progress==1.0 and final is False,
    'effect_history':json.dumps(vals),'calls':sum(len(b['calls']) for b in rec['batches'])}
   rows.append(row)
   details.append({'key':key,'row':row,'users':rec['users'],'clock':clock,'target':target,'initial':rec['initial'],'points':states,
    'batches':rec['batches'], 'source_subgoals':[{'details':g.get('subgoal',{}).get('details'),'completed':g.get('is_completed')} for g in metrics.get('subgoal_validations',[])]})
 csvout(out/'episodes.csv',rows);dump(out/'episodes.json',rows);dump(out/'evidence.json',details);dump(out/'summary.json',summarize(rows))
 print(json.dumps(summarize(rows),indent=2))

if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--raw',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);ap.add_argument('--split',choices=['dev','later','all'],required=True);a=ap.parse_args();run(a.raw,a.out,a.split)
