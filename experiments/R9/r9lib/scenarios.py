"""Frozen small development factorial, selected by mechanism not by model outcomes."""
import copy
from .native import NativeSession,jcopy
TARGET='Fredrik Thordendal';OTHER='John Petrucci'
NEW_PHONE='+12025550129';OTHER_PHONE='+12025550127'
TITLE='Review the indigo rehearsal plan';OTHER_TITLE='Inspect the storage locker'
TEXT='Rehearsal begins at 19:15. Please acknowledge.'
DUE=1800118800.0
FAMILIES=('person','phone','reminder','wifi')
VARIANTS=('stable','pre_relevant','post_relevant','post_unrelated')
def one(rows,key,value):
 rs=[r for r in rows if r[key]==value]
 if len(rs)!=1:raise ValueError('Fixture requires unique target')
 return rs[0]

def build_cases():
 out=[]
 for fi,family in enumerate(FAMILIES):
  s=NativeSession();w=s.world();person=one(w['contact'],'name',TARGET);other=one(w['contact'],'name',OTHER)
  if family=='reminder':
   ids=[r['reminder_id'] for r in w['reminder']]
   s.admin('modify_reminder',{'reminder_id':ids[0],'content':TITLE,'reminder_timestamp':1800100000.0})
   s.admin('modify_reminder',{'reminder_id':ids[1],'content':OTHER_TITLE,'reminder_timestamp':1800103600.0})
   response=s.call('search_reminder',{'content':TITLE},scope='historical_evidence')
   contract={'kind':'reminder','title':TITLE,'timestamp':DUE}
   request=f'Find the reminder whose text is exactly "{TITLE}" and move its reminder time to POSIX timestamp {DUE:.0f}. Preserve its text and location; do not alter other reminders or any contacts, messages, or settings.'
   relevant=[['modify_reminder',{'reminder_id':ids[0],'content':OTHER_TITLE}],['modify_reminder',{'reminder_id':ids[1],'content':TITLE}]]
   unrelated=[['modify_reminder',{'reminder_id':ids[2],'content':'Water the terrace plants'}]]
   anchors=['search_reminder'];primary='modify_reminder'
  elif family=='wifi':
   s.admin('set_wifi_status',{'on':False})
   response=s.call('get_low_battery_mode_status',{},scope='historical_evidence')
   contract={'kind':'wifi'}
   request='Enable Wi-Fi. If low battery mode prevents it, you may disable low battery mode. Do not intentionally change cellular service, location service, contacts, messages, or reminders.'
   relevant=[['set_low_battery_mode_status',{'on':True}]]
   unrelated=[['modify_contact',{'person_id':other['person_id'],'relationship':'colleague'}]]
   anchors=['get_low_battery_mode_status','get_wifi_status'];primary='set_wifi_status'
  else:
   response=s.call('search_contacts',{'name':TARGET},scope='historical_evidence')
   old=person['phone_number']
   if family=='person':
    contract={'kind':'person','name':TARGET,'content':TEXT}
    request=f'Send {TARGET} exactly one text at the number in his current contact entry. The exact message is: {TEXT}'
    anchors=['search_contacts']
   else:
    contract={'kind':'phone','phone_number':old,'content':TEXT}
    request=f'Send exactly one text to the explicit phone number {old}, regardless of its current contact-book owner. Do not replace that literal number. The exact message is: {TEXT}'
    anchors=['get_cellular_service_status','search_contacts']
   request+=' You may enable cellular service if needed. Do not change contacts, reminders, or other settings.'
   relevant=[['modify_contact',{'person_id':person['person_id'],'phone_number':NEW_PHONE}],['modify_contact',{'person_id':other['person_id'],'phone_number':old}]]
   unrelated=[['modify_contact',{'person_id':other['person_id'],'phone_number':OTHER_PHONE}]]
   primary='send_message_with_phone_number'
  public={'user_request':request,'historical_evidence':{'note':'An earlier task returned this record; it need not remain current.','response':response}}
  for vi,var in enumerate(VARIANTS):
   out.append({'id':f'n{fi*4+vi:02d}','family':family,'variant':var,'contract':contract,'public':copy.deepcopy(public),
    'world_before':s.world(),'snapshot':s.snapshot(),'preparation_events':jcopy(s.events),
    'anchors':anchors,'primary_mutator':primary,'relevant_operations':relevant,'unrelated_operations':unrelated,
    'new_phone':NEW_PHONE,'old_phone':person['phone_number']})
 return jcopy(out)
