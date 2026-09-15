"""Frozen JSON plan compiler and bounded, deterministic API execution.
No arbitrary code. The deterministic compiler uses exactly the LLM's public input.
"""
from .environment import CHANNEL_KEYS,semantics

SYSTEM='Compile the public inventory request into a JSON plan. Follow the supplied cached interface evidence exactly. Return only the required JSON object; do not claim to know unobserved updates.'
RELEVANT=((0,1),(2,),(0,1,2))


def make_view(task,memory):
    q=task['type'];kind=('catalog_ids','stock_sum','available_ids')[q]
    request={'workflow':kind}
    if q in (0,2):request.update(category=task['category'],page_size=3)
    if q==1:request['skus']=list(task['skus'])
    if q==2:request['minimum_available']=task['minimum']
    descriptions={0:'List every active SKU in the requested category, in sorted order.',
      1:'Sum free inventory for the explicitly listed SKUs. Free inventory excludes reserved units and is clamped at zero.',
      2:'List active SKUs in the category with at least the requested free inventory. Enumerate every catalogue page, join inventory by SKU, filter and sort.'}
    evidence={CHANNEL_KEYS[j]:memory[CHANNEL_KEYS[j]] for j in RELEVANT[q]}
    keys=list(request)+list(evidence)
    return {'request':request,'task':descriptions[q],'evidence':evidence,'allowed_keys':keys,
      'tools':{'catalogue':'catalog.items(page,page_size,status_code) paginates after filtering by active status. Use cached first_page and active_code; executor fetches until has_more=false.',
       'inventory':'inventory.batch(skus) returns stock_value and reserved. gross means subtract reserved; net means already free. Renderer clamps at zero.',
       'execution':'Only the named bounded workflow is allowed. A deterministic executor paginates, joins, filters, sorts and presents output; do not supply final answers.'},
      'instruction':'Return exactly allowed_keys. Copy public workflow/request values. For interface arguments use evidence. first_page/active_code are integer 0 or 1, stock_semantics is net or gross. No extra or unused fields.'}


def rule_plan(view):return {**view['request'],**view['evidence']}

def valid_plan(plan,view):
    if not isinstance(plan,dict) or set(plan)!=set(view['allowed_keys']):return False
    if plan.get('workflow')!=view['request']['workflow']:return False
    for k in ('first_page','active_code'):
        if k in plan and (type(plan[k]) is not int or plan[k] not in (0,1)):return False
    if 'stock_semantics' in plan and plan['stock_semantics'] not in ('net','gross'):return False
    for k,v in view['request'].items():
        if k=='workflow':continue
        # Public request changes are plan errors, not silent normalization.
        if type(plan[k]) is not type(v) or plan[k]!=v:return False
    return True


def execute(world,view,plan):
    trace=[]
    if not valid_plan(plan,view):return {'error':'INVALID_PLAN'},trace
    def call(path,args):
        result=world.call(path,args);trace.append({'path':path,'args':args,'result':result});return result
    if plan['workflow']=='stock_sum':
        inv=call('/inventory/batch',{'skus':plan['skus']})
        if 'error' in inv:return inv,trace
        val=sum(max(0,r['stock_value']-(r['reserved'] if plan['stock_semantics']=='gross' else 0)) for r in inv['items'])
        return {'available_total':val},trace
    rows=[]
    for step in range(64):
        data=call('/catalog/items',{'page':plan['first_page']+step,'page_size':plan['page_size'],'status_code':plan['active_code']})
        if 'error' in data:return data,trace
        rows.extend(data['items'])
        if not data['has_more']:break
    else:return {'error':'PAGE_LIMIT'},trace
    chosen=[r for r in rows if r['category']==plan['category']]
    if plan['workflow']=='available_ids':
        inv=call('/inventory/batch',{'skus':[r['sku'] for r in chosen]})
        if 'error' in inv:return inv,trace
        chosen=[r for r in inv['items'] if max(0,r['stock_value']-(r['reserved'] if plan['stock_semantics']=='gross' else 0))>=plan['minimum_available']]
    return {'skus':sorted(r['sku'] for r in chosen)},trace


def freshness(task,memory,modes):
    truth=semantics(modes);use=RELEVANT[task['type']]
    stale=[j for j in use if memory.get(CHANNEL_KEYS[j])!=truth[CHANNEL_KEYS[j]]]
    return {'relevant_channels':list(use),'stale_channels':stale,'semantic_mismatches':len(stale)}
