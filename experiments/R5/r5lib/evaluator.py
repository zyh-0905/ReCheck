"""Independent numerical/reference scoring, not a policy input."""
from .data import decode

def correct_answer(rows,task):
    if task['type']==1:
        tab={r['sku']:r for r in rows}
        return {'available_total':sum(max(0,tab[s]['physical']-tab[s]['reserved']) for s in task['skus'])}
    relevant=[r for r in rows if r['active'] and r['category']==task['category']]
    if task['type']==2:relevant=[r for r in relevant if max(0,r['physical']-r['reserved'])>=task['minimum']]
    return {'skus':sorted(r['sku'] for r in relevant)}

def independently_execute(rows,task,cached,true):
    """Does not call vendor.World, worker.execute, or its gold function."""
    m=decode(cached);z=decode(true)
    if task['type']==1:
        selected=[next(r for r in rows if r['sku']==s) for s in task['skus']]
    else:
        if m[0]<z[0]:return {'error':'PAGE_BEFORE_FIRST'}
        keep=[r for r in rows if r['active']==(m[1]==z[1])]
        selected=[r for r in keep[3*(m[0]-z[0]):] if r['category']==task['category']]
    if task['type']==0:return {'skus':sorted(r['sku'] for r in selected)}
    def free(r):
        raw=r['physical'] if z[2] else max(0,r['physical']-r['reserved'])
        return max(0,raw-(r['reserved'] if m[2] else 0))
    if task['type']==1:return {'available_total':sum(free(r) for r in selected)}
    return {'skus':sorted(r['sku'] for r in selected if free(r)>=task['minimum'])}
