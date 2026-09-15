"""Public scenario grammar and evaluator-only private catalogs.
No learned selector accepts rows, true runtime modes, answers, or evaluation seeds.
"""
from pathlib import Path
import json,random,hashlib,math
ROOT=Path(__file__).resolve().parents[1]
RELEVANT=((0,1),(2,),(0,1,2),(0,1,2),(0,1,2))

def protocol():return json.loads((ROOT/'configs/protocol.json').read_text(encoding='utf-8'))
def canonical(o):return json.dumps(o,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()
def digest(o):return hashlib.sha256(canonical(o)).hexdigest()
def decode(m):
    if type(m) is not int or not 0<=m<8:raise ValueError('mode must be an int 0..7')
    return tuple((m>>j)&1 for j in range(3))
def memory(m):
    from vendor.r4.environment import semantics
    return semantics(decode(m))
def encode_memory(m):
    if type(m.get('first_page')) is not int or m['first_page'] not in (0,1):raise ValueError('page')
    if type(m.get('active_code')) is not int or m['active_code'] not in (0,1):raise ValueError('code')
    if m.get('stock_semantics') not in ('gross','net'):raise ValueError('stock')
    return m['first_page']+2*(1-m['active_code'])+4*int(m['stock_semantics']=='gross')
def make_rows(seed,profile='standard',n=23):
    if profile not in ('standard','reservation_free_clustered') or n<5:raise ValueError('profile/size')
    r=random.Random(seed)
    rows=[{'sku':f'SKU-{i:03d}','physical':r.randint(0,25),'reserved':r.randint(0,12),
           'category':r.choice(['A','B','C']),'active':bool(r.getrandbits(1))} for i in range(n)]
    if profile=='reservation_free_clustered':
        for x in rows:x['reserved']=0
        rows.sort(key=lambda x:(x['category'],x['sku']))
    return rows

def make_task(q,rows,seed):
    if type(q) is not int or not 0<=q<5:raise ValueError('q')
    r=random.Random(seed)
    return {'type':q if q<2 else 2,'category':r.choice(['A','B','C']),
            'minimum':(3,12,22)[q-2] if q>=2 else 3,
            'skus':sorted(r.sample([x['sku'] for x in rows],5))}
def transition(rho,qn=5):
    return [[rho if q==k else (1-rho)/(qn-1) for k in range(qn)] for q in range(qn)]
def split_ids(p):
    n=p['calibration_catalogs_per_panel'];panels=p['calibration_panels']
    per=len(p['conditions'])*p['streams_per_condition']
    return {'calibration':[list(range(p['calibration_seed']+i*1000,p['calibration_seed']+i*1000+n)) for i in range(panels)],
            'evaluation':list(range(p['evaluation_seeds']['data'],p['evaluation_seeds']['data']+panels*per))}
def cases(p):
    out=[];P=transition(p['persistence']);n=p['streams_per_condition'];conditions=p['conditions']
    for panel in range(p['calibration_panels']):
        for ci,c in enumerate(conditions):
            for rep in range(n):
                sid=(panel*len(conditions)+ci)*n+rep
                seeds={k:v+sid for k,v in p['evaluation_seeds'].items()}
                rows=make_rows(seeds['data'],c['data_profile'],p['catalog_size'])
                tr=random.Random(seeds['tasks']);wr=random.Random(seeds['modes']);m=wr.randrange(8);initial=m;q=rep%5
                steps=[]
                for step in range(p['steps']):
                    if step:q=tr.choices(range(5),P[q])[0]
                    for j in range(3):
                        if wr.random()<c['actual_hazard']:m^=1<<j
                    steps.append({'q':q,'task':make_task(q,rows,seeds['tasks']*1000+step),'true_mode':m})
                out.append({'id':sid,'panel':panel,'condition':c['name'],'profile':c['data_profile'],'seeds':seeds,
                            'initial_mode':initial,'rows':rows,'steps':steps})
    return out

def correct_answer(rows,task):
    """Evaluator only; used as supervised truth for *training*, not for online choices."""
    if task['type']==1:
        t={x['sku']:x for x in rows}
        return {'available_total':sum(max(0,t[s]['physical']-t[s]['reserved']) for s in task['skus'])}
    xs=[x for x in rows if x['active'] and x['category']==task['category']]
    if task['type']==2:xs=[x for x in xs if max(0,x['physical']-x['reserved'])>=task['minimum']]
    return {'skus':sorted(x['sku'] for x in xs)}

def independent_execute(rows,task,cached,true):
    """Does not call World, rule_plan or worker.execute. Audit only."""
    m=decode(cached);z=decode(true)
    if task['type']==1:
        tab={x['sku']:x for x in rows};xs=[tab[s] for s in task['skus']]
    else:
        if m[0]<z[0]:return {'error':'PAGE_BEFORE_FIRST'}
        xs=[x for x in rows if x['active']==(m[1]==z[1])]
        xs=[x for x in xs[3*(m[0]-z[0]):] if x['category']==task['category']]
    if task['type']==0:return {'skus':sorted(x['sku'] for x in xs)}
    def free(x):
        raw=x['physical'] if z[2] else max(0,x['physical']-x['reserved'])
        return max(0,raw-(x['reserved'] if m[2] else 0))
    if task['type']==1:return {'available_total':sum(free(x) for x in xs)}
    return {'skus':sorted(x['sku'] for x in xs if free(x)>=task['minimum'])}
