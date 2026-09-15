"""Empirical direction-sensitive task-failure kernel learned on calibration only."""
import hashlib,json
import numpy as np
from . import data,evaluator
from vendor.r4 import worker,environment

def sha(o):
    return hashlib.sha256(json.dumps(o,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()

def single_failure(rows,task,cached,true):
    w=environment.World(rows);w.set_modes(data.decode(true))
    view=worker.make_view(task,data.memory(cached))
    actual,_=worker.execute(w,view,worker.rule_plan(view))
    return int(actual!=evaluator.correct_answer(rows,task))

def catalog_labels(seed):
    rows=data.make_rows(seed)
    result=np.zeros((5,8,8),dtype=np.uint8)
    for q in range(5):
        task=data.make_task(q,rows,seed*100+q)
        expected=evaluator.correct_answer(rows,task)
        for z in range(8):
            w=environment.World(rows);w.set_modes(data.decode(z))
            for m in range(8):
                view=worker.make_view(task,data.memory(m))
                actual,_=worker.execute(w,view,worker.rule_plan(view))
                result[q,m,z]=int(actual!=expected)
    return result

def fit(seeds):
    if not seeds or len(set(seeds))!=len(seeds):raise ValueError('nonempty independent calibration IDs required')
    counts=np.zeros((5,8,8),dtype=np.int64)
    for seed in seeds:counts+=catalog_labels(seed)
    out={'schema':'risk_kernel_v1','seeds':list(seeds),'independent_catalogs':len(seeds),
         'task_classes':list(data.load_protocol()['tasks']),
         'table':(counts/len(seeds)).tolist(),'failure_counts':counts.tolist()}
    out['fingerprint']=sha(out)
    return out

def semantic_table(binary=False):
    a=np.zeros((5,8,8))
    for q in range(5):
        for m in range(8):
            for z in range(8):
                c=sum(bool((m^z)&(1<<j)) for j in data.RELEVANT[q])
                a[q,m,z]=int(c>0) if binary else c
    return a

def single_effect(table):
    """Single-flip noisy-OR approximation; higher-order interactions deliberately omitted."""
    t=np.asarray(table,dtype=float)
    if t.shape!=(5,8,8):raise ValueError('table shape')
    out=np.zeros_like(t)
    for q in range(5):
        for m in range(8):
            for z in range(8):
                survival=1.
                for j in range(3):
                    if (m^z)&(1<<j):survival*=1-t[q,m,m^(1<<j)]
                out[q,m,z]=1-survival
    return out

def residual_tables(train,validation):
    """Validation used only to describe out-of-sample table error."""
    a=np.asarray(train['table']);b=np.asarray(validation['table'])
    return {'mean_absolute_error':float(np.abs(a-b).mean()),'max_absolute_error':float(np.abs(a-b).max()),
       'by_task_mae':np.abs(a-b).mean(axis=(1,2)).tolist(),
       'first_order_vs_joint_max_abs':float(np.max(np.abs(single_effect(a)-a))),
       'validation_not_used_for_tuning':True}
