"""Known finite-model references for overlapping probes with hard episode budgets.
No hidden state or model response enters scheduling. Not a new general DP theorem.
"""
from dataclasses import dataclass
from functools import lru_cache
from itertools import combinations
import math

METHODS=('recheck_joint','bundle_rollout','bundle_myopic','age_paced','separable_projected','never')


def mismatch(age:int,hazard:float)->float:
    if type(age) is not int or age<0 or not 0<=hazard<=.5:
        raise ValueError('Age must be nonnegative integer; symmetric flip hazard in [0,.5]')
    return (1-(1-2*hazard)**age)/2

@dataclass(frozen=True)
class Action:
    ids:tuple
    cover:tuple
    cost:int

class Solver:
    def __init__(self,spec):
        self.hazards=tuple(spec['hazards']);self.weights=tuple(tuple(w) for w in spec['weights'])
        self.P=tuple(tuple(r) for r in spec['transition']);self.price=float(spec['price'])
        self.cap=spec['step_cap'];self.n=len(self.hazards);self.qn=len(self.weights)
        if self.price<0 or type(self.cap) is not int or self.cap<0:raise ValueError('Invalid price/cap')
        if len(self.P)!=self.qn or any(len(r)!=self.qn or any(x<0 for x in r) or abs(sum(r)-1)>1e-10 for r in self.P):raise ValueError('Invalid task transition')
        if any(len(w)!=self.n or any(x<0 for x in w) for w in self.weights):raise ValueError('Invalid task weights')
        for h in self.hazards:mismatch(0,h)
        packets=spec['packets'];ids=[p['id'] for p in packets]
        if len(set(ids))!=len(ids):raise ValueError('Duplicate packet ID')
        for p in packets:
            if type(p['cost']) is not int or p['cost']<=0 or not p['cover'] or any(type(j) is not int or j<0 or j>=self.n for j in p['cover']):raise ValueError('Invalid packet')
        best={():Action((),(),0)}
        for size in range(1,len(packets)+1):
            for subset in combinations(packets,size):
                cost=sum(p['cost'] for p in subset)
                if cost>self.cap:continue
                cover=tuple(sorted({j for p in subset for j in p['cover']}))
                a=Action(tuple(p['id'] for p in subset),cover,cost)
                if cover not in best or (cost,a.ids)<(best[cover].cost,best[cover].ids):best[cover]=a
        self.catalogue=tuple(sorted(best.values(),key=lambda a:(a.cost,a.ids)))
        self._single_cost=tuple(min((p['cost']/len(set(p['cover'])) for p in packets if j in p['cover']),default=1e6) for j in range(self.n))
        # Instance-local caches avoid retaining solvers after a grid cell finishes.
        self.value=lru_cache(None)(self._value)
        self.base_value=lru_cache(None)(self._base_value)
        self.look_value=lru_cache(None)(self._look_value)
        self.choose=lru_cache(None)(self._choose)
        self.single_value=lru_cache(None)(self._single_value)
        self.evaluate=lru_cache(None)(self._evaluate)

    def actions(self,b:int):return tuple(a for a in self.catalogue if a.cost<=b)
    def after(self,ages,b,a):
        if a.cost>b or a.cost>self.cap:raise ValueError('Hard budget violation')
        return tuple(1 if j in a.cover else ages[j]+1 for j in range(self.n)), b-a.cost
    def loss(self,ages,q,a,hazards=None):
        rates=self.hazards if hazards is None else hazards
        return sum(self.weights[q][j]*mismatch(int(ages[j]),rates[j]) for j in range(self.n) if j not in a.cover)
    def _expected(self,h,ages,q,b,a,continuation):
        nxt,nb=self.after(ages,b,a)
        return self.price*a.cost+self.loss(ages,q,a)+sum(self.P[q][k]*continuation(h-1,nxt,k,nb) for k in range(self.qn))
    def _value(self,h,ages,q,b):
        if h==0:return 0.
        return min(self._expected(h,ages,q,b,a,self.value) for a in self.actions(b))
    def _base_action(self,h,ages,q,b):
        if b<min((a.cost for a in self.catalogue if a.cost),default=1e9):return self.catalogue[0]
        interval=max(1,math.ceil(2*h/max(b,1)))
        eligible=[a for a in self.actions(b) if a.cover and max(ages[j] for j in a.cover)>=interval]
        if not eligible:return self.catalogue[0]
        weights=[self.weights[q][j]+sum(self.P[q][k]*self.weights[k][j] for k in range(self.qn)) for j in range(self.n)]
        return min(eligible,key=lambda a:(-sum(weights[j]*ages[j] for j in a.cover)/a.cost,a.cost,a.ids))
    def _base_value(self,h,ages,q,b):
        if h==0:return 0.
        return self._expected(h,ages,q,b,self._base_action(h,ages,q,b),self.base_value)
    def _look_value(self,depth,h,ages,q,b):
        if h==0:return 0.
        if depth==0:return self.base_value(h,ages,q,b)
        return min(self._expected(h,ages,q,b,a,lambda hh,aa,qq,bb:self.look_value(depth-1,hh,aa,qq,bb)) for a in self.actions(b))
    def _single_value(self,h,age,q,j):
        if h==0:return 0.
        skip=self.weights[q][j]*mismatch(age,self.hazards[j])+sum(self.P[q][k]*self.single_value(h-1,age+1,k,j) for k in range(self.qn))
        refresh=self.price*self._single_cost[j]+sum(self.P[q][k]*self.single_value(h-1,1,k,j) for k in range(self.qn))
        return min(skip,refresh)
    def _choose(self,method,h,ages,q,b):
        if method not in METHODS or h<=0 or b<0 or len(ages)!=self.n:raise ValueError('Invalid policy/state')
        if method=='never':return self.catalogue[0]
        if method=='age_paced':return self._base_action(h,ages,q,b)
        if method=='recheck_joint':score=lambda a:self._expected(h,ages,q,b,a,self.value)
        elif method=='bundle_myopic':score=lambda a:self.loss(ages,q,a)+self.price*a.cost
        elif method=='bundle_rollout':score=lambda a:self._expected(h,ages,q,b,a,lambda hh,aa,qq,bb:self.look_value(1,hh,aa,qq,bb))
        else:
            benefits=[]
            for j in range(self.n):
                v=self.weights[q][j]*mismatch(ages[j],self.hazards[j])+sum(self.P[q][k]*(self.single_value(h-1,ages[j]+1,k,j)-self.single_value(h-1,1,k,j)) for k in range(self.qn))
                benefits.append(v)
            score=lambda a:self.price*a.cost-sum(benefits[j] for j in a.cover)
        return min(self.actions(b),key=lambda a:(score(a),a.cost,a.ids))
    def _evaluate(self,method,h,ages,q,b,actual_hazards=None):
        if h==0:return 0.
        a=self.choose(method,h,ages,q,b);nxt,nb=self.after(ages,b,a)
        return self.loss(ages,q,a,actual_hazards)+self.price*a.cost+sum(self.P[q][k]*self.evaluate(method,h-1,nxt,k,nb,actual_hazards) for k in range(self.qn))
