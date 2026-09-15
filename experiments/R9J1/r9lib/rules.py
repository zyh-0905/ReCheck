"""Grammar-bound local controls; not new agents, not LLM scores.
Only public task/history are used. Extra-read is a one-update diagnostic, NOT a
TOCTOU solution; post-confirm may restore final state but cannot erase past writes.
"""
import re

def parse(public):
 text=public['user_request']
 if text.startswith('Enable Wi-Fi'):return {'kind':'wifi'}
 if text.startswith('Find the reminder'):return {'kind':'reminder','title':re.search(r'"([^\"]+)"',text).group(1),'timestamp':float(re.search(r'POSIX timestamp (\d+)',text).group(1))}
 content=text.split('The exact message is: ')[1].split(' You may enable')[0]
 if 'explicit phone number ' in text:return {'kind':'phone','phone_number':re.search(r'explicit phone number (\+\d+)',text).group(1),'content':content}
 return {'kind':'person','name':text.split('Send ')[1].split(' exactly one text')[0],'content':content}

def action(name,**args):return {'tool':name,'arguments':args}

def rule_action(public,hist,mode='once'):
 c=parse(public);ok=[h for h in hist if h['response']['ok']]
 if c['kind']=='wifi':
  if any(h['tool']=='set_wifi_status' and h['arguments'].get('on') is True for h in ok):return {'done':'Wi-Fi enabled.'}
  lows=[h for h in ok if h['tool']=='get_low_battery_mode_status']
  if not lows:return action('get_low_battery_mode_status')
  disabled=any(h['tool']=='set_low_battery_mode_status' and h['arguments']['on'] is False for h in ok)
  need=lows[-1]['response']['value'] is True or (hist and not hist[-1]['response']['ok'] and 'low battery' in str(hist[-1]['response'].get('error')))
  if need and not disabled:return action('set_low_battery_mode_status',on=False)
  if mode=='extra_read' and len(lows)<2:return action('get_low_battery_mode_status')
  return action('set_wifi_status',on=True)
 mutator='modify_reminder' if c['kind']=='reminder' else 'send_message_with_phone_number'
 writes=[h for h in ok if h['tool']==mutator]
 if c['kind']=='phone':
  if writes:return {'done':'Literal number honored.'}
  if not any(h['tool']=='get_cellular_service_status' for h in ok):return action('get_cellular_service_status')
  return action(mutator,phone_number=c['phone_number'],content=c['content'])
 q='search_reminder' if c['kind']=='reminder' else 'search_contacts';args={'content':c['title']} if c['kind']=='reminder' else {'name':c['name']}
 reads=[h for h in ok if h['tool']==q and h['arguments']==args]
 if not reads or (mode=='extra_read' and len(reads)<2):return {'tool':q,'arguments':args}
 def row(h):
  key='content' if c['kind']=='reminder' else 'name';val=c.get('title',c.get('name'))
  matches=[r for r in h['response']['value'] if r[key]==val]
  if len(matches)!=1:raise ValueError('No unique public target')
  return matches[0]
 current=row(reads[-1]);first=row(reads[0])
 if writes:
  if mode!='post_confirm':return {'done':'Requested write returned successfully.'}
  last_write_index=max(i for i,h in enumerate(hist) if h in writes)
  recent=[h for h in hist[last_write_index+1:] if h['tool']==q and h['response']['ok']]
  if not recent:return {'tool':q,'arguments':args}
  current=row(recent[-1])
  if c['kind']=='person':
   if writes[0]['arguments']['phone_number']!=current['phone_number']:return {'done':'Contact changed; a previous message may have gone to an obsolete number. I will not send a duplicate.'}
   return {'done':'Contact and sent target agree.'}
  if current['reminder_timestamp']==c['timestamp']:return {'done':'Target reminder now has requested time.'}
  # Explicit diagnostic repair of an accidental prior modification; path grader
  # still records the first wrong write. No private scoring signal used here.
  if first['reminder_id']!=current['reminder_id'] and not any(h['arguments'].get('reminder_id')==first['reminder_id'] and h['arguments'].get('reminder_timestamp')==first['reminder_timestamp'] for h in writes):
   return action('modify_reminder',reminder_id=first['reminder_id'],reminder_timestamp=first['reminder_timestamp'])
 if c['kind']=='reminder':return action(mutator,reminder_id=current['reminder_id'],reminder_timestamp=c['timestamp'])
 return action(mutator,phone_number=current['phone_number'],content=c['content'])

def history_from_messages(messages):
 import json
 public=json.loads(messages[1]['content']);hist=[]
 for a,b in zip(messages[2::2],messages[3::2]):
  obj=json.loads(a['content'])
  if 'tool' in obj:hist.append({**obj,'response':json.loads(b['content'].removeprefix('TOOL_RESULT '))})
 return public,hist
