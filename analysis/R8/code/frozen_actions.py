"""Offline intervention on a recorded proposed action, not a new model trajectory."""
import argparse,json,csv,hashlib
from pathlib import Path
import bootstrap
from r7clib.native import NativeSession
from r7clib.cases import infer_intent
from boundary import score_write,intervene

def run(feedback,out):
 f=Path(feedback);out=Path(out)
 if out.exists():raise ValueError('Output exists')
 out.mkdir(parents=True)
 cases={x['id']:x for x in json.loads((f/'kit_source/fixtures/cases.json').read_text())}
 rows=[]
 for p in sorted((f/'runs/R7C_main/episodes').glob('primary_*.json')):
  ep=json.loads(p.read_text());case=cases[ep['case_id']];intent={'person_message':'person','literal_message':'literal','reminder_label':'reminder'}[case['family']]
  req=infer_intent(case['public'])
  for change in ('none','binding'):
   s=NativeSession(case['snapshot']);prefix=0
   for t in ep['turns']:
    if t['kind']!='tool':continue
    a=t['action']
    if a['tool'] in ('send_message_with_phone_number','modify_reminder'):
     intervened=intervene(s,intent,change,101)
     before=s.world();r=s.call(a['tool'],a['arguments']);after=s.world()
     correct=score_write(intent,req,before,after) if r['ok'] else False
     record={'episode_id':ep['episode_id'],'case_id':ep['case_id'],'arm':ep['arm'],'intent':intent,'intervention':change,'source_file_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'source_turn':t['turn'],'unchanged_proposed_action':a,'prefix_calls_replayed':prefix,'external_operations':intervened,'before_world':before,'after_world':after,'native_response':r,'correct_at_this_commit':correct,'wrong_write_at_this_commit':before!=after and not correct,'new_llm_calls':0,'kind':'FROZEN_ACTION_TRANSITION_NOT_AGENT_EPISODE'}
     (out/f'{ep["episode_id"]}_{change}.json').write_text(json.dumps(record,ensure_ascii=False,sort_keys=True,indent=2,allow_nan=False))
     rows.append({k:record[k] for k in ('episode_id','case_id','arm','intent','intervention','prefix_calls_replayed','source_turn','correct_at_this_commit','wrong_write_at_this_commit')});break
    else:
     r=s.call(a['tool'],a['arguments'],scope='replayed_prefix')
     if r!=t['observation']:raise ValueError(f'Prefix differs {p.name} {t["turn"]}')
     prefix+=1
   else:raise ValueError('No mutating action in source')
 assert len(rows)==84
 assert all(x['correct_at_this_commit'] for x in rows if x['intervention']=='none')
 with (out/'summary.csv').open('w',newline='') as h:
  w=csv.DictWriter(h,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
 agg=[]
 for intent in ('person','literal','reminder'):
  for change in ('none','binding'):
   g=[x for x in rows if x['intent']==intent and x['intervention']==change]
   agg.append({'intent':intent,'intervention':change,'transition_checks':len(g),'correct':sum(x['correct_at_this_commit'] for x in g),'wrong_write':sum(x['wrong_write_at_this_commit'] for x in g)})
 (out/'aggregates.json').write_text(json.dumps(agg,indent=2));print(json.dumps(agg,indent=2))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--feedback',required=True);p.add_argument('--out',required=True);a=p.parse_args();run(a.feedback,a.out)
