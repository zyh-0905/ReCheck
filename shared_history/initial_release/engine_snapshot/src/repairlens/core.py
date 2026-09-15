"""Productive diagnosis over an explicit, deterministic finite hypothesis family.

The problem contains candidate behavior, never the true hypothesis index.
Exact dynamic programming is a finite reference, not a scalable LLM guarantee.
"""
from dataclasses import dataclass
from functools import lru_cache
from collections import defaultdict
import math


@dataclass(frozen=True)
class Probe:
    name: str
    cost: float
    outcomes: tuple[int,...]
    produces: int=0


@dataclass(frozen=True)
class RepairProblem:
    required_masks: tuple[int,...]
    prior: tuple[float,...]
    artifact_costs: tuple[float,...]
    probes: tuple[Probe,...]

    def __post_init__(self):
        n=len(self.required_masks); d=len(self.artifact_costs); maxmask=(1<<d)-1
        if not n or len(self.prior)!=n or not d: raise ValueError('empty or mismatched model')
        if any(not math.isfinite(x) or x<=0 for x in self.prior) or not math.isclose(sum(self.prior),1,abs_tol=1e-8):
            raise ValueError('strictly positive normalized prior required')
        if any(not math.isfinite(x) or x<=0 for x in self.artifact_costs): raise ValueError('positive repair costs required')
        if any(m<0 or m>maxmask for m in self.required_masks): raise ValueError('invalid required mask')
        for p in self.probes:
            if not math.isfinite(p.cost) or p.cost<=0 or len(p.outcomes)!=n or p.produces<0 or p.produces>maxmask:
                raise ValueError('invalid probe')


def required_union(problem:RepairProblem,support:tuple[int,...])->int:
    if not support: raise ValueError('empty support cannot certify repair')
    mask=0
    for i in support:
        if not 0<=i<len(problem.prior): raise ValueError('bad hypothesis index')
        mask |= problem.required_masks[i]
    return mask


def mask_cost(problem:RepairProblem,mask:int)->float:
    return sum(c for j,c in enumerate(problem.artifact_costs) if mask & (1<<j))


def terminal_cost(problem:RepairProblem,support:tuple[int,...],cached:int)->float:
    return mask_cost(problem,required_union(problem,support)&~cached)


def partitions(problem:RepairProblem,support:tuple[int,...],probe_index:int):
    buckets=defaultdict(list)
    probe=problem.probes[probe_index]
    total=sum(problem.prior[i] for i in support)
    for i in support: buckets[probe.outcomes[i]].append(i)
    return [(out,tuple(ids),sum(problem.prior[i] for i in ids)/total) for out,ids in sorted(buckets.items())]


class RepairSolver:
    """Bellman solver with cache state; depth=-1 is exact, finite depth is rollout."""
    def __init__(self,problem:RepairProblem,reuse:bool=True,depth:int=-1):
        if depth==0 or depth < -1: raise ValueError('depth must be positive or -1')
        self.problem=problem;self.reuse=reuse;self.depth=depth
        self._cached=lru_cache(maxsize=None)(self._solve)

    def choose(self,support:tuple[int,...],cached:int=0,used:int=0)->tuple[float,int]:
        required_union(self.problem,support)
        return self._cached(tuple(sorted(support)),cached,used,self.depth)

    def _solve(self,support,cached,used,depth):
        p=self.problem
        best=terminal_cost(p,support,cached); action=-1
        if depth==0 or best<1e-12: return best,action
        for j,probe in enumerate(p.probes):
            if used&(1<<j): continue
            parts=partitions(p,support,j)
            next_cached=cached|probe.produces if self.reuse else cached
            if len(parts)==1 and next_cached==cached: continue
            child_depth=-1 if depth==-1 else depth-1
            val=probe.cost+sum(prob*self._cached(ids,next_cached,used|(1<<j),child_depth)[0]
                               for _,ids,prob in parts)
            if val < best-1e-10: best,action=val,j
        return float(best),action

    @property
    def states_evaluated(self): return self._cached.cache_info().misses


def _entropy(weights):
    total=sum(weights)
    return -sum((x/total)*math.log2(x/total) for x in weights if x>0)


def information_action(problem:RepairProblem,support:tuple[int,...],cached:int,used:int,mode:str)->int:
    """GBS/full entropy, repair-class entropy, or an EC2-style edge-cut score.

    These are local, fully disclosed finite-model instantiations, not reproductions
    of contemporary LLM-agent systems.
    """
    def ent(ids,classes):
        mass=defaultdict(float)
        for i in ids: mass[problem.required_masks[i] if classes else i]+=problem.prior[i]
        return _entropy(mass.values())
    def edge(ids):
        return sum(problem.prior[i]*problem.prior[j] for k,i in enumerate(ids) for j in ids[k+1:]
                   if problem.required_masks[i]!=problem.required_masks[j])
    if not support: raise ValueError('empty support')
    if mode!='graph_entropy' and terminal_cost(problem,support,cached)<1e-12:return -1
    if mode=='class_entropy' and len({problem.required_masks[i] for i in support})==1:return -1
    base=edge(support) if mode=='ec2' else ent(support,mode=='class_entropy')
    if base<=1e-15:return -1
    best=0.; chosen=-1
    for j,probe in enumerate(problem.probes):
        if used&(1<<j):continue
        parts=partitions(problem,support,j)
        if len(parts)==1:continue
        after=sum(prob*(edge(ids) if mode=='ec2' else ent(ids,mode=='class_entropy')) for _,ids,prob in parts)
        gain=(base-after)/probe.cost
        if gain>best+1e-12:best,chosen=gain,j
    return chosen
