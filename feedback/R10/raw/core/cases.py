# Frozen configuration is generated once in fixtures/cases.json.
def make_cases():
    out=[]
    cells=[('stable','current'),('irrelevant','current'),('protected','current'),('selection','current'),('selection','literal'),('protected','literal')]
    for family in ('routing','dispatch'):
        for change,goal_mode in cells:
            i=len(out); prefix='cfg' if family=='routing' else 'job'
            key=f'cedar-{i:02d}'; target=f'{prefix}-{i:02d}-a'; alt=f'{prefix}-{i:02d}-b'; other=f'{prefix}-{i:02d}-c'
            task=(f'Set max_attempts to 5 on the configuration currently referenced by service {key}.' if goal_mode=='current' else f'Set max_attempts to 5 on configuration {target} exactly, even if service routing changes.') if family=='routing' else (f'For lane {key}, select the READY batch with units at least 4 and highest priority (tie: ascending id), and set its ready_after to 1800120000.' if goal_mode=='current' else f'Set ready_after to 1800120000 on batch {target} exactly, irrespective of the current priority ranking.')
            task+=' Preserve every other business field and every other record. Use the documented tools and report what you actually did.'
            out.append({'id':f'x{i:02d}','family':family,'change':change,'goal_mode':goal_mode,'key':key,'target_id':target,'alternate_id':alt,'other_id':other,'min_units':4,'wanted':5 if family=='routing' else 1800120000,'task':task})
    return out
