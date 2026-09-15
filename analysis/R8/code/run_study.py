#!/usr/bin/env python3
"""Researcher-owned execution, no user run or API key required."""
import sys,argparse,json,csv,hashlib,platform,time
from pathlib import Path
import bootstrap
from boundary import run_case,all_specs,score_write

def dump(path,data):
 path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(data,ensure_ascii=False,sort_keys=True,indent=2,allow_nan=False))
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--out',required=True);a=ap.parse_args();root=Path(a.out)
 if root.exists():raise SystemExit('Refusing to overwrite existing study directory')
 root.mkdir(parents=True);tic=time.perf_counter();rows=[]
 for i,spec in enumerate(all_specs()):
  r=run_case(*spec)
  for w in r['writes']:
   assert score_write(r['intent'],r['request'],w['before_world'],w['after_world'])==w['correct_at_commit']
  assert not r['invariant_error']
  name=f'{i:03d}_{r["intent"]}_{r["event"]}_{r["when"]}_{r["policy"]}'
  dump(root/'trajectories'/f'{name}.json',r)
  rows.append({k:r[k] for k in ('intent','event','when','policy','safe_success','wrong_write','rejections','tool_calls','global_token_issuances','global_token_checks')})
 with (root/'per_case.csv').open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
 agg=[]
 for policy in sorted({x['policy'] for x in rows}):
  group=[x for x in rows if x['policy']==policy]
  agg.append({'policy':policy,'cells':len(group),**{k:sum(r[k] for r in group) for k in ('safe_success','wrong_write','rejections','tool_calls','global_token_issuances','global_token_checks')}})
 dump(root/'summary.json',agg)
 # Boundary stress is NOT part of the 120 main cells.
 stress=[run_case(k,'binding','after_resolve','scoped_retry1',True) for k in ('person','reminder')]
 dump(root/'stress_continuous_changes.json',stress)
 scientific={'rows':rows,'stress':[{'intent':x['intent'],'success':x['safe_success'],'wrong_write':x['wrong_write'],'rejections':x['rejections']} for x in stress]}
 dump(root/'science.json',scientific)
 dump(root/'verification.json',{'records':len(rows),'native_scored_writes':sum(bool(x['safe_success'] or x['wrong_write']) for x in rows),'separate_stress_cases':2,'new_llm_calls':0,'phase':'OFFLINE_EXECUTION_CONTRACT_BOUNDARY_NOT_LLM_PERFORMANCE','execution_seconds':time.perf_counter()-tic,'python':platform.python_version(),'system':platform.system(),'science_sha256':hashlib.sha256(json.dumps(scientific,sort_keys=True,separators=(',',':')).encode()).hexdigest()})
 print(json.dumps(agg,indent=2));print(root)
if __name__=='__main__':main()
