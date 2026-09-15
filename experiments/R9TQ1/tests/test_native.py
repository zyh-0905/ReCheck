
import unittest,json,copy,tempfile
from pathlib import Path
from tq.engine import initial_messages,qualification,run_case
from legacy.native import NativeSession,FUNCTIONS
ROOT=Path(__file__).resolve().parents[1]
CASES=json.loads((ROOT/"fixtures/cases.json").read_text())
class NativeTests(unittest.TestCase):
 def test_public_prompt_no_private_labels(self):
  ms=initial_messages(CASES[1]);s=json.dumps(ms)
  self.assertIn("explicit phone number",s);self.assertNotIn("world_before",s)
  self.assertNotIn("post_relevant",s);self.assertNotIn("contract",s)
  self.assertNotIn("TOOL_RESULT",s)
 def test_missing_observation_cannot_pass(self):
  c=CASES[0]
  q=qualification(c,[],c["world_before"],True,"CELLULAR_ON")
  self.assertFalse(q["qualified"]);self.assertFalse(q["roundtrip_ready"])
 def test_real_readonly_observation(self):
  c=CASES[0];s=NativeSession(c["snapshot"]);s.call("get_cellular_service_status",{})
  q=qualification(c,s.events,s.world(),True,"CELLULAR_ON")
  self.assertTrue(q["qualified"]);self.assertTrue(q["task_state_ok"])
 def test_wrong_readonly_final_not_pass(self):
  c=CASES[0];s=NativeSession(c["snapshot"]);s.call("get_cellular_service_status",{})
  self.assertFalse(qualification(c,s.events,s.world(),True,"CELLULAR_OFF")["qualified"])
 def test_statement_only_not_message_send(self):
  c=CASES[1];s=NativeSession(c["snapshot"])
  self.assertFalse(qualification(c,[],s.world(),True,"Sent successfully")["qualified"])
 def test_real_message_feedback(self):
  c=CASES[1];s=NativeSession(c["snapshot"])
  s.call("send_message_with_phone_number",{"phone_number":c["contract"]["phone_number"],"content":c["contract"]["content"]})
  self.assertTrue(qualification(c,s.events,s.world(),True,"Sent")["qualified"])
 def test_duplicate_send_disqualifies(self):
  c=CASES[1];s=NativeSession(c["snapshot"])
  for _ in range(2):
   s.call("send_message_with_phone_number",{"phone_number":c["contract"]["phone_number"],"content":c["contract"]["content"]})
  self.assertFalse(qualification(c,s.events,s.world(),True,"Sent")["qualified"])
 def test_reminder_read_mutate_read(self):
  c=CASES[2];s=NativeSession(c["snapshot"])
  r=s.call("search_reminder",{"content":c["contract"]["title"]})
  ident=r["value"][0]["reminder_id"]
  s.call("modify_reminder",{"reminder_id":ident,"reminder_timestamp":c["contract"]["timestamp"]})
  s.call("search_reminder",{"reminder_id":ident})
  self.assertTrue(qualification(c,s.events,s.world(),True,"Updated")["qualified"])
 def test_no_explicit_termination(self):
  c=CASES[0];s=NativeSession(c["snapshot"]);s.call("get_cellular_service_status",{})
  self.assertFalse(qualification(c,s.events,s.world(),False,"")["qualified"])
if __name__=="__main__":unittest.main()
