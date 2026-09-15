"""Summaries and fixed phase checks on the already frozen splits; no score changes."""
from pathlib import Path
import sys,json,csv,collections,argparse
from corpus_audit import analyze,dump,csvout,rebuild,SEQUENTIAL
from phase_audit import phase_check

def main(root):
 raw=root/'inputs/download/raw';result=root/'results';allrows=[];links=[];phases=[];struct=[];runids=[];nameissues=[];counts=[]
 for split,d in [('dev','dev_v2'),('heldout','heldout_v1')]:
  allrows.extend(csv.DictReader((result/d/'episodes.csv').open()))
 for p in sorted(raw.glob('toolsandbox/*/*/trial_*_results.json')):
  doc=json.loads(p.read_text());model=p.parts[-3];persona=p.parts[-2];trial=doc['trial_id']
  for i,s in enumerate(doc['samples']):
   assert s['trial_id']==trial
   runids.append(s.get('run_id'));sid=s['sample_id'];key=f'{model}/{persona}/{trial}/{sid}'
   r=rebuild(s)
   for bi,b in enumerate(r['batches']):
    names={c.get('id'):c.get('function',{}).get('name') for c in b['calls']}
    for rec in b['receipts']:
     cid=rec.get('tool_call_id')
     if cid in names and rec.get('name')!=names[cid]:nameissues.append({'key':key,'batch':bi,'id':cid,'call_name':names[cid],'receipt_name':rec.get('name')})
   if sid==SEQUENTIAL:
    ph=phase_check(s);phases.append({'key':key,'source':p.relative_to(raw).as_posix(),'sample_index':i,'model':model,'persona':persona,'trial':trial,'split':'dev' if trial<2 else 'heldout',**ph,'original_final_progress':(s['metrics'].get('progress_rates') or [None])[-1]})
 for model in sorted({x['model'] for x in allrows}):
  for persona in ['expert','nonexpert']:
   rows=[x for x in allrows if x['model']==model and x['persona']==persona]
   counts.append({'model':model,'persona':persona,'records':len(rows),'static_in_scope':sum(x['goal_supported']=='True' for x in rows),
       'static_known':sum(x['goal_known']=='True' for x in rows),'static_effect_true':sum(x['effect_final']=='True' for x in rows),'static_effect_false':sum(x['effect_final']=='False' for x in rows),
       'static_effect_unknown':sum(x['goal_supported']=='True' and x['goal_known']=='False' for x in rows),'static_lost_goal_candidates':sum(x['ever_true_final_false_candidate']=='True' for x in rows),
       'static_original_full_but_effect_false':sum(x['reported_full_effect_false_candidate']=='True' for x in rows),
       'source_final_full_all_tasks':sum(x['ted_final_full']=='True' for x in rows)})
 csvout(result/'all_episodes.csv',allrows);csvout(result/'by_model_persona.csv',counts);csvout(result/'sequential_scopes.csv',phases);dump(result/'receipt_name_anomalies.json',nameissues)
 phasecounts={}
 for split in ['dev','heldout']:
  rows=[x for x in phases if x['split']==split];phasecounts[split]={'n':len(rows),'scoped_complete':sum(x['scoped_complete'] is True for x in rows),'scoped_not_complete':sum(x['scoped_complete'] is False for x in rows),'unknown':sum(x['scoped_complete'] is None for x in rows),'original_full':sum(x['original_final_progress']==1 for x in rows),'complete_but_not_original_full':sum(x['scoped_complete'] is True and x['original_final_progress']!=1 for x in rows)}
 summary={'all_records':len(allrows),'unique_run_ids':len(set(runids)),'receipt_name_anomalies':len(nameissues),'static_in_scope':sum(x['static_in_scope'] for x in counts),'static_known':sum(x['static_known'] for x in counts),'static_effect_true':sum(x['static_effect_true'] for x in counts),'static_effect_false':sum(x['static_effect_false'] for x in counts),'static_effect_unknown':sum(x['static_effect_unknown'] for x in counts),'static_lost_goal_candidates':sum(x['static_lost_goal_candidates'] for x in counts),'static_original_full_but_effect_false':sum(x['static_original_full_but_effect_false'] for x in counts),'unscored_task_records':sum(x['goal_supported']=='False' and x['sample_id']!=SEQUENTIAL for x in allrows),'phase_checks':phasecounts,
  'interpretation':'The predicates check selected task effects, not all safety/communication requirements. Candidate regression requires manual user-intent review; source TED scores retained.'}
 dump(result/'combined_summary.json',summary);print(json.dumps(summary,ensure_ascii=False,indent=2))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);a=p.parse_args();main(a.root)
