import unittest,copy,json,tempfile,zipfile
from pathlib import Path
from r7c.core import ROOT,read,MAIN_CAP,TOTAL_CAP,safe_unzip
from r7c.actor import messages
from r7c.native import specs,make_case,Session
from r7c.experiment import schedule
from r7c.rules import run_rule
class ProtocolTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.cases=read(ROOT/'fixtures/cases.json')
 def test_size_caps(self):self.assertEqual(len(self.cases)*3*6,MAIN_CAP);self.assertEqual(MAIN_CAP+1,TOTAL_CAP)
 def test_schedule_unique(self):self.assertEqual(len(set(schedule(self.cases))),72)
 def test_same_memory_across_conditions(self):
  for f in ('person_message','literal_message','reminder_retime','wifi_dependency'):
   arr=[c for c in self.cases if c['family']==f]
   self.assertTrue(all(c['memory']==arr[0]['memory'] and c['task']==arr[0]['task'] for c in arr))
 def test_private_excluded(self):
  for c in self.cases:
   q=json.loads(messages(c,'memory_standard',[])[1]['content'])
   self.assertEqual(set(q),{'task','historical_memory','ordinary_observations','available_tools','action_history','decisions_remaining'})
 def test_no_memory_only_one_field_changes(self):
  c=self.cases[3];a=json.loads(messages(c,'no_memory',[])[1]['content']);b=json.loads(messages(c,'memory_standard',[])[1]['content']);b['historical_memory']=[];self.assertEqual(a,b)
 def test_read_only_does_not_change_state(self):
  s=Session(self.cases[0]);before=s.state();s.call('search_contacts',{'name':'Mira Chen'});self.assertEqual(before,s.state())
 def test_no_arbitrary_keyword(self):
  s=Session(self.cases[0]);self.assertFalse(s.call('search_contacts',{'__import__':'os'})['ok'])
 def test_zip_traversal(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'bad.zip'
   with zipfile.ZipFile(p,'w') as z:z.writestr('../escape','x')
   with self.assertRaises(ValueError):safe_unzip(p,Path(d)/'out')
 def test_strong_script_all_cases(self):
  for c in self.cases:
   r=run_rule(c,'always_resolve');self.assertTrue(r['score']['effective_success'],c['id']);self.assertLessEqual(r['decision_count'],6)
 def test_replay_same_native_output(self):
  from r7c.native import OLD,TEXT
  c=self.cases[0];a=Session(c);a.call('send_message_with_phone_number',{'phone_number':OLD,'content':TEXT});b=Session(c);b.call('send_message_with_phone_number',{'phone_number':OLD,'content':TEXT},replay_event=a.events[0])
  self.assertEqual(a.state(),b.state());self.assertEqual(a.events[0]['response'],b.events[0]['response'])
if __name__=='__main__':unittest.main()
