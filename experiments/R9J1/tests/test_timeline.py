import unittest,copy
from r9lib.scenarios import build_cases
from r9lib.timeline import Timeline
from r9lib.scoring import grade
class TimelineTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.cs=build_cases()
 def case(self,fam,variant):return next(c for c in self.cs if c['family']==fam and c['variant']==variant)
 def test_count(self):self.assertEqual(len(self.cs),16)
 def test_public_inputs_do_not_reveal_event(self):
  for fam in ('person','phone','reminder','wifi'):
   cs=[c for c in self.cs if c['family']==fam]
   self.assertTrue(all(c['public']==cs[0]['public'] for c in cs));self.assertTrue(all(c['snapshot']==cs[0]['snapshot'] for c in cs))
 def test_only_one_change_and_stale_raw_response(self):
  c=self.case('person','post_relevant');t=Timeline(c)
  a=t.call('search_contacts',{'name':c['contract']['name']});self.assertTrue(t.fired)
  b=t.call('search_contacts',{'name':c['contract']['name']})
  self.assertNotEqual(a['value'][0]['phone_number'],b['value'][0]['phone_number'])
  self.assertEqual(sum(e['scope']=='environment' for e in t.events),2)
 def test_pre_change_visible_first_read(self):
  c=self.case('person','pre_relevant');t=Timeline(c)
  a=t.call('search_contacts',{'name':c['contract']['name']});self.assertEqual(a['value'][0]['phone_number'],c['new_phone'])
 def test_skipped_read_no_postcommit_event(self):
  c=self.case('person','post_relevant');t=Timeline(c)
  t.call('send_message_with_phone_number',{'phone_number':c['old_phone'],'content':c['contract']['content']})
  t.call('search_contacts',{'name':c['contract']['name']})
  self.assertFalse(t.fired);self.assertTrue(t.missed)
 def test_silent_wrong_write_real_tool_success(self):
  c=self.case('person','post_relevant');t=Timeline(c)
  rs=t.call('search_contacts',{'name':c['contract']['name']})['value']
  t.call('send_message_with_phone_number',{'phone_number':rs[0]['phone_number'],'content':c['contract']['content']})
  r=grade(c['contract'],c['world_before'],t.events,t.world())
  self.assertTrue(r['tool_success_proxy']);self.assertTrue(r['wrong_write']);self.assertFalse(r['goal_final'])
 def test_second_read_can_recover_before_write(self):
  c=self.case('person','post_relevant');t=Timeline(c)
  for _ in range(2):rs=t.call('search_contacts',{'name':c['contract']['name']})['value']
  t.call('send_message_with_phone_number',{'phone_number':rs[0]['phone_number'],'content':c['contract']['content']})
  self.assertTrue(grade(c['contract'],c['world_before'],t.events,t.world())['trace_safe_success'])
 def test_wifi_visible_error_then_recovery(self):
  c=self.case('wifi','post_relevant');t=Timeline(c)
  self.assertFalse(t.call('get_low_battery_mode_status',{})['value'])
  self.assertFalse(t.call('set_wifi_status',{'on':True})['ok'])
  t.call('set_low_battery_mode_status',{'on':False});t.call('set_wifi_status',{'on':True})
  r=grade(c['contract'],c['world_before'],t.events,t.world())
  self.assertTrue(r['trace_safe_success']);self.assertEqual(r['tool_errors'],1)
 def test_no_hidden_trigger_in_observation(self):
  c=self.case('person','post_relevant');t=Timeline(c)
  self.assertEqual(set(t.call('search_contacts',{'name':c['contract']['name']})),{'ok','value','error'})
