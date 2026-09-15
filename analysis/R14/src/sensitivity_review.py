"""Explicit POST-HOC robustness checks; not the locked heldout analysis.
Accept transparent English relationship inflections. Tighten the phase-boundary
screen to explicit 'back/restore/revert' rather than the ambiguous word 'again'.
No source score changes, no LLM requests.
"""
from pathlib import Path
import json,copy,csv,re,collections,argparse
from corpus_audit import rebuild,goal,STATIC,SEQUENTIAL,temporal,csvout,dump
ALIASES={'friends':'friend','enemies':'enemy'}
def alias_state(s):
 d=copy.deepcopy(s)
 if isinstance(d.get('CONTACT'),list):
  for v in d['CONTACT']:
   x=v.get('relationship')
   if isinstance(x,str):v['relationship']=ALIASES.get(x.strip().casefold(),x.strip().casefold())
 return d

def run(raw,out):
 rows=[];phase=[]
 for p in sorted(raw.glob('toolsandbox/*/*/trial_*_results.json')):
  d=json.loads(p.read_text());model=p.parts[-3];persona=p.parts[-2];trial=d['trial_id']
  for i,s in enumerate(d['samples']):
   sid=s['sample_id']
   if sid not in STATIC and sid!=SEQUENTIAL:continue
   r=rebuild(s);ini=alias_state(r['initial']);key=f'{model}/{persona}/{trial}/{sid}'
   if sid in STATIC:
    vals=[goal(sid,alias_state(pt['state']),ini) for pt in r['points'] if pt['kind']!='user'];v=temporal(vals)
    row={'key':key,'sample_id':sid,'model':model,'persona':persona,'trial':trial,'final':v['final'],'ever_true_final_false':v['ever_true_final_false'],'observed_regression':v['observed_regression'],'original_progress':(s['metrics']['progress_rates'] or [None])[-1]};rows.append(row)
   else:
    c=[u for u in r['users'] if u['turn']>0 and re.search(r'\b(back|restore|revert)\b',u['text'],re.I) and re.search(r'\bfriends?\b',u['text'],re.I)]
    boundary=c[0]['turn'] if c else None
    before=[pt for pt in r['points'] if boundary is not None and pt['turn']<boundary and pt['kind']=='turn_end']
    a=goal('phase_enemy',alias_state(before[-1]['state']),ini) if before else None;b=goal('phase_friend',alias_state(r['points'][-1]['state']),ini)
    phase.append({'key':key,'boundary':boundary,'phase1':a,'phase2':b,'scoped_complete':a and b if a is not None and b is not None else None,'original_progress':(s['metrics']['progress_rates'] or [None])[-1]})
 csvout(out/'posthoc_semantic_sensitivity.csv',rows);csvout(out/'posthoc_phase_sensitivity.csv',phase)
 summ={'label':'POSTHOC_SENSITIVITY_NOT_INDEPENDENT_CONFIRMATION','static_n':len(rows),'static_true':sum(x['final'] is True for x in rows),'static_false':sum(x['final'] is False for x in rows),'static_unknown':sum(x['final'] is None for x in rows),'static_lost':sum(x['ever_true_final_false'] is True for x in rows),'full_but_false':sum(x['final'] is False and x['original_progress']==1 for x in rows),'phase_n':len(phase),'phase_true':sum(x['scoped_complete'] is True for x in phase),'phase_false':sum(x['scoped_complete'] is False for x in phase),'phase_unknown':sum(x['scoped_complete'] is None for x in phase)}
 dump(out/'posthoc_sensitivity_summary.json',summ);print(json.dumps(summ,indent=2))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--raw',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();run(a.raw,a.out)
