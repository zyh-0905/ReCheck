
import unittest,json,copy,tempfile,shutil
from pathlib import Path
from tq.contract import validate_response,validate_history,tool_reply,ContractError,build_payload
from tq.common import no_network,read,write
from tq.runtime import prepare,qualify,audit,export
from test_contract import TOOLS,CFG,response,call
from helpers import freeze,Wire
ROOT=Path(__file__).resolve().parents[1]
class EdgeCases(unittest.TestCase):
 def test_observed_legacy_content_never_becomes_calls(self):
  text=(ROOT/"tests/observed_legacy_response.txt").read_text()
  v=validate_response(response(content=text),TOOLS)
  self.assertEqual(v["calls"],[]);self.assertEqual(v["kind"],"final")
 def test_duplicate_tool_reply(self):
  m=[{"role":"user","content":"x"},response([call()])["choices"][0]["message"],
     tool_reply("c1",{}),tool_reply("c1",{})]
  with self.assertRaises(ContractError):validate_history(m)
 def test_two_calls_require_two_matched_replies(self):
  m=[{"role":"user","content":"x"},response([call(),call("get_wifi_status",identifier="c2")])["choices"][0]["message"],
     tool_reply("c1",{"ok":True}),tool_reply("c2",{"ok":True})]
  validate_history(m)
  m[-1]["tool_call_id"]="c1"
  with self.assertRaises(ContractError):validate_history(m)
 def test_thinking_not_forced_tool(self):
  p=build_payload(CFG,[{"role":"user","content":"x"}],TOOLS)
  self.assertEqual(p["tool_choice"],"auto")
  self.assertFalse(any(t["function"].get("strict") for t in p["tools"]))
 def test_network_block_native(self):
  import socket
  with no_network(),self.assertRaises(RuntimeError):socket.create_connection(("example.com",443))
 def test_null_reasoning_returned_exactly(self):
  b=response([call()]);b["choices"][0]["message"]["reasoning_content"]=None
  self.assertIsNone(validate_response(b,TOOLS)["message"]["reasoning_content"])
 def test_tool_args_are_not_eval(self):
  with self.assertRaises(ContractError):
   validate_response(response([call(arguments="__import__('os').system('touch bad')")]),TOOLS)
 def test_early_failed_qualification_is_terminal(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d)/"kit";shutil.copytree(ROOT,root,ignore=shutil.ignore_patterns("runs","uploads",".venv","__pycache__","PREPARED.json",".run.lock"))
   freeze(root);prepare(root);w=Wire("prose")
   r=qualify(root,12,secret="dummy-key-for-local-only",exchange=w)
   self.assertEqual(r["status"],"completed_not_qualified")
   qualify(root,12,secret="unused",exchange=w);self.assertEqual(w.n,1)
   a=audit(root);self.assertTrue(a["mechanical_pass"]);self.assertFalse(a["qualification_pass"])
 def test_paused_raw_ledger_audited(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d)/"kit";shutil.copytree(ROOT,root,ignore=shutil.ignore_patterns("runs","uploads",".venv","__pycache__","PREPARED.json",".run.lock"))
   freeze(root);prepare(root);w=Wire("bad_batch");qualify(root,12,secret="dummy-key-for-local-only",exchange=w)
   a=audit(root)
   self.assertTrue(a["mechanical_pass"],str(a));self.assertFalse(a["execution_complete"])
   self.assertEqual(a["reconstructed_requests"],1)
if __name__=="__main__":unittest.main()
