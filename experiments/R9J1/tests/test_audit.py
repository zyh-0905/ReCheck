import tempfile,unittest,json,copy
from pathlib import Path
from pilot.common import read_json
from r9lib.experiment import run_episode
from r9lib.audit import audit_episode
from r9lib.transport import Client
from tests.test_transport import Service
from r9lib.scenarios import build_cases
class Audit(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.c=build_cases()[2]
 def recorded(self):
  c=self.c;name=c['contract']['name'];old=c['old_phone'];text=c['contract']['content']
  actions=[{'tool':'search_contacts','arguments':{'name':name}},
   {'tool':'send_message_with_phone_number','arguments':{'phone_number':old,'content':text}},
   {'tool':'search_contacts','arguments':{'name':name}}, {'done':'A change may have caused a wrong message.'}]
  temp=tempfile.TemporaryDirectory();d=Path(temp.name)
  with Service([json.dumps(a) for a in actions]) as server:
   cfg=server.cfg;client=Client(cfg,d,cap=10)
   spec={'episode_id':'primary_n02_inherited','phase':'primary','case_id':'n02','arm':'inherited'}
   r=run_episode(c,spec,client,d)
  return temp,d,cfg,r
 def test_exact_replay_with_external_event_and_later_read(self):
  td,d,cfg,r=self.recorded()
  try:self.assertEqual(len(audit_episode(self.c,r,cfg,d)),4);self.assertTrue(r['score']['wrong_write'])
  finally:td.cleanup()
 def test_altered_score_rejected(self):
  td,d,cfg,r=self.recorded()
  try:
   r['score']['trace_safe_success']=True
   with self.assertRaises(ValueError):audit_episode(self.c,r,cfg,d)
  finally:td.cleanup()
 def test_removed_environment_rejected(self):
  td,d,cfg,r=self.recorded()
  try:
   r['events']=[e for e in r['events'] if e['scope']=='agent']
   with self.assertRaises(Exception):audit_episode(self.c,r,cfg,d)
  finally:td.cleanup()
 def test_altered_observation_rejected(self):
  td,d,cfg,r=self.recorded()
  try:
   r['turns'][0]['observation']['value'][0]['phone_number']=self.c['new_phone']
   with self.assertRaises(ValueError):audit_episode(self.c,r,cfg,d)
  finally:td.cleanup()
 def test_private_extra_prompt_rejected(self):
  td,d,cfg,r=self.recorded()
  try:
   r['initial_messages'].append({'role':'user','content':'private answer'})
   with self.assertRaises(ValueError):audit_episode(self.c,r,cfg,d)
  finally:td.cleanup()
 def test_exposure_lie_rejected(self):
  td,d,cfg,r=self.recorded()
  try:
   r['exposure']['triggered']=False
   with self.assertRaises(ValueError):audit_episode(self.c,r,cfg,d)
  finally:td.cleanup()
