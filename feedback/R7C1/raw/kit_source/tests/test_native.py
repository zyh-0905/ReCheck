
import unittest,copy,json
from r7clib.native import NativeSession
from r7clib.cases import make_cases, scripted
from r7clib.goals import evaluate

class NativeTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.cases=make_cases()
 def test_case_count(self):self.assertEqual(len(self.cases),14)
 def test_families(self):self.assertEqual({x['family'] for x in self.cases},{'person_message','literal_message','reminder_label'})
 def test_shared_goal_world(self):
  for i in range(4):
   a,b=self.cases[i],self.cases[i+4]
   for n in ('contact','setting'):self.assertEqual(a['world_before'][n],b['world_before'][n])
 def test_all_resolve_scripts_solve(self):
  for c in self.cases:
   with self.subTest(c=c['id']):
    r=scripted(c,'resolve');self.assertTrue(r['score']['safe_success'],r)
 def test_stale_person_can_silently_miswrite(self):
  c=self.cases[2];r=scripted(c,'cached')
  self.assertFalse(r['score']['safe_success']);self.assertTrue(r['score']['wrong_write'])
 def test_literal_goal_respects_number(self):
  r=scripted(self.cases[6],'cached')
  self.assertTrue(r['score']['safe_success'])
 def test_reminder_wrong_id_detected(self):
  r=scripted(self.cases[10],'cached')
  self.assertFalse(r['score']['safe_success']);self.assertTrue(r['score']['wrong_write'])
 def test_updated_observation_reuse(self):
  for i in (3,7,11):
   self.assertTrue(scripted(self.cases[i],'reuse')['score']['safe_success'])
 def test_old_observation_not_magically_fresh(self):
  self.assertFalse(scripted(self.cases[2],'reuse')['score']['safe_success'])
 def test_connection_recovery(self):
  for i in (12,13):self.assertTrue(scripted(self.cases[i],'resolve')['score']['safe_success'])
 def test_unknown_tool_rejected(self):
  s=NativeSession(self.cases[0]['snapshot'])
  r=s.call('__import__',{'name':'os'})
  self.assertFalse(r['ok']);self.assertEqual(s.world(),self.cases[0]['world_before'])
 def test_non_json_argument_rejected(self):
  s=NativeSession(self.cases[0]['snapshot'])
  self.assertFalse(s.call('search_contacts',{'name':object()})['ok'])
 def test_code_is_data(self):
  s=NativeSession(self.cases[0]['snapshot']);s.call('search_contacts',{'name':"x');raise Exception('boom"})
  self.assertEqual(s.world(),self.cases[0]['world_before'])
 def test_snapshot_clone_no_sharing(self):
  c=self.cases[0];s=NativeSession(c['snapshot']);s.call('set_cellular_service_status',{'on':False})
  t=NativeSession(c['snapshot']);self.assertEqual(t.world(),c['world_before'])
 def test_posthoc_repair_cannot_erase_wrongwrite(self):
  c=self.cases[2];s=NativeSession(c['snapshot'])
  s.call('send_message_with_phone_number',{'phone_number':c['old_memory']['contact']['phone_number'],'content':c['goal']['content']})
  x=s.call('search_contacts',{'name':c['goal']['name']})
  rows=[v for v in x['value'] if v['name']==c['goal']['name']]
  s.call('send_message_with_phone_number',{'phone_number':rows[0]['phone_number'],'content':c['goal']['content']})
  z=evaluate(c['world_before'],s.world(),c['goal'],s.events)
  self.assertFalse(z['safe_success']);self.assertTrue(z['wrong_write'])
 def test_no_write_not_success(self):
  c=self.cases[0];z=evaluate(c['world_before'],c['world_before'],c['goal'],[])
  self.assertFalse(z['safe_success'])
 def test_reminder_intermediate_mutation_is_seen(self):
  c=self.cases[10];s=NativeSession(c['snapshot'])
  wrong=c['old_memory']['reminder']['reminder_id']
  s.call('modify_reminder',{'reminder_id':wrong,'reminder_timestamp':c['goal']['timestamp']})
  before=[r for r in c['world_before']['reminder'] if r['reminder_id']==wrong][0]
  s.call('modify_reminder',{'reminder_id':wrong,'reminder_timestamp':before['reminder_timestamp']})
  s.call('modify_reminder',{'reminder_id':c['goal']['reminder_id'],'reminder_timestamp':c['goal']['timestamp']})
  z=evaluate(c['world_before'],s.world(),c['goal'],s.events)
  self.assertFalse(z['safe_success'])
 def test_public_has_no_goal_or_condition(self):
  for c in self.cases:
   p=c['public']
   self.assertNotIn('goal',p);self.assertNotIn('variant',p);self.assertNotIn('family',p)
 def test_native_module_not_replaced(self):
  from tool_sandbox.tools.messaging import send_message_with_phone_number
  self.assertEqual(send_message_with_phone_number.__module__,'tool_sandbox.tools.messaging')
