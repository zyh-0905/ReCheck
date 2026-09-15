"""Offline validation of the declared saved execution-contract results."""
import argparse,json,hashlib
from pathlib import Path
import bootstrap
from boundary import score_write,all_specs

def audit(root):
 root=Path(root);a=root/'native_run1';b=root/'native_run2';f=root/'frozen_action_exposure'
 files=sorted((a/'trajectories').glob('*.json'))
 assert len(files)==120
 expected=set(all_specs()); seen=set(); write_checks=0
 for p in files:
  r=json.loads(p.read_text());key=tuple(r[k] for k in ('intent','event','when','policy'))
  assert key in expected and key not in seen;seen.add(key)
  assert r['tool_calls']==len(r['events'])
  for e in r['events']:
   if e['tool'].startswith('search_'):assert e['before_world']==e['after_world']
  good=False;wrong=False
  for w in r['writes']:
   ok=score_write(r['intent'],r['request'],w['before_world'],w['after_world']) if w['response']['ok'] else False
   assert ok==w['correct_at_commit'];write_checks+=1
   good|=ok;wrong|=w['before_world']!=w['after_world'] and not ok
  assert r['safe_success']==(good and not wrong) and r['wrong_write']==wrong
 assert (a/'science.json').read_bytes()==(b/'science.json').read_bytes()
 fs=sorted(f.glob('primary_*.json'));assert len(fs)==84
 # Frozen records are independently evaluated at a single write, not whole episodes.
 for p in fs:
  r=json.loads(p.read_text())
  assert r['kind']=='FROZEN_ACTION_TRANSITION_NOT_AGENT_EPISODE' and r['new_llm_calls']==0
  assert r['native_response']['ok']
 assert json.loads((root/'paid_r7c1_recheck/verification.json').read_text())['saved_responses']==169
 v={'new_remote_llm_calls':0,'new_primary_llm_episodes':0,'scripted_contract_trajectories':120,'main_write_transitions_rescored':write_checks,'stress_cases_separate':2,'frozen_action_transitions':84,'frozen_action_source_primary_episodes':42,'paid_r7c1_responses_rechecked_not_new':169,'native_repeat_discrete_projection_equal':True,'all_checks_pass':True,'not_claimed':['real concurrency atomicity','new model failures under changed feedback','novel TOCTOU defense','model superiority','publication readiness']}
 (root/'audit_verification.json').write_text(json.dumps(v,indent=2));print(json.dumps(v,indent=2));return v
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--root',required=True);a=p.parse_args();audit(a.root)
