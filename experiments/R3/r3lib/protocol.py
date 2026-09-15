"""Frozen R3 design. Scheduling consumes only public task type, ages and assumptions."""
from pathlib import Path
import copy,json
import numpy as np
from vendor.recheck_core import solve_refresh_dp,mismatch_probability
ROOT=Path(__file__).resolve().parents[1]

def load_protocol():
 p=json.loads((ROOT/'configs/r3_protocol.json').read_text(encoding='utf-8'))
 if p['methods']!=['recheck','myopic'] or p['steps']!=12 or len(p['streams'])!=16:raise ValueError('Frozen design changed')
 if p['main_calls']!=len(logical_ids(p)):raise ValueError('Incorrect main cap')
 return p

def policy_spec(cell,p):
 rho=cell['persistence'];P=np.full((4,4),(1-rho)/3);np.fill_diagonal(P,rho)
 return {'steps':p['steps'],'weights':copy.deepcopy(p['weights']),'transition':P.tolist(),
         'assumed_hazards':list(p['assumed_hazards']),'probe_price':list(cell['probe_price']),'ttl_age':3}

def solve(s):
 return solve_refresh_dp(np.array(s['weights']),np.array(s['transition']),np.array(s['assumed_hazards']),np.array(s['probe_price']),s['steps'])

def choose(method,age,q,remaining,dp,s):
 age=np.asarray(age,int)
 if method=='recheck':return dp.action(remaining,age,q)
 if method=='myopic':return np.array(s['weights'])[q]*np.array([mismatch_probability(int(a),h) for a,h in zip(age,s['assumed_hazards'])])>np.array(s['probe_price'])
 if method=='ttl':return age>=s['ttl_age']
 if method=='always':return np.ones(2,bool)
 if method=='never':return np.zeros(2,bool)
 raise ValueError('Unknown strategy')

def task_types(cell,p):
 rng=np.random.default_rng(cell['task_seed']);s=policy_spec(cell,p);q=cell['initial_task'];out=[]
 for t in range(p['steps']):
  if t:q=int(rng.choice(4,p=s['transition'][q]))
  out.append(q)
 return out

def make_cases(p):
 out=[]
 for c in p['streams']:
  dr=np.random.default_rng(c['data_seed']);wr=np.random.default_rng(c['world_seed'])
  cents=dr.integers(100,10001,size=20).tolist();mode=wr.integers(0,2,size=2);initial=mode.tolist();tasks=[]
  for q in task_types(c,p):
   mode=mode^(wr.random(2)<c['actual_hazard']).astype(int)
   tasks.append({'type':q,'cutoff':int(dr.integers(5,15)),'modes':mode.tolist()})
  out.append({'stream':c['stream'],'condition':c['condition'],'cents':cents,'initial_modes':initial,'tasks':tasks})
 return out

def logical_ids(p):
 ids=[]
 for c in p['streams']:
  for t in range(p['steps']):
   for m in p['methods']:
    stem=f"r3/rc/{c['stream']}/{t}/{m}"
    ids.append(stem+'/primary')
    if t==p['repeat_step']:ids.append(stem+'/repeat')
 return ids
