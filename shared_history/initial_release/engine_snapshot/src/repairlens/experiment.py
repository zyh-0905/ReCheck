"""Synthetic executable signal-summary workflows with uncertain dependencies.

No LLM, natural failure corpus, trained model or public-benchmark score is used.
The candidate family is known; policies never receive the sampled true index.
"""
from pathlib import Path
from dataclasses import replace
import argparse
import gzip
import hashlib
import json
import math
import tempfile
import time
import shutil
import numpy as np
import pandas as pd
from .core import Probe,RepairProblem,RepairSolver,required_union,mask_cost,information_action
from .artifacts import ArtifactStore,canonical_bytes

ROOT=Path(__file__).resolve().parents[2]
FAMILIES=['sparse','overlap','general','nuisance','coupled','expensive']
METHODS=['restart','conservative','point_estimate','random','graph_entropy','class_entropy','ec2','myopic','lookahead2','exact','discard_replay']


def make_problem(seed:int,family:str):
    rng=np.random.default_rng(seed)
    masks={'sparse':[1,2,4],'overlap':[3,5,6],'general':list(range(1,8)),
           'nuisance':[3],'coupled':list(range(1,8)),'expensive':list(range(1,8))}[family]
    models=[(m,z) for m in masks for z in range(4)]
    maskmass=rng.dirichlet(np.full(len(masks),.7))
    prior=tuple(float(maskmass[masks.index(m)]/4) for m,z in models)
    costs=tuple(float(x) for x in rng.integers(3,10,size=3))
    probes=[]
    for j in range(3):
        out=tuple((m>>j)&1 for m,z in models)
        probes.append(Probe(f'refresh-{j}',costs[j],out,1<<j))
    for j in range(3):
        out=tuple(((m>>j)&1)^((z&1) if family=='coupled' else 0) for m,z in models)
        scale=2.4 if family=='expensive' else float(rng.uniform(.15,1.35))
        probes.append(Probe(f'inspect-{j}',round(scale*costs[j],4),out,0))
    probes.append(Probe('parity-01',round(float(rng.uniform(.5,4)),4),tuple(((m&1)^((m>>1)&1)) for m,z in models),0))
    for j in range(2):
        probes.append(Probe(f'route-{j}',round(float(rng.uniform(.08,.35)),4),tuple((z>>j)&1 for m,z in models),0))
    p=RepairProblem(tuple(m for m,z in models),prior,costs,tuple(probes))
    truth=int(rng.choice(len(models),p=prior))
    meta={'seed':seed,'family':family,'models':[list(x) for x in models],
          'true_mask':models[truth][0],'true_route':models[truth][1]}
    return p,truth,meta


class ReplayWorld:
    """Deterministic black-box worker, physically writing local JSON artifacts."""
    def __init__(self,path,meta):
        self.meta=meta;self.store=ArtifactStore(path)
        self._mask=meta['true_mask'];self._route=meta['true_route']
        rng=np.random.default_rng(meta['seed']+9321)
        self._signals=[rng.normal(0,1,64)+np.sin(np.linspace(0,4*np.pi,64)) for _ in range(3)]
        self.scope=hashlib.sha256(canonical_bytes({'seed':meta['seed'],'source':1,'contract':'signal-summary-v1'})).hexdigest()
        self.blocks_executed=0
        self.store.put('source',{'offset':0.},'root-contract')
        for j in range(3):self.store.put(f'block{j}',self.compute(j,0.),'initial-v0')
        self.initial_digest=self.store.digest()
        self.store.snapshot(Path(path).parent/(Path(path).name+'-snapshot'))
        self.store.put('source',{'offset':1.},'root-contract')

    def compute(self,j,source):
        x=self._signals[j]+source*int(bool(self._mask&(1<<j)))
        # Route changes provenance, not the numerical function, except that
        # coupled-family inspection results intentionally require route decoding.
        if self._route&1:x=x[::-1][::-1]
        if self._route&2:x=x.copy()
        f=np.fft.rfft(x)
        return {'mean':float(x.mean()),'rms':float(np.sqrt(np.mean(x*x))),'dc':float(abs(f[0]))}

    def refresh(self,j,persist=True):
        out=self.compute(j,1.);self.blocks_executed+=1
        if persist:self.store.put(f'block{j}',out,self.scope)
        return out

    def probe(self,spec:Probe,persist=True):
        kind=spec.name.split('-')[0]
        if kind=='refresh':
            j=int(spec.name.split('-')[1]); out=self.refresh(j,persist)
            obs=int(abs(out['mean']-self.compute(j,0.)['mean'])>.5)
            return obs,{'observed_summary':out,'artifact_reusable':persist}
        if kind=='inspect':
            j=int(spec.name.split('-')[1])
            old=self.compute(j,0.);new=self.compute(j,1.)
            obs=int(abs(new['mean']-old['mean'])>.5)
            if self.meta['family']=='coupled':obs^=self._route&1
            return obs,{'public_trace_bit':obs,'artifact_reusable':False}
        if kind=='route':
            j=int(spec.name.split('-')[1]);obs=(self._route>>j)&1
            return obs,{'public_route_bit':obs,'artifact_reusable':False}
        if kind=='parity':
            bits=[int(abs(self.compute(j,1.)['mean']-self.compute(j,0.)['mean'])>.5) for j in (0,1)]
            return bits[0]^bits[1],{'public_parity':bits[0]^bits[1],'artifact_reusable':False}
        raise ValueError(kind)

    def preserve(self,j):
        # The planner may certify independence within its retained finite family.
        # Relabeling is not evidence if the family omitted the truth (stress-tested).
        payload=self.store.get(f'block{j}','initial-v0')
        self.store.put(f'block{j}',payload,self.scope)

    def evaluate(self):
        """Evaluator-only, invoked strictly AFTER the policy stops."""
        outputs=[self.store.get(f'block{j}',self.scope) for j in range(3)]
        gold=[self.compute(j,1.) for j in range(3)]
        per=[all(math.isclose(o[k],g[k],rel_tol=1e-10,abs_tol=1e-10) for k in g) for o,g in zip(outputs,gold)]
        # Three fixed downstream contracts, not independent new benchmark tasks.
        a=sum(o['mean'] for o in outputs);ag=sum(g['mean'] for g in gold)
        b=sum((j+1)*o['rms'] for j,o in enumerate(outputs));bg=sum((j+1)*g['rms'] for j,g in enumerate(gold))
        follow=math.isclose(a,ag,rel_tol=1e-10,abs_tol=1e-10) and math.isclose(b,bg,rel_tol=1e-10,abs_tol=1e-10)
        return {'current_ok':per[0],'state_ok':all(per),'followup_ok':follow,'complete':all(per) and follow}


def run_case(problem,truth,meta,method,path):
    # truth is used by the experiment driver only; ReplayWorld mediates outcomes.
    world=ReplayWorld(path,meta);p=problem
    support=tuple(range(len(p.prior)));cached=0;used=0;cost=1.;fallback=False
    planning_ms=0.;actions=[];traces=[{'kind':'source_correction','charged':1.}]
    reuse=method!='discard_replay'
    depth={'exact':-1,'discard_replay':-1,'myopic':1,'lookahead2':2}.get(method)
    solver=RepairSolver(p,reuse=reuse,depth=depth) if depth is not None else None
    rng=np.random.default_rng(meta['seed']+997)
    tstart=time.perf_counter()
    if method=='restart': final_mask=(1<<len(p.artifact_costs))-1
    elif method=='conservative':final_mask=required_union(p,support)
    elif method=='point_estimate': final_mask=p.required_masks[int(np.argmax(p.prior))]
    else:
        for step in range(len(p.probes)+1):
            before=time.perf_counter()
            if solver is not None:_,a=solver.choose(support,cached,used)
            elif method in ('graph_entropy','class_entropy','ec2'):
                a=information_action(p,support,cached,used,method)
            elif method=='random':
                if len({p.required_masks[i] for i in support})==1:a=-1
                else:
                    opts=[j for j,pr in enumerate(p.probes) if not used&(1<<j) and len({pr.outcomes[i] for i in support})>1]
                    a=int(rng.choice(opts)) if opts else -1
            else:raise ValueError(method)
            planning_ms+=(time.perf_counter()-before)*1000
            if a==-1:break
            pr=p.probes[a];obs,evidence=world.probe(pr,persist=reuse)
            cost+=pr.cost;used|=1<<a
            if reuse:cached|=pr.produces
            new_support=tuple(i for i in support if pr.outcomes[i]==obs)
            traces.append({'kind':'probe','name':pr.name,'observed':obs,'charged':pr.cost,
                           'support_before':list(support),'support_after':list(new_support),'cached':cached,**evidence})
            actions.append(a)
            if not new_support:
                fallback=True
                break
            support=new_support
        else:raise RuntimeError('probe loop did not terminate')
        final_mask=((1<<len(p.artifact_costs))-1) if fallback else required_union(p,support)
    repaired=final_mask&~cached
    for j,c in enumerate(p.artifact_costs):
        if repaired&(1<<j):
            world.refresh(j);cost+=c
            traces.append({'kind':'final_refresh','block':j,'charged':c})
        elif cached&(1<<j):
            # Verification includes content hash and exact current input scope.
            world.store.get(f'block{j}',world.scope)
        else:world.preserve(j)
    # Charge the same declared publication validation cost to every method.
    validation=.15*len(p.artifact_costs);cost+=validation
    traces.append({'kind':'publication_validation','charged':validation})
    execution_ms=(time.perf_counter()-tstart)*1000-planning_ms
    checks=world.evaluate()
    restart=1+sum(p.artifact_costs)+validation
    row={'seed':meta['seed'],'family':meta['family'],'method':method,'cost':cost,
         'normalized_cost':cost/restart,'planning_ms':planning_ms,'execution_ms':execution_ms,
         'probes':len(actions),'recomputed_blocks':world.blocks_executed,
         'retained_hypotheses':len(support),'fallback':fallback,
         'states_evaluated':solver.states_evaluated if solver else 0,
         'initial_digest':world.initial_digest,'final_digest':world.store.digest(),**checks}
    if abs(cost-sum(e['charged'] for e in traces))>1e-8:raise AssertionError('cost ledger mismatch')
    return row,traces


def run_main(per_family=20):
    rows=[];specs=[]
    with gzip.open(ROOT/'results/repairlens_traces.jsonl.gz','wt') as f, tempfile.TemporaryDirectory(prefix='repairlens-') as tmp:
        for fi,family in enumerate(FAMILIES):
            for x in range(per_family):
                seed=10000+fi*100+x
                p,truth,meta=make_problem(seed,family)
                specs.append({'seed':seed,'family':family,'required_masks':list(p.required_masks),'prior':list(p.prior),
                              'artifact_costs':list(p.artifact_costs),'probes':[vars(a) for a in p.probes],
                              'evaluation_only_truth_index':truth,'metadata':meta})
                for method in METHODS:
                    path=Path(tmp)/f'{seed}-{method}'
                    out,trace=run_case(p,truth,meta,method,path);rows.append(out)
                    f.write(json.dumps({'seed':seed,'family':family,'method':method,'events':trace},separators=(',',':'))+'\n')
                    if x==0 and fi==0 and method in ('exact','restart'):
                        dest=ROOT/'results'/f'repairlens_example_{method}'
                        if dest.exists():shutil.rmtree(dest)
                        shutil.copytree(path,dest)
                print('RepairLens completed',family,seed,flush=True)
    pd.DataFrame(rows).to_csv(ROOT/'results/repairlens_main.csv',index=False)
    (ROOT/'results/repairlens_instances.json').write_text(json.dumps(specs,separators=(',',':')))


def run_support_stress():
    rows=[]
    with tempfile.TemporaryDirectory(prefix='repairlens-stress-') as tmp:
        for seed in range(20000,20060):
            p,truth,meta=make_problem(seed,'general')
            true_mask=meta['true_mask']
            keep=[i for i,m in enumerate(p.required_masks) if m!=true_mask]
            den=sum(p.prior[i] for i in keep)
            reduced=RepairProblem(tuple(p.required_masks[i] for i in keep),tuple(p.prior[i]/den for i in keep),p.artifact_costs,
                tuple(Probe(pr.name,pr.cost,tuple(pr.outcomes[i] for i in keep),pr.produces) for pr in p.probes))
            for label,pp in [('covered',p),('truth_omitted',reduced)]:
                row,trace=run_case(pp,truth,meta,'exact',Path(tmp)/f'{seed}-{label}')
                rows.append({'condition':label,**row})
    pd.DataFrame(rows).to_csv(ROOT/'results/repairlens_support_stress.csv',index=False)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--stage',choices=['main','stress','all'],default='all')
    parser.add_argument('--per-family',type=int,default=20);a=parser.parse_args()
    if a.stage in ('main','all'):run_main(a.per_family)
    if a.stage in ('stress','all'):run_support_stress()
