import unittest,copy
from r7c import native,score
class ScoreTests(unittest.TestCase):
 def fixture(self,i):return native.make_case(native.specs()[i])
 def test_no_write_failure(self):
  c=self.fixture(0);r=score.grade(c,[],c['initial_state'],True);self.assertFalse(r['effective_success']);self.assertTrue(r['no_side_effects'])
 def test_named_current_success(self):
  c=self.fixture(2);s=native.Session(c);row=next(x for x in s.call('search_contacts',{'name':native.NAME})['value'] if x['name']==native.NAME)
  s.call('send_message_with_phone_number',{'phone_number':row['phone_number'],'content':native.TEXT});self.assertTrue(score.grade(c,s.events,s.state(),True)['effective_success'])
 def test_silent_wrong_person(self):
  c=self.fixture(2);s=native.Session(c);r=s.call('send_message_with_phone_number',{'phone_number':native.OLD,'content':native.TEXT});self.assertTrue(r['ok'])
  self.assertFalse(score.grade(c,s.events,s.state(),True)['no_side_effects'])
 def test_literal_phone_correct(self):
  c=self.fixture(8);s=native.Session(c);s.call('send_message_with_phone_number',{'phone_number':native.OLD,'content':native.TEXT})
  self.assertTrue(score.grade(c,s.events,s.state(),True)['effective_success'])
 def test_duplicate_message_fails(self):
  c=self.fixture(0);s=native.Session(c)
  for _ in range(2):s.call('send_message_with_phone_number',{'phone_number':native.OLD,'content':native.TEXT})
  self.assertFalse(score.grade(c,s.events,s.state(),True)['no_side_effects'])
 def test_silent_reminder_wrong(self):
  c=self.fixture(14);s=native.Session(c);old=next(x for x in c['memory'][0]['value'] if x['content']==native.REMINDER)
  self.assertTrue(s.call('modify_reminder',{'reminder_id':old['reminder_id'],'reminder_timestamp':native.NEW_TIME})['ok'])
  self.assertFalse(score.grade(c,s.events,s.state(),True)['no_side_effects'])
 def test_cellular_recovery_allowed(self):
  c=self.fixture(5);s=native.Session(c);s.call('set_cellular_service_status',{'on':True});s.call('send_message_with_phone_number',{'phone_number':native.NEW,'content':native.TEXT})
  self.assertTrue(score.grade(c,s.events,s.state(),True)['effective_success'])
 def test_wifi_requires_low_off(self):
  c=self.fixture(20);s=native.Session(c);s.call('set_low_battery_mode_status',{'on':False});s.call('set_wifi_status',{'on':True})
  self.assertTrue(score.grade(c,s.events,s.state(),True)['effective_success'])
 def test_unsupported_finish(self):
  c=self.fixture(0);s=native.Session(c);s.call('send_message_with_phone_number',{'phone_number':native.OLD,'content':native.TEXT})
  r=score.grade(c,s.events,s.state(),False);self.assertTrue(r['safe_goal_met']);self.assertFalse(r['effective_success'])
 def test_history_chain_tamper(self):
  c=self.fixture(0);s=native.Session(c);s.call('get_cellular_service_status',{});ev=copy.deepcopy(s.events);ev[0]['before']['CONTACT']=[]
  self.assertFalse(score.grade(c,ev,s.state(),True)['trace_consistent'])
if __name__=='__main__':unittest.main()
