
import unittest,json,tempfile,copy
from pathlib import Path
from tq.journal import Client
from tq.contract import build_payload,ContractError
from test_contract import TOOLS,CFG,response,call
class JournalTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);self.count=0
  self.payload=build_payload(CFG,[{"role":"user","content":"Read it"}],TOOLS)
 def tearDown(self):self.tmp.cleanup()
 def wire(self,p):
  self.count+=1;b=response([call(identifier=f"c{self.count}")]);b["id"]=f"r{self.count}"
  return 200,json.dumps(b).encode()
 def client(self,exchange=None):return Client(CFG,self.root,TOOLS,"dummy-key-for-local-test",exchange=exchange or self.wire)
 def test_raw_bytes_journal_and_validation(self):
  c=self.client();r=c.complete("x",self.payload,{},TOOLS,set())
  self.assertEqual(r["validated"]["kind"],"tools")
  self.assertTrue((self.root/"attempts/000001_response.raw").exists())
  self.assertEqual(json.loads((self.root/"attempts/000001_request.json").read_text())["payload"],self.payload)
 def test_no_second_request_for_same_logical_id(self):
  c=self.client();c.complete("x",self.payload,{},TOOLS,set());c.complete("x",self.payload,{},TOOLS,set())
  self.assertEqual(self.count,1)
 def test_metadata_change_rejected(self):
  c=self.client();c.complete("x",self.payload,{},TOOLS,set())
  with self.assertRaises(ContractError):c.complete("x",self.payload,{"changed":1},TOOLS,set())
  self.assertEqual(self.count,1)
 def test_journal_budget_hard(self):
  c=self.client()
  for i in range(12):c.complete(str(i),self.payload,{},TOOLS,set())
  with self.assertRaises(ContractError):c.complete("overflow",self.payload,{},TOOLS,set())
  self.assertEqual(self.count,12)
 def test_orphan_no_retry(self):
  c=self.client();d=self.root/"attempts";d.mkdir(exist_ok=True)
  (d/"000001_request.json").write_text(json.dumps({"logical_id":"x"}))
  with self.assertRaises(ContractError):c.complete("x",self.payload,{},TOOLS,set())
  self.assertEqual(self.count,0)
 def test_http_error_raw_retained_and_no_retry(self):
  def bad(p):self.count+=1;return 400,b'{"error":"unsupported"}'
  c=self.client(bad)
  for _ in range(2):
   with self.assertRaises(ContractError):c.complete("x",self.payload,{},TOOLS,set())
  self.assertEqual(self.count,1)
  self.assertIn("unsupported",(self.root/"attempts/000001_response.raw").read_text())
 def test_malformed_native_reply_pauses_without_repair(self):
  def bad(p):self.count+=1;return 200,b'{"choices":[]}'
  c=self.client(bad)
  with self.assertRaises(ContractError):c.complete("x",self.payload,{},TOOLS,set())
  self.assertEqual(self.count,1)
 def test_wire_is_redacted_if_it_echoes_key(self):
  key="dummy-key-for-local-test"
  def bad(p):return 400,('problem '+key).encode()
  with self.assertRaises(ContractError):self.client(bad).complete("x",self.payload,{},TOOLS,set())
  self.assertNotIn(key,(self.root/"attempts/000001_response.raw").read_text())
 def test_request_key_never_sent(self):
  p=copy.deepcopy(self.payload);p["messages"][0]["content"]="dummy-key-for-local-test"
  with self.assertRaises(ContractError):self.client().complete("x",p,{},TOOLS,set())
  self.assertEqual(self.count,0)
 def test_no_duplicate_response_id(self):
  def same(p):self.count+=1;return 200,json.dumps(response([call()])).encode()
  c=self.client(same);c.complete("x",self.payload,{},TOOLS,set())
  with self.assertRaises(ContractError):c.complete("y",self.payload,{},TOOLS,set())
if __name__=="__main__":unittest.main()
