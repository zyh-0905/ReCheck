"""Final selected-effect check implemented without importing the main checker.
Checks recorded final snapshot predicates only; does not reconstruct latent
native intermediate execution or score all task requirements.
"""
from pathlib import Path
import csv,json,hashlib,zipfile,collections,argparse
ID='9e137f06-916a-5310-8174-cf0b7e9f7054'
def normalized(x):return ' '.join(x.lower().split()) if isinstance(x,str) else x

def check(root):
 raw=root/'inputs/download/raw';manifest=json.loads((raw.parent/'MANIFEST.json').read_text());files=[]
 for e in manifest['files']:
  b=(raw/e['path']).read_bytes();assert hashlib.sha256(b).hexdigest()==e['sha256'] and len(b)==e['bytes']
  etag=e.get('response_headers',{}).get('etag','').strip('"')
  blob=hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()
  files.append({'path':e['path'],'bytes':len(b),'sha256':e['sha256'],'etag_equals_git_blob_sha1':etag==blob,'response_commit_matches':e.get('response_headers',{}).get('x-repo-commit')==manifest['revision']})
 rows=list(csv.DictReader((root/'results/all_episodes.csv').open()));checked=[]
 settings={'wifi_off':('wifi',False),'cellular_off':('cellular',False),'turn_on_wifi_low_battery_mode':('wifi',True),'turn_on_cellular_low_battery_mode':('cellular',True),'turn_on_location_low_battery_mode':('location_service',True)}
 cache={}
 for r in rows:
  if r['goal_known']!='True':continue
  if r['source'] not in cache:cache[r['source']]=json.loads((raw/r['source']).read_text())
  s=cache[r['source']]['samples'][int(r['sample_index'])];initial={};last={}
  for turn in s['trajectory']:
   for m in turn:
    for k in ['user_details','tool_details']:
     u=m.get(k,{}).get('database_update',{})
     for ns,v in u.items():
      if ns not in initial:initial[ns]=v
      last[ns]=v
  sid=r['sample_id']
  if sid in settings:
   f,v=settings[sid];value=last['SETTING'][0][f]==v
  else:
   contacts=last['CONTACT'];ci=initial['CONTACT'];byid={x['person_id']:x for x in contacts}
   if sid=='update_contact_with_id_and_phone_number':value=ID in byid and byid[ID]['phone_number']=='+19876543210'
   elif sid=='add_contact_with_name_and_phone_number':value=any(normalized(x.get('name'))=='stephen sondheim' and x.get('phone_number')=='+19876543210' for x in contacts)
   elif sid=='remove_contact_with_id':value=ID not in byid
   elif sid=='remove_contact_by_phone':
    ids=[x['person_id'] for x in ci if x['phone_number']=='+12453344098'];assert ids;value=all(i not in byid for i in ids)
   elif sid=='update_contact_relationship_with_relationship':
    ids=[x['person_id'] for x in ci if normalized(x.get('relationship'))=='friend'];assert ids
    value=all(i in byid and normalized(byid[i].get('relationship'))=='enemy' for i in ids)
   else:raise AssertionError(sid)
  assert str(value)==r['effect_final'],r['key'];checked.append({'key':r['key'],'predicate':value})
 out={'raw_files_checked':len(files),'raw_bytes':sum(x['bytes'] for x in files),'etag_git_blobs_match':sum(x['etag_equals_git_blob_sha1'] for x in files),'response_revision_matches':sum(x['response_commit_matches'] for x in files),'selected_known_predicates_checked':len(checked),'matches':len(checked),'true':sum(x['predicate'] for x in checked),'false':sum(not x['predicate'] for x in checked),'not_claimed':'Not independent human review, not native tool replay, not full benchmark regrading; missing/ambiguous states excluded by published main-checker scope.'}
 (root/'results/independent_final_check.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
 (root/'results/raw_file_checks.json').write_text(json.dumps(files,indent=2)+'\n')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);a=p.parse_args();check(a.root)
