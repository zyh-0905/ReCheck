"""Mechanism coverage on all fixed cells. Scripted results are NOT LLM results."""
import sys,json,tempfile,csv,copy,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from core.cases import make_cases
from core.db import Store,CONFIG_FIELDS,BATCH_FIELDS
from core.score import grade
from core.common import write

POLICIES=['full_id','minimal_id','full_intent','minimal_intent','reresolve_minimal','row_cas','selection_guard','guard_retry']
def query(c,s):
 if c['goal_mode']=='literal':
  r=s.call('get_config' if c['family']=='routing' else 'get_batch',{'id':c['target_id']});return {'record':r['value'],'selection_token':None}
 r=s.call('resolve_service',{'service':c['key']}) if c['family']=='routing' else s.call('select_batch',{'lane':c['key'],'min_units':4})
 return r['value']
def args_for(c,selection,full=False,rowcheck=False,selectcheck=False):
 r=selection['record'];a={'id':r['id'],('max_attempts' if c['family']=='routing' else 'ready_after'):c['wanted']}
 if full:
  a={k:r[k] for k in (CONFIG_FIELDS if c['family']=='routing' else BATCH_FIELDS)}|a
 if rowcheck:a['expected_version']=r['version']
 if selectcheck and c['goal_mode']=='current':
  a['expected_selection_token']=selection['selection_token']
  if c['family']=='routing':a['service']=c['key']
  else:a.update(lane_query=c['key'],min_units_query=4)
 return a

def episode(c,policy):
 with tempfile.TemporaryDirectory() as d:
  s=Store(c,Path(d)/'local.sqlite');tic=time.perf_counter()
  try:
   v=query(c,s)
   if policy=='reresolve_minimal':v=query(c,s)
   a=args_for(c,v,full=policy.startswith('full'),rowcheck=policy in ('row_cas','selection_guard','guard_retry'),selectcheck=policy in ('selection_guard','guard_retry'))
   response=s.call('update_config' if c['family']=='routing' else 'update_batch',a)
   if policy=='guard_retry' and not response['ok']:
    v=query(c,s);a=args_for(c,v,rowcheck=True,selectcheck=True);response=s.call('update_config' if c['family']=='routing' else 'update_batch',a)
   claim=False
   if response['ok']:
    if policy.endswith('intent') or policy in ('reresolve_minimal','guard_retry'):
     current=query(c,s);record=current['record'];claim=record['id']==a['id']
    else:
     record=s.call('get_config' if c['family']=='routing' else 'get_batch',{'id':a['id']})['value'];claim=True
    claim=claim and record[('max_attempts' if c['family']=='routing' else 'ready_after')]==c['wanted']
   g=grade(c,s.initial,s.events,s.world())
   return {'evidence_kind':'SCRIPTED_MECHANISM_NOT_LLM','case_id':c['id'],'family':c['family'],'condition':c['change'],'intent':c['goal_mode'],'policy':policy,'claim':claim,'false_confirmation':claim and not g['trace_safe_success'],'initial':s.initial,'events':copy.deepcopy(s.events),'final':s.world(),'score':g,'elapsed_seconds':time.perf_counter()-tic}
  finally:s.close()

def main(out):
 out=Path(out)
 if out.exists():raise ValueError('Refuse to overwrite previous research results')
 out.mkdir(parents=True)
 rows=[]
 for c in make_cases():
  for p in POLICIES:
   r=episode(c,p);write(out/'traces'/f'{c["id"]}_{p}.json',r,once=True)
   rows.append({k:r[k] for k in ('case_id','family','condition','intent','policy','claim','false_confirmation')}|{k:v for k,v in r['score'].items() if k!='violations'})
 with (out/'cases.csv').open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
 summary=[]
 for p in POLICIES:
  group=[r for r in rows if r['policy']==p];summary.append({'policy':p,'cases':len(group),**{k:sum(int(r[k]) for r in group) for k in ('goal_final','final_state_clean','trace_safe_success','wrong_write','claim','false_confirmation','tool_calls','conflicts')}})
 write(out/'summary.json',summary);print(json.dumps(summary,indent=2))
if __name__=='__main__':main(sys.argv[1])
