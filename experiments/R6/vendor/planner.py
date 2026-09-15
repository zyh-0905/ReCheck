"""Known-transition, calibrated-loss planner. Exact small model; not a novel DP claim.
All forecasts use ONLY ages, last observed semantic bits, task class and quota.
Live data/true modes/answers are not accepted by Planner.choose.
"""
from dataclasses import dataclass
from functools import lru_cache
from itertools import combinations
import math
import numpy as np

@dataclass(frozen=True)
class Action:
    ids:tuple
    mask:int
    cost:int
    @property
    def cover(self):return tuple(j for j in range(3) if self.mask&(1<<j))

def actions(shared,cap):
    ps=[(f's{j}',1<<j,2) for j in range(3)]
    if shared:ps += [('p01',3,3),('p12',6,3)]
    best={0:Action((),0,0)}
    for k in range(1,len(ps)+1):
        for ss in combinations(ps,k):
            c=sum(x[2] for x in ss)
            if c>cap:continue
            mask=0
            for x in ss:mask|=x[1]
            a=Action(tuple(x[0] for x in ss),mask,c)
            if mask not in best or (a.cost,a.ids)<(best[mask].cost,best[mask].ids):best[mask]=a
    return tuple(sorted(best.values(),key=lambda a:(a.cost,a.ids)))

def posterior(ages,hazards):
    if len(ages)!=3 or len(hazards)!=3 or any(type(x) is not int or x<0 for x in ages) or any(not 0<=x<=.5 for x in hazards):
        raise ValueError('invalid ages/hazards')
    p=[(1-(1-2*h)**a)/2 for a,h in zip(ages,hazards)]
    mm=np.arange(8)[:,None];zz=np.arange(8)[None,:];out=np.ones((8,8))
    for j in range(3):out*=np.where(((mm^zz)>>j)&1,p[j],1-p[j])
    return out

class Planner:
    """Memory value matters when task consequences are direction-asymmetric."""
    def __init__(self,table,*,hazards,transition,price,budget,step_cap,shared):
        self.table=np.array(table,dtype=float,copy=True)
        if self.table.ndim!=3 or self.table.shape[1:]!=(8,8) or not np.isfinite(self.table).all() or (self.table<0).any():
            raise ValueError('invalid risk table')
        self.qn=self.table.shape[0];self.P=np.array(transition,dtype=float,copy=True)
        if self.P.shape!=(self.qn,self.qn) or not np.isfinite(self.P).all() or (self.P<0).any() or not np.allclose(self.P.sum(axis=1),1,atol=1e-12):
            raise ValueError('invalid task transition')
        if type(budget) is not int or budget<0 or type(step_cap) is not int or step_cap<0 or not math.isfinite(price) or price<0:
            raise ValueError('invalid budget/price')
        self.hazards=tuple(hazards);posterior((0,0,0),self.hazards)
        self.price=price;self.budget=budget;self.actions=actions(shared,step_cap)
        self.table.setflags(write=False);self.P.setflags(write=False)
        self._stage_cached=lru_cache(None)(self._stage)
        self.values=lru_cache(None)(self._values)
        self.scores=lru_cache(None)(self._scores)
        self.look=lru_cache(None)(self._look)
        self._base_indices=lru_cache(None)(self._base)
        self._indices=lru_cache(None)(self._idx)

    def stage(self,ages,a):
        return self._stage_cached(tuple(ages),a.mask)

    def _stage_with(self,ages,mask,table,hazards):
        probs=posterior(ages,hazards)
        m=np.arange(8)[:,None];z=np.arange(8)[None,:]
        updated=(m&(~mask&7))|(z&mask)
        # [q,m,z] then marginalize current true states. This includes outcomes
        # of a probe, rather than treating updated memory as unchanged.
        loss=np.sum(probs[None,:,:]*table[:,updated,np.broadcast_to(z,(8,8))],axis=2)
        trans=np.zeros((8,8))
        for old in range(8):np.add.at(trans[old],updated[old],probs[old])
        return loss,trans

    def _stage(self,ages,mask):
        loss,T=self._stage_with(ages,mask,self.table,self.hazards)
        loss.setflags(write=False);T.setflags(write=False)
        return loss,T

    def _next(self,ages,a):
        return tuple(1 if a.mask&(1<<j) else ages[j]+1 for j in range(3))

    def _base(self,h,ages,b):
        # Fixed age-based pacing, independent of fitted risk or evaluation outcomes.
        interval=max(1,math.ceil(2*h/max(b,1)))
        weights=np.array([(1,1,0),(0,0,1)]+[(1,1,1)]*max(0,self.qn-2),dtype=float)[:self.qn]
        if self.qn==1:weights=np.ones((1,3))
        importance=weights+self.P@weights
        indices=np.zeros((self.qn,8),dtype=int)
        for q in range(self.qn):
            eligible=[i for i,a in enumerate(self.actions) if a.cost and a.cost<=b
                      and max(ages[j] for j in a.cover)>=interval]
            if eligible:
                i=min(eligible,key=lambda i:(-sum(importance[q,j]*ages[j] for j in self.actions[i].cover)/self.actions[i].cost,
                                            self.actions[i].cost,self.actions[i].ids))
                indices[q,:]=i
        return indices

    def _scores(self,method,h,ages,b):
        if h<=0 or b<0:raise ValueError('invalid horizon/budget')
        if method not in ('exact','myopic','rollout2','age_paced','never'):raise ValueError('method')
        allscores=[]
        for a in self.actions:
            if a.cost>b:allscores.append(np.full((self.qn,8),np.inf));continue
            loss,T=self.stage(ages,a);v=loss+self.price*a.cost
            if h>1 and method!='myopic':
                nxt=self._next(ages,a)
                if method=='rollout2':
                    child=self.look(1,h-1,nxt,b-a.cost)
                else:child=self.values(method,h-1,nxt,b-a.cost)
                v=v+self.P@child@T.T
            allscores.append(v)
        return np.stack(allscores,axis=0)

    def _idx(self,method,h,ages,b):
        if method=='age_paced':return self._base_indices(h,ages,b)
        if method=='never':return np.zeros((self.qn,8),dtype=int)
        return np.argmin(np.round(self.scores(method,h,ages,b),12),axis=0)

    def _values(self,method,h,ages,b):
        if h==0:return np.zeros((self.qn,8))
        idx=self._indices(method,h,ages,b)
        if method in ('age_paced','never'):
            out=np.zeros((self.qn,8))
            for i in np.unique(idx):
                a=self.actions[int(i)]
                loss,T=self.stage(ages,a)
                child=self.values(method,h-1,self._next(ages,a),b-a.cost)
                v=loss+self.price*a.cost+self.P@child@T.T
                out=np.where(idx==i,v,out)
            return out
        s=self.scores(method,h,ages,b)
        return np.take_along_axis(s,idx[None,:,:],axis=0)[0]

    def _look(self,depth,h,ages,b):
        if h==0:return np.zeros((self.qn,8))
        if depth==0:return self.values('age_paced',h,ages,b)
        vals=[]
        for a in self.actions:
            if a.cost>b:continue
            loss,T=self.stage(ages,a)
            child=self.look(depth-1,h-1,self._next(ages,a),b-a.cost)
            vals.append(loss+self.price*a.cost+self.P@child@T.T)
        return np.min(vals,axis=0)

    def choose(self,method,h,ages,q,memory,budget):
        if type(h) is not int or h<=0 or type(budget) is not int or not 0<=budget<=self.budget:
            raise ValueError('invalid horizon/budget')
        if type(q) is not int or not 0<=q<self.qn or type(memory) is not int or not 0<=memory<8:
            raise ValueError('invalid public state')
        posterior(tuple(ages),self.hazards)
        if method not in ('exact','myopic','rollout2','age_paced','never'):raise ValueError('method')
        a=self.actions[int(self._indices(method,h,tuple(ages),budget)[q,memory])]
        if a.cost>budget:raise RuntimeError('budget violation')
        return a

    def evaluate(self,method,h,ages,b,table,hazards):
        """Evaluator only: a fixed frozen policy on another finite risk kernel.
        This reference diagnostic is NEVER used by choose or test execution.
        """
        other=np.asarray(table);rates=tuple(hazards)
        @lru_cache(None)
        def ev(h,ages,b):
            if h==0:return np.zeros((self.qn,8))
            idx=self._indices(method,h,ages,b);out=np.zeros((self.qn,8))
            for i in np.unique(idx):
                a=self.actions[int(i)]
                loss,T=self._stage_with(ages,a.mask,other,rates)
                child=ev(h-1,self._next(ages,a),b-a.cost)
                v=loss+self.price*a.cost+self.P@child@T.T
                out=np.where(idx==i,v,out)
            return out
        return ev(h,tuple(ages),b).copy()

    def cache_info(self):
        return {'value_states':self.values.cache_info().currsize,'score_states':self.scores.cache_info().currsize,
                'stage_kernels':self._stage_cached.cache_info().currsize,'lookahead_states':self.look.cache_info().currsize}

    def clear(self):
        for f in (self.values,self.scores,self._stage_cached,self.look,self._base_indices,self._indices):f.cache_clear()
