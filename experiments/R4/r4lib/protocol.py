"""Frozen tasks; scheduling receives no future tasks or realized hidden values."""
from pathlib import Path
import json,random,copy
from .model import Solver
ROOT=Path(__file__).resolve().parents[1]

def load_protocol():
    p=json.loads((ROOT/'configs/r4_protocol.json').read_text())
    if p['main_calls']!=len(logical_ids(p)) or p['main_calls']!=408:raise ValueError('Frozen call cap mismatch')
    if p['steps']!=8 or len(p['streams'])!=12 or p['methods']!=['recheck_joint','bundle_rollout','bundle_myopic','age_paced']:raise ValueError('Frozen design changed')
    return p

def spec(cell,p):
    rho=cell['persistence'];packets=[{'id':f's{j}','cover':[j],'cost':2} for j in range(3)]
    if cell['overlap']:packets +=[{'id':'p01','cover':[0,1],'cost':3},{'id':'p12','cover':[1,2],'cost':3}]
    return {'hazards':list(p['assumed_hazards']),'weights':copy.deepcopy(p['weights']),
      'transition':[[rho if k==q else (1-rho)/2 for k in range(3)] for q in range(3)],
      'packets':packets,'step_cap':p['step_cap'],'price':cell['price']}

def task_types(cell,p):
    rng=random.Random(cell['task_seed']);q=cell['initial_task'];out=[];P=spec(cell,p)['transition']
    for t in range(p['steps']):
        if t:q=rng.choices(range(3),P[q])[0]
        out.append(q)
    return out

def make_cases(p):
    out=[]
    for cell in p['streams']:
        dr=random.Random(cell['data_seed']);wr=random.Random(cell['world_seed'])
        rows=[]
        for i in range(23):
            physical=dr.randint(0,25);reserved=dr.randint(0,12)
            rows.append({'sku':f"SKU-{i:03d}",'category':dr.choice(['A','B','C']),'active':bool(dr.getrandbits(1)),
                         'physical':physical,'reserved':reserved})
        modes=[wr.randrange(2) for _ in range(3)];initial=list(modes);tasks=[]
        for q in task_types(cell,p):
            modes=[m^int(wr.random()<cell['actual_hazard']) for m in modes]
            tasks.append({'type':q,'category':dr.choice(['A','B','C']),'minimum':dr.randint(2,14),
              'skus':sorted(dr.sample([r['sku'] for r in rows],5)),'modes':list(modes)})
        out.append({'stream':cell['stream'],'condition':cell['condition'],'rows':rows,'initial_modes':initial,'tasks':tasks})
    return out

def order(cell,p,t):
    methods=list(p['methods']);random.Random(p['order_seed']+cell['stream']).shuffle(methods)
    k=t%len(methods);return methods[k:]+methods[:k]

def logical_ids(p):
    out=[]
    for cell in p['streams']:
        for t in range(p['steps']):
            for m in order(cell,p,t):
                stem=f"r4/api/{cell['stream']}/{t}/{m}"
                out.append(stem+'/primary')
                if t==p['repeat_step'] and m in p['repeat_methods']:out.append(stem+'/repeat')
    return out
