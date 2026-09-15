"""Executable in-process JSON reference API: pagination, status, inventory.
This is a new controlled environment, not an external benchmark or live service.
"""
import copy,json

CHANNEL_KEYS=('first_page','active_code','stock_semantics')

def semantics(modes):
    return dict(first_page=int(modes[0]),active_code=1-int(modes[1]),stock_semantics='gross' if modes[2] else 'net')

class World:
    def __init__(self,rows):
        self.rows=copy.deepcopy(rows);self.modes=(0,0,0)
        if len({x['sku'] for x in rows})!=len(rows):raise ValueError('Duplicate SKU')
    def set_modes(self,modes):
        if len(modes)!=3 or any(type(x) is not int or x not in (0,1) for x in modes):raise ValueError('Invalid mode')
        self.modes=tuple(modes)
    def call(self,path,args):
        # JSON round trip isolates callers from internal mutable objects.
        args=json.loads(json.dumps(args));s=semantics(self.modes)
        if path=='/catalog/items':
            page=args['page']-s['first_page'];size=args['page_size']
            if page<0:return {'error':'PAGE_BEFORE_FIRST'}
            status=args['status_code'];want_active=status==s['active_code']
            rows=[r for r in self.rows if r['active']==want_active]
            part=rows[page*size:(page+1)*size]
            return {'items':[{'sku':r['sku'],'category':r['category']} for r in part],
                    'has_more':(page+1)*size<len(rows)}
        if path=='/inventory/batch':
            table={r['sku']:r for r in self.rows};items=[]
            for sku in args['skus']:
                if sku not in table:return {'error':'UNKNOWN_SKU'}
                r=table[sku];v=r['physical'] if self.modes[2] else max(0,r['physical']-r['reserved'])
                items.append({'sku':sku,'stock_value':v,'reserved':r['reserved']})
            return {'items':items}
        raise ValueError('Unknown bounded API path')
    def _calibration(self,j):
        if j==0:
            origin=self.modes[0]
            return {'channel':0,'fixture':'known first item CAL-A then CAL-B',
              'page0':{'error':'PAGE_BEFORE_FIRST'} if origin else {'first_sku':'CAL-A'},
              'page1':{'first_sku':'CAL-A' if origin else 'CAL-B'}}
        if j==1:
            return {'channel':1,'fixture':'known active CANARY-A and inactive CANARY-I',
                'active_example_code':1-self.modes[1],'inactive_example_code':self.modes[1]}
        if j==2:
            return {'channel':2,'fixture':'known physical=10 reserved=4',
                'physical':10,'reserved':4,'stock_value':10 if self.modes[2] else 6}
        raise ValueError('Unknown calibration channel')
    def calibration_packet(self,p):
        # One abstract response can contain multiple scoped calibration outcomes.
        return {'packet_id':p['id'],'credit_cost':p['cost'],'observations':[self._calibration(j) for j in p['cover']]}
    def initial_calibration(self):
        return [self.calibration_packet({'id':'initial_all','cost':6,'cover':[0,1,2]})]


def decode_receipts(receipts):
    out={}
    for r in receipts:
        for obs in r['observations']:
            j=obs['channel']
            if j==0:
                if obs['page0'].get('first_sku')=='CAL-A':out['first_page']=0
                elif obs['page1'].get('first_sku')=='CAL-A':out['first_page']=1
                else:raise ValueError('Unidentified page convention')
            elif j==1:
                if obs['active_example_code'] not in (0,1) or obs['inactive_example_code']!=1-obs['active_example_code']:raise ValueError('Invalid status receipt')
                out['active_code']=obs['active_example_code']
            elif j==2:
                if obs['stock_value']==obs['physical']:out['stock_semantics']='gross'
                elif obs['stock_value']==obs['physical']-obs['reserved']:out['stock_semantics']='net'
                else:raise ValueError('Invalid stock receipt')
            else:raise ValueError('Unknown receipt channel')
    return out

class ProbeBudget:
    """Credits are a controlled rate quota, not time or currency. Failed admission never queries."""
    def __init__(self,world,packets,budget,step_cap):
        self.world=world;self.packets={p['id']:copy.deepcopy(p) for p in packets}
        self.remaining=budget;self.cap=step_cap;self.transactions=[]
    def read(self,ids):
        if len(set(ids))!=len(ids) or any(i not in self.packets for i in ids):raise ValueError('Unknown or duplicate packet')
        cost=sum(self.packets[i]['cost'] for i in ids)
        if cost>self.remaining or cost>self.cap:raise ValueError('HARD_PROBE_BUDGET_EXCEEDED')
        before=self.remaining
        result=[self.world.calibration_packet(self.packets[i]) for i in ids]
        self.remaining-=cost
        self.transactions.append({'ids':list(ids),'before':before,'after':self.remaining,'cost':cost})
        return result


def gold(rows,task):
    """Evaluator only: direct canonical rows, never called by the scheduler/compiler."""
    q=task['type']
    if q==1:
        tab={r['sku']:r for r in rows}
        return {'available_total':sum(max(0,tab[s]['physical']-tab[s]['reserved']) for s in task['skus'])}
    selected=[r for r in rows if r['active'] and r['category']==task['category']]
    if q==2:selected=[r for r in selected if max(0,r['physical']-r['reserved'])>=task['minimum']]
    return {'skus':sorted(r['sku'] for r in selected)}
