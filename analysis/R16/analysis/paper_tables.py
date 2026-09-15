"""Generate descriptive paper tables; preserve all original labels and denominators.
Run from anywhere: python analysis/paper_tables.py
Only reads frozen local evidence; never calls a model or network service.
"""
from __future__ import annotations
import csv,json
from pathlib import Path

CONFLICT_CLASSES={'CALENDAR_EFFECT_CONFLICT','NO_COMMIT_EXECUTOR_SYNTAX_ERROR','NO_NATIVE_ADD_TEXT_ONLY'}

def flag(value):
    if value is True or value=='True': return True
    if value is False or value=='False': return False
    raise ValueError(f'Not a serialized boolean: {value!r}')

def validate_rows(rows):
    seen=set()
    for r in rows:
        if r['key'] in seen: raise ValueError('Duplicate episode identity')
        seen.add(r['key'])
        full,conflict=flag(r['source_full']),flag(r['conservative_conflict'])
        if conflict and not full: raise ValueError('A retained conflict must have source full progress')
        if conflict != (r['review_class'] in CONFLICT_CLASSES):
            raise ValueError('Conflict flag inconsistent with preserved review class')

def summarize(rows):
    rows=list(rows);validate_rows(rows)
    return dict(records=len(rows),tasks=len({r['sample_id'] for r in rows}),
                source_full=sum(flag(r['source_full']) for r in rows),
                conflicts=sum(flag(r['conservative_conflict']) for r in rows),
                calendar=sum(r['review_class']=='CALENDAR_EFFECT_CONFLICT' for r in rows),
                no_commit=sum(r['review_class'] in CONFLICT_CLASSES-{'CALENDAR_EFFECT_CONFLICT'} for r in rows))

def write_csv(path,rows):
    with path.open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)

def main():
    root=Path(__file__).resolve().parents[1]
    inp=root/'analysis/reproduced_r15/all_episodes.csv'
    if not inp.exists(): inp=root/'evidence/R15_Effect_Coverage/results/reproduced/all_episodes.csv'
    rows=list(csv.DictReader(inp.open(encoding='utf-8',newline='')))
    validate_rows(rows)
    out=root/'analysis/paper_results';out.mkdir(exist_ok=True)
    overall=summarize(rows); assert overall=={'records':576,'tasks':6,'source_full':349,'conflicts':64,'calendar':62,'no_commit':2},overall
    reminders=[r for r in rows if r['sample_id'].startswith('add_reminder')]
    by_task=[dict(task=k,**summarize(r for r in rows if r['sample_id']==k)) for k in sorted({r['sample_id'] for r in rows})]
    by_model=[dict(model=k,**summarize(r for r in reminders if r['model']==k)) for k in sorted({r['model'] for r in reminders})]
    by_persona=[dict(persona=k,**summarize(r for r in reminders if r['persona']==k)) for k in sorted({r['persona'] for r in reminders})]
    by_split=[dict(split=k,**summarize(r for r in rows if r['split']==k)) for k in ['dev','later']]
    for k,v in [('by_task',by_task),('by_model',by_model),('by_persona',by_persona),('by_split',by_split)]:write_csv(out/(k+'.csv'),v)
    data={'overall':overall,'reminders':summarize(reminders),'by_model':by_model,'by_persona':by_persona,'by_split':by_split,
          'scope':'Descriptive fixed-corpus counts, not independent task samples, new evaluations, or causal effects.'}
    (out/'summary.json').write_text(json.dumps(data,indent=2),encoding='utf-8')
    print(json.dumps(data,indent=2))
if __name__=='__main__':main()
