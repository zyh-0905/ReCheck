"""Offline reconstruction of requests, native tools and state scoring."""
from pathlib import Path
from collections import Counter,defaultdict
import copy,csv,json,math
from .core import read,write,digest,file_sha,verify_sources,METHODS,MAIN_CAP,TOTAL_CAP,ROOT
from .journal import validate_response,payload,Paused
from .actor import SMOKE_MESSAGES
from .experiment import Replay,episode,schedule

def scientific_record(rec):
 d=copy.deepcopy(rec)
 for e in d['events']:e.pop('elapsed_seconds',None)
 return d

def audit(root=ROOT):
 root=Path(root);run=root/'runs/R7C';out=root/'offline_reports';out.mkdir(exist_ok=True)
 issues=[];notes=[];source=verify_sources(root);protocol=read(root/'configs/protocol.json');cases=read(root/'fixtures/cases.json')
 prepared=read(root/'PREPARED.json')
 if prepared['source_manifest_sha256']!=source['manifest_sha256'] or prepared['cases_sha256']!=file_sha(root/'fixtures/cases.json') or prepared['protocol_sha256']!=file_sha(root/'configs/protocol.json'):issues.append('Prepared binding mismatch')
 if not run.exists():
  report={'mechanical_pass':not issues,'run_complete':False,'issues':issues,'notes':['No paid run exists'],'new_audit_llm_calls':0};write(out/'audit.json',report);return report
 manifest=read(run/'manifest.json')
 if manifest.get('prepared')!=prepared:issues.append('Run manifest binding mismatch')
 srcfiles=read(root/'SOURCE_MANIFEST.json')['files']
 for rel,v in srcfiles.items():
  p=run/'code_snapshot'/rel
  if not p.exists() or file_sha(p)!=v['sha256']:issues.append('Snapshot mismatch: '+rel)
 records={};ordered=[];resp_ids=[];identity=None;call_rows=[]
 starts=sorted((run/'attempts').glob('*_start.json'))
 if len(starts)>TOTAL_CAP:issues.append('Global cap exceeded')
 for idx,p in enumerate(starts,1):
  st=read(p);ident=st['logical_id'];ordered.append(ident)
  if st['attempt']!=idx:issues.append('Noncontiguous attempt indices')
  if digest(st['payload'])!=st['payload_sha256']:issues.append('Request digest mismatch')
  rp=p.with_name(f'{idx:06d}_result.json');sp=p.with_name(f'{idx:06d}_send_intent.json')
  if not sp.exists():notes.append('Registered attempt has no send-intent: '+ident)
  else:
   si=read(sp)
   if si['attempt']!=idx or si['logical_id']!=ident:issues.append('Send-intent binding mismatch')
  if not rp.exists():notes.append('Missing response, receipt/billing unknown: '+ident);continue
  r=read(rp)
  if any(r.get(k)!=v for k,v in st.items()):issues.append('Result/start binding mismatch: '+ident)
  if r['transport']!='response':notes.append('Transport failure retained: '+ident);continue
  cf=run/'calls'/(digest(ident)+'.json')
  if not cf.exists() or read(cf)!=r:issues.append('Call/result ledger mismatch: '+ident)
  if manifest.get('evidence_kind')=='USER_LIVE_ENDPOINT':
   if r.get('evidence_kind')!='USER_LIVE_ENDPOINT' or r.get('endpoint')!=protocol['base_url']:issues.append('Live/fixture evidence mismatch')
  elif manifest.get('evidence_kind')=='SOFTWARE_TEST_NOT_RESEARCH':
   from urllib.parse import urlsplit
   if r.get('evidence_kind')!='SOFTWARE_TEST_NOT_RESEARCH' or urlsplit(r.get('endpoint','')).hostname not in ('127.0.0.1','localhost','::1'):issues.append('Untrusted fixture label')
  else:issues.append('Missing evidence-kind label')
  records[ident]=r;resp_ids.append(r['response'].get('id'))
  try:
   if json.loads(r['raw_response_text'])!=r['response']:issues.append('Raw response mismatch')
   _,identity=validate_response(r['response'],identity)
  except (ValueError,Paused):notes.append('Response pause gate: '+ident)
  u=r['response'].get('usage',{})
  call_rows.append({'logical_id':ident,'attempt':idx,'prompt_tokens':u.get('prompt_tokens'),'completion_tokens':u.get('completion_tokens'),
    'reasoning_tokens':u.get('completion_tokens_details',{}).get('reasoning_tokens'),'latency_seconds':r['elapsed_seconds'],'money':'UNKNOWN'})
 if len(ordered)!=len(set(ordered)):issues.append('Duplicate logical attempts')
 if len(resp_ids)!=len(set(resp_ids)):issues.append('Duplicate response IDs')
 if ordered and ordered[0]!='smoke':issues.append('Smoke not first')
 if 'smoke' in records and records['smoke']['payload']!=payload(SMOKE_MESSAGES,protocol):issues.append('Smoke payload mismatch')
 if 'smoke' in records:
  try:
   obj,_=validate_response(records['smoke']['response'],None)
   if obj!={'ok':True}:issues.append('Smoke answer not accepted')
  except Paused:
   if len(starts)>1:issues.append('Main proceeded after smoke failure')
 if len([x for x in ordered if x!='smoke'])>MAIN_CAP:issues.append('Main cap exceeded')
 rows=[];checked=0;expected_order=['smoke'] if ordered else [];used=[]
 byid={c['id']:c for c in cases};expected_files=set()
 for cid,m in schedule(cases,protocol['schedule_seed']):
  path=run/'episodes'/f'{cid}__{m}.json'
  if not path.exists():continue
  expected_files.add(path.name);saved=read(path);case=byid[cid]
  if saved['case_sha256']!=digest(case):issues.append('Case binding changed: '+path.name)
  player=Replay(records,protocol)
  try:actual=episode(case,m,player,replay_events=saved['events'])
  except Paused:
   # Recreate a paused prefix by collecting the result through a temporary file.
   import tempfile
   with tempfile.TemporaryDirectory() as tmp:
    pp=Path(tmp)/'partial.json';player=Replay(records,protocol)
    try:episode(case,m,player,pp,replay_events=saved['events'])
    except Paused:pass
    actual=read(pp)
  if scientific_record(actual)!=scientific_record(saved):issues.append('Episode reconstruction mismatch: '+path.name)
  expected_order.extend(player.expected);used.extend(player.used);checked+=len(player.expected)
  rows.append({'case_id':cid,'family':case['family'],'condition':case['condition'],'method':m,
               'decisions':len(saved['steps']),'tool_calls':len(saved['events']),'termination':saved['termination'],**saved['score']})
 # A paused pending attempt is included by Replay.expected even when no valid response.
 if ordered!=expected_order[:len(ordered)] or len(expected_order)<len(ordered):issues.append('Actual attempt schedule differs from frozen reconstructed order')
 extra=set(p.name for p in (run/'episodes').glob('*.json'))-expected_files
 if extra:issues.append('Unexpected episode files')
 all_calls=set(p.stem for p in (run/'calls').glob('*.json'))
 if all_calls!={digest(x) for x in records}:issues.append('Unexpected call files')
 status=read(run/'status.json');complete=status['state']=='completed'
 if complete and (len(rows)!=72 or any(r['termination']=='paused' for r in rows)):issues.append('Completed status with incomplete episodes')
 if complete and set(records)!={'smoke',*used}:issues.append('Unconsumed response in completed run')
 summary={}
 for m in METHODS:
  rr=[r for r in rows if r['method']==m]
  summary[m]={'episodes':len(rr),'effective_success':sum(r['effective_success'] for r in rr),'safe_goal_met':sum(r['safe_goal_met'] for r in rr),
              'side_effect_cases':sum(not r['no_side_effects'] for r in rr),'decisions':sum(r['decisions'] for r in rr),'tool_calls':sum(r['tool_calls'] for r in rr)}
 for name,data in [('per_episode.csv',rows),('per_call.csv',call_rows)]:
  if data:
   with (out/name).open('w',encoding='utf-8',newline='') as f:
    wr=csv.DictWriter(f,fieldnames=list(data[0]));wr.writeheader();wr.writerows(data)
 report={'mechanical_pass':not issues,'run_complete':complete,'source':source,'issues':issues,'notes':notes,
         'attempts':len(starts),'response_records':len(records),'episodes':len(rows),'reconstructed_decisions':checked,
         'method_summary':summary,'scientific_gate':'PENDING_RESEARCHER_REVIEW','money_cost':'UNKNOWN','new_audit_llm_calls':0,
         'evidence_kind':manifest.get('evidence_kind'),'scope':'Internal consistency; not provider weight/billing authentication. Native-tool constructed task diagnosis; not official benchmark.'}
 write(out/'audit.json',report);return report
