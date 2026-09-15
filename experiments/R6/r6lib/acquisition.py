"""Paid, on-demand supervised calibration. No precomputed full tensor.
An atom = one canonical semantic cell measured on all panel catalogs.
The oracle is a training environment: its correct labels never leave the ledger
except for atoms actually purchased by this learner.
"""
from dataclasses import dataclass
import copy,time
import numpy as np
from . import data
from vendor.r4 import environment,worker


def canonical_cell(c):
    if len(c)!=3 or any(type(x) is not int for x in c):raise ValueError('integer cell required')
    q,m,z=c
    if not 0<=q<5 or not 0<=m<8 or not 0<=z<8:raise ValueError('cell range')
    mask=sum(1<<j for j in data.RELEVANT[q])
    return q,m&mask,z&mask

def all_cells():
    return sorted({canonical_cell((q,m,z)) for q in range(5) for m in range(8) for z in range(8)
                   if canonical_cell((q,m,z))[1]!=canonical_cell((q,m,z))[2]})
def single_cells():return [c for c in all_cells() if (c[1]^c[2]).bit_count()==1]
def interaction_cells():return [c for c in all_cells() if (c[1]^c[2]).bit_count()>=2]
def key(c):return ':'.join(map(str,c))
def unkey(k):return tuple(map(int,k.split(':')))

class PaidOracle:
    """State and label ownership are per learner; other learners' events are not inputs.
    Cached repeats within the same oracle do not incur a second execution.
    Reference answers are obtained via actual, correct zero-mode workflows,
    checked against independent arithmetic, and charged separately.
    """
    def __init__(self,seeds):
        if not seeds or len(set(seeds))!=len(seeds) or any(type(s) is not int for s in seeds):raise ValueError('independent seeds')
        self.seeds=tuple(seeds);self.events=[];self._paid={};self._references={}
        self._rows={s:data.make_rows(s) for s in seeds}
        self.label_executions=0;self.reference_executions=0;self.tool_calls=0
        self.execution_seconds=0.;self.reference_seconds=0.
    @property
    def total_workflows(self):return self.label_executions+self.reference_executions
    def _run(self,seed,q,m,z):
        rows=self._rows[seed];task=data.make_task(q,rows,seed*100+q)
        w=environment.World(rows);w.set_modes(data.decode(z));view=worker.make_view(task,data.memory(m))
        tic=time.perf_counter();ans,trace=worker.execute(w,view,worker.rule_plan(view));dt=time.perf_counter()-tic
        self.tool_calls+=len(trace)
        return ans,trace,dt
    def _reference(self,seed,q):
        k=(seed,q)
        if k not in self._references:
            ans,trace,dt=self._run(seed,q,0,0)
            task=data.make_task(q,self._rows[seed],seed*100+q)
            if ans!=data.correct_answer(self._rows[seed],task):raise AssertionError('reference contract failure')
            e={'sequence':len(self.events),'kind':'reference','seed':seed,'q':q,'m':0,'z':0,
               'answer':ans,'trace':trace,'workflow_seconds':dt}
            self.events.append(e);self.reference_executions+=1;self.reference_seconds+=dt
            self._references[k]=copy.deepcopy(ans)
        return self._references[k]
    def purchase(self,cell):
        c=canonical_cell(cell)
        if c!=tuple(cell) or c[1]==c[2]:raise ValueError('only canonical non-diagonal atoms may be bought')
        if c in self._paid:return copy.deepcopy(self._paid[c])
        q,m,z=c;failures=[]
        for seed in self.seeds:
            truth=self._reference(seed,q)
            ans,trace,dt=self._run(seed,q,m,z);bad=int(ans!=truth)
            self.events.append({'sequence':len(self.events),'kind':'label','seed':seed,'q':q,'m':m,'z':z,
                                'reference_key':f'{seed}:{q}','answer':ans,'trace':trace,'failure':bad,'workflow_seconds':dt})
            self.label_executions+=1;self.execution_seconds+=dt;failures.append(bad)
        obs={'cell':list(c),'n':len(self.seeds),'failures':sum(failures),'labels':failures,
             'mean':sum(failures)/len(self.seeds)}
        self._paid[c]=obs;return copy.deepcopy(obs)
    def cost(self):
        return {'label_executions':self.label_executions,'reference_executions':self.reference_executions,
                'total_workflows':self.total_workflows,'tool_calls':self.tool_calls,
                'label_execution_seconds':self.execution_seconds,'reference_execution_seconds':self.reference_seconds}

class Learner:
    def __init__(self,oracle):self.oracle=oracle;self.observed={}
    def buy(self,c):
        obs=self.oracle.purchase(c);self.observed[tuple(c)]=obs;return obs
    def initialize_singles(self):
        for c in single_cells():self.buy(c)
    def table(self):return expand_table(self.observed)
    def snapshot(self):
        obj={'observed':{key(c):copy.deepcopy(v) for c,v in sorted(self.observed.items())},
             'table':self.table().tolist(),'cost':copy.deepcopy(self.oracle.cost()),
             'oracle_event_count':len(self.oracle.events),'training_seeds':list(self.oracle.seeds)}
        obj['model_fingerprint']=data.digest({'observed':obj['observed'],'training_seeds':obj['training_seeds']})
        return obj

def expand_table(observed):
    if not set(single_cells())<=set(observed):raise ValueError('missing paid singles')
    out=np.zeros((5,8,8),dtype=float)
    for q in range(5):
        for m in range(8):
            for z in range(8):
                c=canonical_cell((q,m,z));_,mm,zz=c
                if mm==zz:continue
                if c in observed:out[q,m,z]=observed[c]['mean'];continue
                survival=1.
                for j in data.RELEVANT[q]:
                    if (mm^zz)&(1<<j):survival*=1-observed[(q,mm,mm^(1<<j))]['mean']
                out[q,m,z]=1-survival
    return out

def from_snapshot(s):return {unkey(k):v for k,v in s['observed'].items()}
def any_table():
    return np.array([[[float(canonical_cell((q,m,z))[1]!=canonical_cell((q,m,z))[2]) for z in range(8)] for m in range(8)] for q in range(5)])
