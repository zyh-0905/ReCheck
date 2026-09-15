"""Exact expected costs and public opportunity, not LLM accuracy or currency."""
import itertools,copy
import numpy as np
from . import protocol
from vendor.recheck_core import mismatch_probability

METHODS=('recheck','myopic','ttl','always','never')

def expected_policy(method,s,actual_hazard):
 """Forward expectation on (age, task) separately for each channel.
 Initial task is uniform; age starts at one after a shared exact calibration.
 Independence, exogenous Markov tasks, additive mismatch and precise probes required.
 """
 H=s['steps'];dp=protocol.solve(s);P=np.array(s['transition']);W=np.array(s['weights']);c=np.array(s['probe_price'])
 loss=probes=probe_cost=0.
 for j in range(2):
  dist=np.zeros((H+2,4));dist[1]=.25
  for t in range(H):
   nxt=np.zeros_like(dist)
   for age in range(1,t+2):
    for q in range(4):
     mass=dist[age,q]
     if mass==0:continue
     take=bool(protocol.choose(method,np.array([age,age]),q,H-t,dp,s)[j]);after=0 if take else age
     loss+=mass*W[q,j]*mismatch_probability(after,actual_hazard)
     probes+=mass*take;probe_cost+=mass*take*c[j]
     nxt[after+1]+=mass*P[q]
   dist=nxt
 return {'semantic_loss':float(loss),'probe_count':float(probes),'probe_cost':float(probe_cost),'objective':float(loss+probe_cost)}

def factorial_report(horizons=None):
 p=protocol.load_protocol();g=p['offline_grid'];rows=[]
 for H,h,c,rho,fac in itertools.product(horizons or g['horizons'],g['hazards'],g['prices'],g['persistence'],g['actual_multipliers']):
  s=protocol.policy_spec({'persistence':rho,'probe_price':[c,c]},p);s['steps']=H;s['assumed_hazards']=[h,h]
  actual=min(.5,h*fac);vals={m:expected_policy(m,s,actual) for m in METHODS}
  a=vals['recheck']['objective'];b=vals['myopic']['objective']
  rows.append({'horizon':H,'assumed_hazard':h,'actual_hazard':actual,'actual_multiplier':fac,'probe_price':c,'persistence':rho,
              'metrics':vals,'recheck_minus_myopic':a-b,'relative_reduction':(b-a)/b if b else None})
 return {'label':'EXACT_FINITE_MODEL_EXPECTATION_NOT_LLM_NOT_CURRENCY','remote_model_calls':0,'sampling':False,'rows':rows,
         'scope':'All predeclared cells retained. This instantiates classical finite-horizon decision theory; no new general theorem claimed.'}

def opportunity(cell,p):
 """No hidden world generation, labels or outcomes. Expected bit difference from check-time gap."""
 s=protocol.policy_spec(cell,p);dp=protocol.solve(s);ages={m:np.zeros(2,int) for m in p['methods']};stamps={m:[0,0] for m in ages}
 changes=0;expected=0.;detail=[]
 for t,q in enumerate(protocol.task_types(cell,p)):
  act={}
  for m in ages:
   ages[m]+=1;act[m]=protocol.choose(m,ages[m],q,p['steps']-t,dp,s)
   for j in np.flatnonzero(act[m]):stamps[m][int(j)]=t+1
   ages[m][act[m]]=0
  a,b=p['methods'];different=not np.array_equal(act[a],act[b]);changes+=int(different)
  probs=[mismatch_probability(abs(stamps[a][j]-stamps[b][j]),cell['actual_hazard']) for j in range(2) if s['weights'][q][j]>0]
  prob=1-float(np.prod([1-x for x in probs]));expected+=prob
  detail.append({'step':t,'task_type':q,'probe_diff':different,'expected_relevant_bit_difference':prob})
 return {'stream':cell['stream'],'condition':cell['condition'],'action_differences':changes,
         'expected_relevant_semantic_differences':expected,'hidden_worlds_generated':0,'rows':detail}

def preflight(p=None):
 p=p or protocol.load_protocol();cells=[]
 for c in p['streams'][::4]:
  s=protocol.policy_spec(c,p);vals={m:expected_policy(m,s,c['actual_hazard']) for m in METHODS}
  b=vals['myopic']['objective'];a=vals['recheck']['objective']
  cells.append({'condition':c['condition'],'metrics':vals,'relative_reduction':(b-a)/b if b else 0.})
 opp=[opportunity(c,p) for c in p['streams']]
 gains=[c['relative_reduction'] for c in cells if c['condition'].startswith('matched')]
 potential=sum(x['expected_relevant_semantic_differences'] for x in opp)
 gate=max(gains)>=p['gate']['minimum_matched_relative_gain'] and potential>=p['gate']['minimum_expected_relevant_differences']
 return {'pass':bool(gate),'conditions':cells,'streams':opp,'expected_relevant_differences_total':potential,
         'gate_uses_realized_hidden_modes':False,'gate_uses_llm_results':False,'new_remote_calls':0,
         'gate_scope':'Feasibility under model assumptions only. Misspecification and no-drift losses do not veto or remove negative controls.'}
