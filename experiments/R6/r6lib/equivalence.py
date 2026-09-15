"""Separate byte integrity, typed discrete equality and scoped numerical equality.
Never round answers, packets, identities, credits, or raw evidence to pass a test.
"""
import copy,math
from .data import digest
ROOT_TIME={'planner_setup_seconds','execution_seconds','cache_info'}
RECORD_TIME={'planning_seconds','probe_seconds','tool_seconds'}
PRED='predicted_task_error_after_receipts'

def science(obj):
    out={k:copy.deepcopy(v) for k,v in obj.items() if k not in ROOT_TIME}
    if 'records' in out:
        out['records']=[{k:v for k,v in r.items() if k not in RECORD_TIME} for r in out['records']]
    return out

def valid_prob(v):return type(v) is float and math.isfinite(v) and 0<=v<=1

def compare(left,right,atol=1e-14):
    a,b=science(left),science(right);issues=[];drift=[]
    def walk(x,y,path):
        prob=len(path)==3 and path[0]=='records' and type(path[1]) is int and path[2]==PRED
        if prob:
            if not valid_prob(x) or not valid_prob(y):issues.append({'path':list(path),'error':'invalid probability type/range'});return
            d=abs(x-y)
            if d>atol:issues.append({'path':list(path),'error':'probability tolerance exceeded','delta':d})
            elif d:drift.append(d)
            return
        if type(x) is not type(y):issues.append({'path':list(path),'error':'type mismatch'});return
        if isinstance(x,dict):
            if set(x)!=set(y):issues.append({'path':list(path),'error':'key mismatch'});return
            for k in x:walk(x[k],y[k],path+(k,))
        elif isinstance(x,list):
            if len(x)!=len(y):issues.append({'path':list(path),'error':'length mismatch'});return
            for i,(u,v) in enumerate(zip(x,y)):walk(u,v,path+(i,))
        elif x!=y or (isinstance(x,float) and not math.isfinite(x)):
            issues.append({'path':list(path),'error':'strict value mismatch'})
    walk(a,b,())
    return {'pass':not issues,'issues':issues,'tolerated_predictions':len(drift),'maximum_probability_delta':max(drift,default=0.)}

def reference(obj):
    s=science(obj);pred=[]
    for r in s['records']:
        v=r.pop(PRED)
        if not valid_prob(v):raise ValueError('invalid probability')
        pred.append(v)
    return {'discrete_sha256':digest(s),'predictions':pred,'records':len(pred)}

def check_reference(ref,obj,atol=1e-14):
    actual=reference(obj);issues=[]
    if ref['discrete_sha256']!=actual['discrete_sha256']:issues.append('discrete_science_mismatch')
    x=ref['predictions'];y=actual['predictions']
    if len(x)!=len(y):issues.append('record_count')
    elif any(not valid_prob(v) for v in x+y):issues.append('invalid_probabilities')
    elif any(abs(u-v)>atol for u,v in zip(x,y)):issues.append('prediction_tolerance')
    return {'pass':not issues,'issues':issues,
            'maximum_probability_delta':max((abs(u-v) for u,v in zip(x,y)),default=0.)}

def strict_equal(x,y):
    """For raw calibration/model evidence: bool/int/float are different types."""
    if type(x) is not type(y):return False
    if isinstance(x,dict):return set(x)==set(y) and all(strict_equal(x[k],y[k]) for k in x)
    if isinstance(x,(list,tuple)):return len(x)==len(y) and all(strict_equal(a,b) for a,b in zip(x,y))
    if isinstance(x,float):return math.isfinite(x) and math.isfinite(y) and x==y
    return x==y
