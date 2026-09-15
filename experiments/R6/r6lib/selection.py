"""Equal-cost, outcome-blind interaction acquisition.
The proposed decision selector is a two-extreme *immediate* regret heuristic on
hypothetical public states. It is not exact dynamic VOI, a posterior confidence
bound or a claim of near-optimal active learning.
"""
import time,random,copy
import numpy as np
from . import data,acquisition as a
from vendor.planner import actions,posterior

class Design:
    """Precomputed occupancy coefficients; constructor never accepts training labels
    or private runtime data. The reference-state grid is not a deployment distribution.
    """
    def __init__(self,p):
        tic=time.perf_counter();self.cells=a.all_cells();self.idx={c:i for i,c in enumerate(self.cells)}
        self.states=[];feats=[];costs=[];valid=[];self.n=8
        for shared in (False,True):
            acts=actions(shared,p['step_cap'])
            for ages in p['selection']['design_ages']:
                pp=posterior(tuple(ages),p['hazards'])
                for b in p['selection']['design_budgets']:
                    for q in range(5):
                        for m in range(8):
                            self.states.append({'shared':shared,'ages':list(ages),'budget':b,'q':q,'memory':m})
                            xx=np.zeros((len(acts),len(self.cells)),dtype=float)
                            for ai,act in enumerate(acts):
                                for z in range(8):
                                    updated=(m&(~act.mask&7))|(z&act.mask)
                                    c=a.canonical_cell((q,updated,z))
                                    if c[1]!=c[2]:xx[ai,self.idx[c]]+=pp[m,z]
                            feats.append(xx);costs.append([p['credit_price']*act.cost for act in acts])
                            valid.append([act.cost<=b for act in acts])
        self.X=np.stack(feats);self.base_cost=np.array(costs);self.valid=np.array(valid,dtype=bool)
        self.build_seconds=time.perf_counter()-tic
    def values(self,table):
        table=np.asarray(table,dtype=float)
        if table.shape!=(5,8,8) or not np.isfinite(table).all() or np.any(table<0) or np.any(table>1):raise ValueError('invalid loss')
        return np.array([table[c] for c in self.cells])
    def action_scores(self,table):
        v=self.values(table)
        out=np.einsum('sac,c->sa',self.X,v,optimize=False)+self.base_cost
        out[~self.valid]=np.inf;return out
    def rank(self,table,candidates,method):
        if method not in ('occupancy','decision'):raise ValueError('unknown selector')
        if not candidates:return []
        ix=[self.idx[c] for c in candidates];v=self.values(table);q=self.action_scores(table)
        best=np.argmin(np.round(q,12),axis=1);ss=np.arange(q.shape[0])
        xx=self.X[:,:,ix]
        if method=='occupancy':score=xx[ss,best,:].mean(axis=0)
        else:
            # Change one unmeasured canonical cell coherently over its public
            # irrelevant-coordinate copies, not multiple arbitrary cells at once.
            low=q[:,:,None]-xx*v[ix][None,None,:]
            high=q[:,:,None]+xx*(1-v[ix])[None,None,:]
            regrets=np.maximum(low[ss,best,:]-np.min(low,axis=1),high[ss,best,:]-np.min(high,axis=1))
            score=np.maximum(regrets,0).mean(axis=0)
        # All atoms cost the same number of catalogs; division would not affect rank.
        ranked=[(c,float(score[i])) for i,c in enumerate(candidates)]
        return sorted(ranked,key=lambda cs:(-round(cs[1],12),cs[0]))

def learn_panel(seeds,p,design,method,budgets,seed):
    if method not in ('single','full','random','occupancy','decision'):raise ValueError('learning method')
    if not budgets or any(type(b) is not int or not 0<=b<=100 for b in budgets):raise ValueError('budget')
    oracle=a.PaidOracle(seeds);learner=a.Learner(oracle);tic=time.perf_counter();learner.initialize_singles()
    base_seconds=time.perf_counter()-tic;select_seconds=0.;learn_start=time.perf_counter()
    candidates=a.interaction_cells();order=candidates.copy();random.Random(seed).shuffle(order)
    checkpoint={};events=[];selected=[]
    if method=='single':budgets=[0]
    if method=='full':budgets=[100]
    maximum=max(budgets)
    def save(k):
        snap=learner.snapshot();snap.update(selected_cells=[list(c) for c in selected],learner=method,
             selector_seconds=select_seconds,initial_fit_seconds=base_seconds,
             acquisition_elapsed_seconds=base_seconds+time.perf_counter()-learn_start,
             design_build_seconds=design.build_seconds if method in ('decision','occupancy') else 0.,
             label_budget=k,selection_event_count=len(events))
        checkpoint[str(k)]=snap
    if 0 in budgets:save(0)
    for i in range(maximum):
        ts=time.perf_counter()
        if method=='random':cell=next(c for c in order if c in candidates);score=None
        elif method=='full':cell=candidates[0];score=None
        else:cell,score=design.rank(learner.table(),candidates,method)[0]
        dt=time.perf_counter()-ts;select_seconds+=dt
        before=oracle.total_workflows;observed_before=data.digest(sorted(a.key(c) for c in learner.observed))
        obs=learner.buy(cell);selected.append(cell);candidates.remove(cell)
        events.append({'index':i,'cell':list(cell),'score':score,'observed_keys_before_sha256':observed_before,
             'label_n':obs['n'],'label_failures':obs['failures'],'workflow_count_before':before,
             'workflow_count_after':oracle.total_workflows,'selection_seconds':dt})
        if i+1 in budgets:save(i+1)
    return {'method':method,'training_seeds':list(seeds),'selection':events,'checkpoints':checkpoint,
            'ledger':oracle.events,'total_physical_workflows':oracle.total_workflows,
            'reference_workflows':oracle.reference_executions,'label_workflows':oracle.label_executions,
            'selected_interactions':len(selected),'selector_seconds':select_seconds}
