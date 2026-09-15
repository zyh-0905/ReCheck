from __future__ import annotations
import csv,json,collections
from pathlib import Path
from effects import TASKS,REMINDERS
from record_parser_r14 import csvout,dump
from analyze import summarize

def finalize(root,out):
 rows=json.loads((out/'dev/episodes.json').read_text())+json.loads((out/'later/episodes.json').read_text())
 anns=json.loads((root/'results/REVIEW_ANNOTATIONS.json').read_text());am={a['key']:a for a in anns}
 assert len({r['key'] for r in rows})==576
 joined=[]
 for r in rows:
  a=am.get(r['key'])
  joined.append({**r,'review_class':a['review_class'] if a else 'NOT_A_FULL_SCORE_NEGATIVE_CANDIDATE','conservative_conflict':a['count_in_conservative_set'] if a else False})
 csvout(out/'all_episodes.csv',joined)
 csvout(out/'confirmed_cases.csv',[r for r in joined if r['conservative_conflict']])
 summary=summarize(rows);summary['review_counts']=dict(collections.Counter(a['review_class'] for a in anns))
 summary['review_conservative_by_split']=dict(collections.Counter(a['split'] for a in anns if a['count_in_conservative_set']))
 summary['full_score_reminder_records']=sum(r['source_full'] and r['sample_id'] in REMINDERS for r in rows)
 summary['calendar_conflict_by_model']=dict(collections.Counter(a['key'].split('/')[0] for a in anns if a['review_class']=='CALENDAR_EFFECT_CONFLICT'))
 summary['raw_record_source']='Third-party public SAP/TED records, not newly generated LLM trials or original ToolSandbox leaderboard scores.'
 summary['scope_notes']=['sourcefull+false candidates are not all errors; explicit user revisions and timezone context were reviewed separately','no new temporal regressions in the six added goal predicates','counts are clustered repeats of six task IDs, not576 independent tasks','annotation is by same assistant, not independent human gold','all source scores and original R14 outputs remain unchanged']
 dump(out/'summary.json',summary)
 bytask=[]
 for sid in sorted(TASKS):
  zz=[r for r in joined if r['sample_id']==sid]
  bytask.append({'task':sid,'records':len(zz),'source_full':sum(r['source_full'] for r in zz),'candidates':sum(r['source_full_effect_false_candidate'] for r in zz),'conservative_conflicts':sum(r['conservative_conflict'] for r in zz),'calendar_conflicts':sum(r['review_class']=='CALENDAR_EFFECT_CONFLICT' for r in zz)})
 csvout(out/'by_task.csv',bytask)
 return summary
