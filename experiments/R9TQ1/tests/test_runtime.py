
import unittest,tempfile,shutil,json,copy
from pathlib import Path
from tq.runtime import prepare,qualify,audit,export
from tq.contract import ContractError
from tq.common import read,write
from helpers import freeze,Wire
ROOT=Path(__file__).resolve().parents[1]
class RuntimeTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)/"kit"
  shutil.copytree(ROOT,self.root,ignore=shutil.ignore_patterns("runs","uploads",".venv","__pycache__","PREPARED.json",".run.lock"))
  freeze(self.root)
 def tearDown(self):self.tmp.cleanup()
 def start(self,mode="normal"):
  prepare(self.root);self.wire=Wire(mode)
  return qualify(self.root,12,secret="dummy-key-not-a-real-key",exchange=self.wire)
 def test_prepare_no_calls(self):
  p=prepare(self.root);self.assertIn("source_manifest_sha256",p)
  self.assertFalse((self.root/"runs").exists())
 def test_full_roundtrip(self):
  r=self.start();self.assertEqual(r["status"],"completed")
  self.assertEqual(self.wire.n,10);self.assertTrue(r["qualification_pass"])
  a=audit(self.root);self.assertTrue(a["mechanical_pass"]);self.assertEqual(a["reconstructed_requests"],10)
 def test_completed_no_new_calls(self):
  self.start();n=self.wire.n
  qualify(self.root,12,secret="not-read",exchange=self.wire);self.assertEqual(self.wire.n,n)
 def test_cap_fixture(self):
  r=self.start("cap");self.assertEqual(self.wire.n,12);self.assertEqual(r["status"],"completed")
 def test_text_actions_not_executed(self):
  r=self.start("prose");self.assertFalse(r["qualification_pass"]);self.assertEqual(self.wire.n,1)
  e=read(self.root/"runs/qualification/cases/q0_read/result.json")
  self.assertEqual(e["events"],[]);self.assertEqual(e["final_world"],e["final_snapshot"]["_world_placeholder"] if "_world_placeholder" in e["final_snapshot"] else read(self.root/"fixtures/cases.json")[0]["world_before"])
 def test_invalid_batch_no_dispatch(self):
  r=self.start("bad_batch");self.assertEqual(r["status"],"paused");self.assertEqual(self.wire.n,1)
  self.assertEqual(read(self.root/"runs/qualification/cases/q0_read/boundary.json")["events"],[])
 def test_paused_blocks_resample(self):
  self.start("bad_batch")
  with self.assertRaises(ContractError):qualify(self.root,12,secret="x",exchange=self.wire)
  self.assertEqual(self.wire.n,1)
 def test_source_tampering_blocks(self):
  prepare(self.root);(self.root/"config.json").write_text("{}")
  with self.assertRaises(ContractError):qualify(self.root,12,secret="x",exchange=Wire())
 def test_audit_changed_tool_reply_rejected(self):
  self.start();p=self.root/"runs/qualification/cases/q0_read/result.json";e=read(p)
  e["turns"][0]["tool_messages"][0]["content"]='{"ok":true,"value":false}'
  write(p,e);self.assertFalse(audit(self.root)["mechanical_pass"])
 def test_audit_changed_request_reasoning_rejected(self):
  self.start();p=self.root/"runs/qualification/attempts/000002_request.json";r=read(p)
  r["payload"]["messages"][-2]["reasoning_content"]="replaced";write(p,r)
  self.assertFalse(audit(self.root)["mechanical_pass"])
 def test_failure_can_export(self):
  self.start("bad_batch");audit(self.root);path=export(self.root)
  self.assertTrue(Path(path).exists())
 def test_confirm_cap_not_expandable(self):
  prepare(self.root)
  with self.assertRaises(ContractError):qualify(self.root,120,secret="x",exchange=Wire())
 def test_private_goal_not_in_requests(self):
  self.start()
  for p in self.wire.payloads:
   user=p["messages"][1]["content"]
   self.assertNotIn("world_before",user);self.assertNotIn('"contract"',user)
 def test_batch_result_receipts_are_original(self):
  self.start()
  for p in self.wire.payloads:
   for m in p["messages"]:
    if m["role"]=="assistant":self.assertIn("reasoning_content",m)
    if m["role"]=="tool":self.assertIn("tool_call_id",m)
if __name__=="__main__":unittest.main()
