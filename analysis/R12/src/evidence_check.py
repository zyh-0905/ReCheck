"""Recompute terminal predicates from snapshots, not the saved truth labels.

This is a second implementation for data consistency, not a human review or a
replacement for executing the unchanged upstream evaluator.
"""
import math,datetime

SETTINGS={
 'cellular_off':('cellular',False), 'wifi_off':('wifi',False),
 'turn_on_wifi_low_battery_mode':('wifi',True),
 'turn_on_cellular_low_battery_mode':('cellular',True),
 'turn_on_location_low_battery_mode':('location_service',True),
}
EXTRA={'update_contact_with_id_and_phone_number','update_contact_relationship_with_relationship','modify_reminder_with_recency_latest'}

def require(condition,message):
    if not condition: raise ValueError(message)

def latest_rows(snapshot,namespace,at=None):
    rows=snapshot['_dbs'][namespace]
    eligible=[r for r in rows if at is None or r['sandbox_message_index']<=at]
    require(bool(eligible),'Missing snapshot')
    index=max(r['sandbox_message_index'] for r in eligible)
    return [{k:v for k,v in r.items() if k!='sandbox_message_index'} for r in eligible
            if r['sandbox_message_index']==index and any(v is not None for k,v in r.items() if k!='sandbox_message_index')]

def check_record(r):
    case=r['scenario'];require(case in SETTINGS or case in EXTRA,'Unknown scenario')
    settings=case in SETTINGS;db='SETTING' if settings else ('REMINDER' if 'reminder' in case else 'CONTACT')
    initial=latest_rows(r['initial_snapshot'],db);final=latest_rows(r['final_snapshot'],db)
    require(initial==([r['initial_settings']] if settings else r['initial_rows']),'Initial rows mismatch')
    require(final==([r['final_settings']] if settings else r['final_rows']),'Final rows mismatch')
    if settings:
        field,desired=SETTINGS[case]
        require(r['public_task_target']=={'field':field,'desired':desired},'Target changed')
        terminal=len(final)==1 and type(final[0].get(field)) is bool and final[0][field] is desired
    else:
        if case=='update_contact_with_id_and_phone_number':
            idfield='person_id';field='phone_number';desired='+19876543210'
            targets=[x['person_id'] for x in initial if x['name']=='Fredrik Thordendal']
        elif case=='update_contact_relationship_with_relationship':
            idfield='person_id';field='relationship';desired='enemy'
            targets=[x['person_id'] for x in initial if x['relationship']=='friend']
        else:
            idfield='reminder_id';field='reminder_timestamp'
            targets=[max(initial,key=lambda x:x['creation_timestamp'])[idfield]]
            clocks=[e['response']['value'] for e in r['events'] if e['tool']=='get_current_timestamp' and e['response']['ok']]
            if clocks:
                tomorrow=datetime.datetime.fromtimestamp(clocks[0])+datetime.timedelta(days=1)
                desired=tomorrow.replace(hour=17,minute=0,second=0,microsecond=0).timestamp()
            else:
                # A no-action trace has no clock receipt; its reported requested date
                # is diagnostic, and no old time satisfies it in this fixed fixture.
                require(r['variant']=='claim_only','Missing clock')
                desired=r['desired']
        require(r['field']==field and r['desired']==desired and set(r['target_ids'])==set(targets),'Target changed')
        terminal=all(len([x for x in final if x[idfield]==t and x[field]==desired])==1 for t in targets)
    require(type(r['terminal_valid']) is bool and r['terminal_valid']==terminal,'Terminal label mismatch')
    events=r['events'];states=r['states_after_calls']
    require(r['native_tool_calls']==len(events)==len(states),'Event count mismatch')
    require(r['native_tool_errors']==sum(e['response']['ok'] is False for e in events),'Error count mismatch')
    prior=initial
    for i,(event,state) in enumerate(zip(events,states)):
        require(event['tool'] in r['tool_allow_list'],'Non-authorized fixture tool')
        after=latest_rows(r['final_snapshot'],db,event['snapshot_index'])
        saved=[state['state']] if settings else state['rows']
        require(state['event_index']==i and after==saved,'Intermediate state mismatch')
        if not event['response']['ok']: require(after==prior,'Error changed business database')
        prior=after
    ev=r['official_evaluation'];s=ev['similarity']
    require(type(s) in (int,float) and math.isfinite(s) and 0<=s<=1,'Invalid original score')
    require(s==int(ev['minefield_similarity']==0)*ev['milestone_similarity'],'Score components mismatch')
    full=s==1.0
    relation=('full_score_terminal_true' if terminal else 'full_score_terminal_mismatch') if full else ('not_full_score_terminal_true' if terminal else 'not_full_score_terminal_false')
    require(r['score_terminal_relation']==relation,'Relation label mismatch')
    return {'scenario':case,'variant':r['variant'],'official_similarity':s,'terminal_valid':terminal,
      'full_score_terminal_mismatch':full and not terminal,'original_full_and_terminal':full and terminal,
      'native_tool_calls':len(events),'native_tool_errors':r['native_tool_errors']}
