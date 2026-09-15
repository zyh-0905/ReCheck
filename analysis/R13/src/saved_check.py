"""Independent standard-library checks for the pinned scripted revision records.

Does not import the experiment's temporal reducer, NativeSession, or native grader.
It validates stored evidence and re-derives scoped business predicates. Native
similarity is range/structure checked, not re-optimized by this module.
"""
import copy,json,math

def need(ok,why):
    if not ok:raise ValueError(why)

def rows_at(snapshot,db,index):
    rows=snapshot['_dbs'][db]
    eligible=[r for r in rows if r['sandbox_message_index']<=index]
    need(bool(eligible),'missing database snapshot')
    epoch=max(r['sandbox_message_index'] for r in eligible)
    out=[]
    for r in eligible:
        if r['sandbox_message_index']!=epoch:continue
        data={k:v for k,v in r.items() if k!='sandbox_message_index'}
        if all(v is None for v in data.values()):continue
        out.append(data)
    return out

def keyed(rows):
    result={r['person_id']:r for r in rows}
    need(len(result)==len(rows),'duplicate contact identifier')
    return result

def check(r):
    need(r['evidence_kind']=='SCRIPTED_ORIGINAL_PUBLIC_USER_REVISION_NOT_LLM','wrong evidence kind')
    need(r['scenario']=='update_contact_relationship_with_relationship_twice_multiple_user_turn','wrong task')
    states=r['states'];need(len(states)>3,'short trajectory')
    snapshot=r['final_snapshot']; start=states[0]['snapshot_index']
    initial=keyed(rows_at(r['initial_snapshot'],'CONTACT',start))
    target=sorted(uid for uid,row in initial.items() if row['relationship']=='friend')
    need(len(target)==2 and target==r['target_ids_bound_at_initial_friend_query'],'target binding mismatch')
    indices=[s['snapshot_index'] for s in states]
    need(indices==sorted(set(indices)),'observation index ordering')
    for s in states:
        need(keyed(s['contacts'])==keyed(rows_at(snapshot,'CONTACT',s['snapshot_index'])),'observation != native snapshot')
    need(keyed(states[0]['contacts'])==initial,'initial contacts changed')
    bus={m['sandbox_message_index']:m for m in snapshot['_dbs']['SANDBOX']}
    def find_message(text):
        ids=[i for i,m in bus.items() if i>=start and m.get('sender')=='USER' and m.get('recipient')=='AGENT' and m.get('content')==text]
        need(len(ids)==1,'missing/repeated scope activation');return ids[0]
    a=find_message('Make all of these friends my enemies.')
    b=find_message('Now update those same people back to my friends.')
    need(a<b,'scope order')
    first_start=indices.index(a);second_start=indices.index(b)
    first_end=second_start-1
    need(r['first_goal_active_interval']==[first_start,first_end],'first scope mismatch')
    need(r['second_goal_active_interval']==[second_start,len(states)-1],'second scope mismatch')
    need(bus[indices[-1]].get('conversation_active') is False,'missing explicit stop')
    enemy=[];friend=[];protected=[]
    for s in states:
        cur=keyed(s['contacts'])
        enemy.append(all(uid in cur and cur[uid]['relationship']=='enemy' for uid in target))
        friend.append(all(uid in cur and cur[uid]['relationship']=='friend' for uid in target))
        valid=initial.keys()==cur.keys()
        for uid,row in initial.items():
            for k,v in row.items():
                if uid in target and k=='relationship':continue
                valid=valid and uid in cur and cur[uid].get(k)==v
        protected.append(valid)
    for key,value in [('enemy_predicate',enemy),('friend_predicate',friend),('protected_predicate',protected)]:
        need(r[key]==value,key+' mismatch')
    events=r['events'];event_ids=[e['snapshot_index'] for e in events]
    need(event_ids==sorted(set(event_ids)),'duplicate/order event')
    need([s['snapshot_index'] for s in states if s['label'].startswith('tool:')]==event_ids,'events not fully observed')
    current=copy.deepcopy(initial);errors=0
    for e in events:
        si=e['snapshot_index'];m=bus[si];need({k:v for k,v in m.items() if k!='sandbox_message_index'}==e['native_response'],'native response linkage')
        need(m.get('sender')=='EXECUTION_ENVIRONMENT','not an executor response')
        args=e['arguments'];ok=e['response']['ok'];need(type(ok) is bool,'invalid status')
        need((m.get('tool_call_exception') is None)==ok,'exception status mismatch')
        traces=m.get('tool_trace') or []
        if ok:
            parsed=[json.loads(t) for t in traces]
            need(any(t.get('tool_name')==e['tool'] and t.get('arguments')==args for t in parsed),'native arguments mismatch')
        if e['tool']=='search_contacts':
            need(args=={'relationship':'friend'} and ok,'unexpected query')
            expected=[x for x in current.values() if x['relationship']=='friend']
            need(keyed(e['response']['value'])==keyed(expected),'query result mismatch')
        elif e['tool']=='modify_contact':
            need(set(args)=={'person_id','relationship'},'unexpected fields')
            if args['person_id'] in current:
                need(ok,'existing-ID write incorrectly failed');current[args['person_id']]['relationship']=args['relationship']
            else:
                need(not ok,'missing-ID write incorrectly passed');errors+=1
        else:raise ValueError('unregistered tool')
        need(current==keyed(rows_at(snapshot,'CONTACT',si)),'native contact transition mismatch')
    expected={'first_scoped_goal':enemy[first_end], 'latest_terminal_only':friend[-1],
              'protected_invariant':all(protected),
              'scoped_contract':enemy[first_end] and friend[-1] and all(protected),
              'blanket_all_goals_terminal':enemy[-1] and friend[-1] and all(protected),
              'native_tool_calls':len(events),'tool_errors':errors}
    for k,v in expected.items():need(r[k]==v,k+' mismatch')
    score=r['official_evaluation']['similarity'];need(type(score) in (int,float) and math.isfinite(score) and 0<=score<=1,'invalid similarity')
    return {'variant':r['variant'],'checked_observations':len(states),'checked_events':len(events),
            'original_similarity_recorded_not_reoptimized':score,**expected}
