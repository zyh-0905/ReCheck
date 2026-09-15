"""Deterministic independent catalogs; private data never passed to a scheduler."""
from pathlib import Path
import json,random
from vendor.r4.environment import semantics

ROOT=Path(__file__).resolve().parents[1]
RELEVANT=((0,1),(2,),(0,1,2),(0,1,2),(0,1,2))

def load_protocol():
    return json.loads((ROOT/'configs/protocol.json').read_text(encoding='utf-8'))

def decode(i):
    if type(i) is not int or not 0<=i<8: raise ValueError('mode index must be 0..7')
    return tuple((i>>j)&1 for j in range(3))

def encode(bits):
    if len(bits)!=3 or any(type(b) is not int or b not in (0,1) for b in bits):raise ValueError('invalid bits')
    return sum(b<<j for j,b in enumerate(bits))

def memory(i):
    return semantics(decode(i))

def encode_memory(m):
    if type(m.get('first_page')) is not int or m['first_page'] not in (0,1):raise ValueError('page')
    if type(m.get('active_code')) is not int or m['active_code'] not in (0,1):raise ValueError('status')
    if m.get('stock_semantics') not in ('gross','net'):raise ValueError('inventory')
    return encode((m['first_page'],1-m['active_code'],int(m['stock_semantics']=='gross')))

def make_rows(seed,profile='standard',n=23):
    if profile not in ('standard','reservation_free_clustered') or n<5:raise ValueError('catalog profile/size')
    rng=random.Random(seed)
    rows=[]
    for i in range(n):
        rows.append({'sku':f'SKU-{i:03d}','physical':rng.randint(0,25),'reserved':rng.randint(0,12),
                    'category':rng.choice(['A','B','C']),'active':bool(rng.getrandbits(1))})
    if profile=='reservation_free_clustered':
        for r in rows:r['reserved']=0
        rows.sort(key=lambda r:(r['category'],r['sku']))
    return rows

def make_task(q,rows,seed):
    if type(q) is not int or not 0<=q<5:raise ValueError('task class')
    rng=random.Random(seed)
    return {'type':q if q<2 else 2,'category':rng.choice(['A','B','C']),
            'minimum':(3,12,22)[q-2] if q>=2 else 3,
            'skus':sorted(rng.sample([r['sku'] for r in rows],5))}

def transition(rho,qn=5):
    if not 0<=rho<=1 or qn<2:raise ValueError('transition')
    return [[rho if k==q else (1-rho)/(qn-1) for k in range(qn)] for q in range(qn)]

def split_ids(p):
    return {'calibration':list(range(p['calibration_seed'],p['calibration_seed']+p['calibration_catalogs'])),
            'validation':list(range(p['validation_seed'],p['validation_seed']+p['validation_catalogs'])),
            'evaluation':list(range(p['evaluation_seeds']['data'],p['evaluation_seeds']['data']+
                                    len(p['conditions'])*p['streams_per_condition']))}

def make_cases(p):
    """Return private environment cases to the runner, never to the policy object."""
    out=[];P=transition(p['persistence'])
    for ci,c in enumerate(p['conditions']):
        for rep in range(p['streams_per_condition']):
            sid=ci*p['streams_per_condition']+rep
            seeds={k:v+sid for k,v in p['evaluation_seeds'].items()}
            rows=make_rows(seeds['data'],c['data_profile'],p['catalog_size'])
            tr=random.Random(seeds['tasks']);wr=random.Random(seeds['modes'])
            m=wr.randrange(8);initial=m;q=rep%5;tasks=[]
            for t in range(p['steps']):
                if t:q=tr.choices(range(5),P[q])[0]
                for j in range(3):
                    if wr.random()<c['actual_hazard']:m^=1<<j
                # Per-step public parameters are drawn without looking at hidden state.
                task=make_task(q,rows,seeds['tasks']*1000+t)
                tasks.append({'q':q,'task':task,'true_mode':m})
            out.append({'id':sid,'condition':c['name'],'profile':c['data_profile'],
                        'seeds':seeds,'initial_mode':initial,'rows':rows,'steps':tasks})
    return out
