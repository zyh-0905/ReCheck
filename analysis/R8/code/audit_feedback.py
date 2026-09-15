#!/usr/bin/env python3
"""Offline R7C1 audit. Standard-library independent scorer + immutable ledger checks.
Usage: python audit_feedback.py --feedback user.zip --kit Research_Handoff_R7C1.zip --out results
No model API, file rewrites, private credentials, or external network are used.
Native replay is a separate check in native_replay.py, not simulated by this script.
"""
import argparse,zipfile,io,hashlib,json,csv,math,stat,random,copy
from pathlib import Path,PurePosixPath
from collections import Counter,defaultdict
from datetime import datetime
from independent_core import canonical,strict_same,derive_goal,independent_score,tool_actions,validate_usage

EXPECTED_KIT='60e5e182c6f256b320cf7a2a19ce2b5c50ef690510e90765765a8e507d44fe84'
def sha(b):return hashlib.sha256(b).hexdigest()
def digest(x):return sha(canonical(x).encode())
def check(ok,msg):
    if not ok:raise ValueError(msg)
def load(b):
    def pairs(kvs):
        d={}
        for k,v in kvs:
            if k in d:raise ValueError('Duplicate JSON key')
            d[k]=v
        return d
    def bad(x):raise ValueError('Nonfinite JSON')
    return json.loads(b,object_pairs_hook=pairs,parse_constant=bad)
def read_zip(data):
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        infos=z.infolist();check(len(infos)==len({i.filename for i in infos}),'Duplicate ZIP names')
        check(sum(i.file_size for i in infos)<500_000_000,'ZIP expansion limit')
        out={}
        for i in infos:
            p=PurePosixPath(i.filename)
            check(not p.is_absolute() and '..' not in p.parts and '\\' not in i.filename,'ZIP path')
            check(not stat.S_ISLNK(i.external_attr>>16) and not i.flag_bits&1,'ZIP special entry')
            if not i.is_dir():out[i.filename]=z.read(i)
        return out

def csv_write(p,rows):
    if not rows:return
    with p.open('w',newline='',encoding='utf8') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
def dump(p,o):p.write_text(json.dumps(o,ensure_ascii=False,sort_keys=True,indent=2,allow_nan=False)+'\n',encoding='utf8')
def run(feedback,kit,out):
    feedback=Path(feedback);kit=Path(kit);out=Path(out);out.mkdir(parents=True,exist_ok=True)
    raw=feedback.read_bytes();original=kit.read_bytes();check(sha(original)==EXPECTED_KIT,'Unexpected distributed kit')
    outer=read_zip(raw);inner_bytes=raw;extra={}
    if 'BUNDLE_MANIFEST.json' not in outer:
        inn=[(k,v) for k,v in outer.items() if k.endswith('.zip') and not k.startswith('__MACOSX/')]
        check(len(inn)==1,'Need exactly one inner feedback archive');inner_bytes=inn[0][1];extra=outer;data=read_zip(inner_bytes)
    else:data=outer
    bm=load(data['BUNDLE_MANIFEST.json']);manifest=bm['sha256']
    check(set(data)==set(manifest)|{'BUNDLE_MANIFEST.json'},'Extra or missing bundled data')
    for n,h in manifest.items():check(sha(data[n])==h,'Bundle hash '+n)
    source=read_zip(original);prefix=next(k.split('/')[0]+'/' for k in source)
    src={k[len(prefix):]:v for k,v in source.items()};sm=load(src['SOURCE_MANIFEST.json'])['sha256']
    check(set(n[len('kit_source/'):] for n in data if n.startswith('kit_source/'))==set(src),'Source file inventory')
    for n,b in src.items():check(data['kit_source/'+n]==b,'Source changed '+n)
    for n,h in sm.items():check(sha(src[n])==h,'Distributed manifest corrupted')
    convenience=0
    for name,b in extra.items():
        if name.startswith('__MACOSX/') or name.endswith(('README.md','.zip')):continue
        base=PurePosixPath(name).name
        matches=[x for x in data if PurePosixPath(x).name==base and not x.startswith('kit_source/')]
        if matches:
            check(any(data[x]==b for x in matches),'Convenience copy differs '+base);convenience+=1
    protocol=load(src['protocol.json']);prep=load(data['PREPARED.json']);cfg=prep['config']
    check(prep['protocol']==protocol,'Prepared protocol')
    check(prep['source']==sm,'Prepared source')
    check(prep['fingerprint']==digest({'config':cfg,'protocol':protocol,'source':sm}),'Prepared fingerprint')
    check(cfg==load(src['config.example.json']),'Frozen config')
    check(protocol['task_id']=='R7C1_NATIVE_AGENT_DIAGNOSIS_01','Wrong protocol')
    cases={c['id']:c for c in load(src['fixtures/cases.json'])}
    eps={PurePosixPath(n).stem:load(b) for n,b in data.items() if n.startswith('runs/R7C_main/episodes/') and n.endswith('.json')}
    rng=random.Random(714031);case_order=list(range(14));rng.shuffle(case_order);schedule=[]
    for i in case_order:
        arms=['stateless','inherited','resolve_rule'];rng.shuffle(arms)
        schedule += [f'primary_c{i:02d}_{a}' for a in arms]
    repeat=[(i,a) for i in (2,10) for a in ('stateless','inherited','resolve_rule')];rng.shuffle(repeat)
    schedule += [f'repeat_c{i:02d}_{a}' for i,a in repeat]
    check(set(eps)==set(schedule),'Episode inventory');check(len(eps)==48,'Episode count')
    callmap={};callrows=[];responseids=[];payloads={};identity=None;sequence=[];tools=[];eprows=[]
    for run_name,cap in [('R7C_smoke',1),('R7C_main',384)]:
        rp='runs/'+run_name+'/'
        rm=load(data[rp+'manifest.json']);check(rm['prepared_fingerprint']==prep['fingerprint'],'Run binding')
        for k in ('protocol','source','config'):check(rm[k]==prep[k],'Run '+k)
        status=load(data[rp+'status.json']);check(status['status']=='completed','Run not complete')
        ident=load(data[rp+'endpoint_identity.json'])
        if identity is None:identity=ident
        check(ident==identity,'Cross-run cohort differs')
        check(ident['requested_model']=='deepseek-v4-flash' and ident['returned_model'] in ('deepseek-flash','deepseek-v4-flash'),'Model labels')
        check(type(ident['system_fingerprint']) is str and ident['system_fingerprint'].strip(),'Fingerprint missing')
        starts=sorted(n for n in data if n.startswith(rp+'attempts/') and n.endswith('_start.json'))
        check(len(starts)<=cap,'Request cap')
        expected_files=set();expected_calls=set()
        for idx,name in enumerate(starts,1):
            st=load(data[name]);check(name==rp+f'attempts/{idx:06d}_start.json','Start ordering');check(st['attempt']==idx,'Attempt number')
            names={x:rp+f'attempts/{idx:06d}_{x}.json' for x in ('start','send_intent','result')};expected_files.update(names.values())
            send=load(data[names['send_intent']]);r=load(data[names['result']]);lid=st['logical_id'];cache=rp+'calls/'+digest(lid)+'.json';expected_calls.add(cache)
            check(strict_same(r,load(data[cache])),'Result/cache mismatch')
            for k,v in st.items():check(strict_same(r.get(k),v),'Start/result '+k)
            check(send['attempt']==idx and send['logical_id']==lid and send['proves_remote_receipt'] is False,'Send intent')
            check(r['status']=='ok','Request failed')
            check(r['estimated_cost'] is None,'Unknown fee replaced')
            pay=r['payload'];check(pay['model']==ident['requested_model'],'Request model')
            check(r['payload_sha256']==digest(pay),'Payload hash');check(r['request_sha256']==digest({'endpoint':cfg['base_url'],'payload':pay}),'Request hash')
            check(r['response']['model']==ident['returned_model'] and r['response']['system_fingerprint']==ident['system_fingerprint'],'Response cohort')
            resp=r['response'];check(len(resp['choices'])==1 and resp['choices'][0]['finish_reason']=='stop','Stop/choice')
            check(resp['choices'][0]['message']['content']==r['text'],'Response text')
            check(type(load(r['text'])) is dict,'JSON root');usage=validate_usage(resp.get('usage'))
            check(type(r['latency_seconds']) in (float,int) and math.isfinite(r['latency_seconds']) and r['latency_seconds']>=0,'Invalid latency')
            start_dt=datetime.fromisoformat(st['started_utc']);send_dt=datetime.fromisoformat(send['local_send_intent_utc']);end_dt=datetime.fromisoformat(r['ended_utc'])
            check(start_dt<=send_dt<=end_dt,'Clock sequence')
            check(lid not in callmap,'Repeated logical id');callmap[lid]=r;payloads[lid]=pay;responseids.append(resp['id'])
            phase=r['metadata'].get('phase');arm=eps[r['metadata']['episode_id']]['arm'] if phase!='smoke' else 'smoke'
            callrows.append({'run':run_name,'attempt':idx,'logical_id':lid,'phase':phase,'arm':arm,**usage,'latency_seconds':r['latency_seconds'],'response_id':resp['id'],'request_hash':r['request_sha256'],'cost':'UNKNOWN'})
            if run_name=='R7C_main':sequence.append(lid)
        check(expected_files=={n for n in data if n.startswith(rp+'attempts/')},'Unaccounted attempt file')
        check(expected_calls=={n for n in data if n.startswith(rp+'calls/')},'Unaccounted cache file')
    check(len(responseids)==len(set(responseids)),'Duplicate response IDs')
    smoke=callmap['smoke'];check(load(smoke['text'])=={'done':'ready'},'Smoke content')
    expected_smoke=[{'role':'system','content':'Return exactly one JSON object: {"done":"ready"}.'},{'role':'user','content':'Check the JSON-only interface.'}]
    check(smoke['payload']['messages']==expected_smoke,'Smoke messages')
    check(load(data['runs/R7C_smoke/smoke_result.json'])=={'json_ok':True,'shape_ok':True,'request_sha256':smoke['request_sha256']},'Smoke saved fields')
    expected_sequence=[]
    for eid in schedule:
        r=eps[eid];phase,cid,arm=eid.split('_',2);case=cases[cid]
        check(r['episode_id']==eid and r['phase']==phase and r['case_id']==cid and r['arm']==arm,'Episode identity')
        check(r['case_sha256']==digest(case) and r['public_input_sha256']==digest(case['public']),'Case hashes')
        derived=derive_goal(case)
        for k,v in derived.items():check(case['goal'][k]==v,'Frozen goal differs from independently resolved public target')
        check(1<=r['model_calls']<=8 and r['model_calls']==len(r['turns']),'Turn budget')
        check(type(r['terminated']) is bool and r['terminated'],'Termination')
        score=independent_score(case,r)
        for k in ('safe_success','goal_achieved','wrong_write'):check(type(r['score'][k]) is bool and r['score'][k]==score[k],'Independent score '+eid)
        check(not score['violations'],'Unexpected state changes')
        messages=copy.deepcopy(r['initial_messages']);public=load(messages[1]['content']);expected_public=case['public'] if arm!='stateless' else {'user_request':case['public']['user_request']}
        check(public==expected_public,'Public-only input boundary')
        event_index=0;errors=0;boundary_messages=None
        for n,t in enumerate(r['turns']):
            lid=eid+f'/turn_{n:02d}';expected_sequence.append(lid);c=callmap[lid]
            check(t['turn']==n and t['logical_id']==lid,'Turn metadata')
            check(c['metadata']=={'episode_id':eid,'phase':phase,'turn':n},'Call metadata')
            check(c['payload']['messages']==messages,'Independent conversation reconstruction '+lid)
            check(t['request_sha256']==c['request_sha256'] and t['response_text']==c['text'],'Turn response')
            partial=f'runs/R7C_main/partial/{eid}/{n:02d}.json';check(strict_same(load(data[partial]),t),'Partial turn file')
            boundary_messages=copy.deepcopy(messages);messages.append({'role':'assistant','content':c['text']})
            action=load(c['text']);check(strict_same(t['action'],action),'Parsed action')
            if t['kind']=='done':
                check(n==len(r['turns'])-1 and set(action)=={'done'} and type(action['done']) is str,'Done position/shape')
                check(r['done_text']==action['done'],'Done text')
            elif t['kind']=='tool':
                check(set(action)=={'tool','arguments'} and type(action['arguments']) is dict,'Tool shape')
                e=r['events'][event_index];check(t['event_index']==event_index and e['scope']=='agent','Event index')
                check(action['tool']==e['tool'] and strict_same(action['arguments'],e['arguments']),'Event action')
                check(strict_same(t['observation'],e['response']),'Event feedback')
                check(type(e['response']['ok']) is bool,'Tool ok type')
                errors+=not e['response']['ok']
                tools.append({'episode_id':eid,'phase':phase,'case_id':cid,'family':case['family'],'arm':arm,'turn':n,'tool':action['tool'],'arguments':canonical(action['arguments']),'ok':e['response']['ok']})
                messages.append({'role':'user','content':'TOOL_RESULT '+json.dumps(e['response'],ensure_ascii=False,sort_keys=True)})
                event_index+=1
            else:raise ValueError('Unexpected action kind in recorded run')
        check(event_index==r['tool_calls']==len(r['events']),'Tool count')
        boundary=load(data[f'runs/R7C_main/partial/{eid}/boundary.json'])
        check(boundary['turn']==r['model_calls']-1 and boundary['messages']==boundary_messages,'Last boundary message')
        check(boundary['world']==r['after_world'] and boundary['snapshot']==r['final_snapshot'],'Last done boundary world')
        goal_kind=derived['kind'];target_tool='search_reminder' if goal_kind=='reminder' else 'search_contacts'
        write_tool='modify_reminder' if goal_kind=='reminder' else 'send_message_with_phone_number'
        ev=r['events'];first_write=next(i for i,e in enumerate(ev) if e['tool']==write_tool)
        before_queries=sum(e['tool']==target_tool for e in ev[:first_write]);after_queries=sum(e['tool']==target_tool for e in ev[first_write+1:])
        eprows.append({'episode_id':eid,'phase':phase,'case_id':cid,'family':case['family'],'variant':case['variant'],'arm':arm,
            'safe_success':score['safe_success'],'goal_achieved':score['goal_achieved'],'wrong_write':score['wrong_write'],'terminated':r['terminated'],
            'model_calls':r['model_calls'],'tool_calls':r['tool_calls'],'tool_errors':errors,'identity_reads_before_write':before_queries,'identity_reads_after_write':after_queries,
            'cellular_reads':sum(e['tool']=='get_cellular_service_status' for e in ev),'cellular_enables':sum(e['tool']=='set_cellular_service_status' for e in ev),
            'goal_kind':goal_kind,'target':derived.get('phone_number',derived.get('reminder_id'))})
    check(sequence==expected_sequence,'Registered call order differs from frozen episode schedule')
    for cid in cases:
        a=eps[f'primary_{cid}_inherited'];b=eps[f'primary_{cid}_resolve_rule']
        check(a['initial_messages'][1]==b['initial_messages'][1],'Treatment material mismatch')
    repeats=[]
    for cid in ('c02','c10'):
        for arm in ('stateless','inherited','resolve_rule'):
            a=eps[f'primary_{cid}_{arm}'];b=eps[f'repeat_{cid}_{arm}'];ta,tb=tool_actions(a),tool_actions(b)
            check(a['initial_messages']==b['initial_messages'],'Repeat initial input mismatch')
            repeats.append({'case_id':cid,'arm':arm,'same_initial_messages':True,'same_all_actions_including_done':[t.get('action') for t in a['turns']]==[t.get('action') for t in b['turns']],
                'same_tool_actions':ta==tb,'same_tool_names':[x['tool'] for x in ta]==[x['tool'] for x in tb],
                'same_done_text':a['done_text']==b['done_text'],'primary_tool_calls':len(ta),'repeat_tool_calls':len(tb),
                'primary_tool_actions':canonical(ta),'repeat_tool_actions':canonical(tb),
                'primary_safe_success':a['score']['safe_success'],'repeat_safe_success':b['score']['safe_success']})
    summary=[]
    for phase in ('primary','repeat'):
        for arm in ('stateless','inherited','resolve_rule'):
            er=[r for r in eprows if r['phase']==phase and r['arm']==arm];cr=[r for r in callrows if r['phase']==phase and r['arm']==arm]
            summary.append({'phase':phase,'arm':arm,'episodes':len(er),'safe_success':sum(r['safe_success'] for r in er),'wrong_write':sum(r['wrong_write'] for r in er),
                'tool_calls':sum(r['tool_calls'] for r in er),'model_calls':len(cr),'prompt_tokens':sum(r['prompt_tokens'] for r in cr),
                'completion_tokens':sum(r['completion_tokens'] for r in cr),'reasoning_tokens':sum(r['reasoning_tokens'] for r in cr),
                'cache_hit_tokens':sum(r['cache_hit_tokens'] for r in cr),'cache_miss_tokens':sum(r['cache_miss_tokens'] for r in cr),
                'model_latency_seconds':math.fsum(r['latency_seconds'] for r in cr),'cost':'UNKNOWN'})
    phase_summary=[]
    for phase in ('smoke','primary','repeat'):
        cr=[r for r in callrows if r['phase']==phase]
        phase_summary.append({'phase':phase,'calls':len(cr),**{k:sum(r[k] for r in cr) for k in ('prompt_tokens','completion_tokens','reasoning_tokens','cache_hit_tokens','cache_miss_tokens')},'latency_seconds':math.fsum(r['latency_seconds'] for r in cr)})
    pairs=[]
    for cid in cases:
        for other in ('stateless','resolve_rule'):
            a=eps[f'primary_{cid}_inherited'];b=eps[f'primary_{cid}_{other}'];pairs.append({'case_id':cid,'comparator':other,
                'same_tool_actions':tool_actions(a)==tool_actions(b),'inherited_safe':a['score']['safe_success'],'comparator_safe':b['score']['safe_success'],
                'inherited_tool_calls':a['tool_calls'],'comparator_tool_calls':b['tool_calls'],'tool_call_difference':b['tool_calls']-a['tool_calls']})
    checks={'protocol':protocol['task_id'],'archive_sha256':sha(raw),'inner_sha256':sha(inner_bytes),'original_kit_sha256':sha(original),
        'manifest_files_checked':len(manifest),'registered_source_files':len(sm),'source_total_including_manifest':len(src),'outer_convenience_copies':convenience,
        'primary_episodes':sum(r['phase']=='primary' for r in eprows),'repeat_episodes':sum(r['phase']=='repeat' for r in eprows),
        'saved_responses':len(callrows),'distinct_response_ids':len(set(responseids)),'independent_conversation_requests':len(sequence),'independent_smoke_requests':1,
        'independent_score_records':len(eprows),'tool_events':len(tools),'response_identity':identity,'new_model_calls':0,
        'method_scope':'standard-library independent target/state/ledger audit; original native replay logged separately',
        'score_definition':'safe_success = goal_achieved and no wrong_write; termination separately checked',
        'all_primary_safe':all(r['safe_success'] for r in eprows if r['phase']=='primary'),
        'tool_repeat_pairs_equal':sum(r['same_tool_actions'] for r in repeats),'only_done_difference_pairs':sum(r['same_tool_actions'] and not r['same_done_text'] for r in repeats),
        'preparation_read_events_in_frozen_cases':sum(e['scope'] in ('initial_memory','preceding_task_observation') for c in cases.values() for e in c['preparation_events']),
        'mechanical_pass':True,'execution_complete':True,'scientific_status':'DIAGNOSTIC_CEILING; NO_OBSERVED_BASELINE_FAILURE_OR_RULE_BENEFIT'}
    for name,rows in [('episodes.csv',eprows),('calls.csv',callrows),('tools.csv',tools),('summary.csv',summary),('phase_costs.csv',phase_summary),('repeat_diagnostics.csv',repeats),('paired_arms.csv',pairs)]:csv_write(out/name,rows)
    dump(out/'verification.json',checks);dump(out/'phase_costs.json',phase_summary)
    check(sha(feedback.read_bytes())==sha(raw) and sha(kit.read_bytes())==sha(original),'Input archives changed')
    print(json.dumps(checks,ensure_ascii=False,indent=2));return checks
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--feedback',required=True);p.add_argument('--kit',required=True);p.add_argument('--out',required=True);a=p.parse_args();run(a.feedback,a.kit,a.out)
