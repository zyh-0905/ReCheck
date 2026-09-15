
import unittest,tempfile,copy,json
from pathlib import Path
from r7clib.cases import make_cases
from r7clib.experiment import run_episode
from r7clib.audit import audit_episode
from tests.test_workflow import Fake
from pilot.common import write_json,request_payload,digest
class Recording(Fake):
 def __init__(self,cfg,root):super().__init__();self.cfg=cfg;self.root=Path(root)
 def complete(self,lid,messages,meta=None):
  r=super().complete(lid,messages,meta);payload=request_payload(self.cfg,messages)
  r.update(payload=payload,metadata=meta,request_sha256=digest({'endpoint':self.cfg['base_url'],'payload':payload}),
    response={'choices':[{'message':{'content':r['text']},'finish_reason':'stop'}],
    'usage':{'prompt_tokens':10,'completion_tokens':5,'total_tokens':15}})
  write_json(self.root/'calls'/(digest(lid)+'.json'),r);return r
class AuditTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.cs=make_cases();cls.cfg=json.loads((Path(__file__).resolve().parents[1]/'config.example.json').read_text())
 def execute_one(self,d,i=2):
  c=self.cs[i];spec={'episode_id':'test','case_id':c['id'],'phase':'primary','arm':'inherited'}
  r=run_episode(c,spec,Recording(self.cfg,d),Path(d));return c,r
 def test_native_replay(self):
  for i in (0,2,8,10,12):
   with tempfile.TemporaryDirectory() as d:
    c,r=self.execute_one(d,i);used=audit_episode(c,r,self.cfg,d);self.assertEqual(len(used),r['model_calls'])
 def test_edited_score_rejected(self):
  with tempfile.TemporaryDirectory() as d:
   c,r=self.execute_one(d);r['score']['safe_success']=False
   with self.assertRaises(ValueError):audit_episode(c,r,self.cfg,d)
 def test_edited_arguments_rejected(self):
  with tempfile.TemporaryDirectory() as d:
   c,r=self.execute_one(d);r['events'][0]['arguments']['name']='wrong'
   with self.assertRaises(ValueError):audit_episode(c,r,self.cfg,d)
 def test_edited_final_snapshot_rejected(self):
  with tempfile.TemporaryDirectory() as d:
   c,r=self.execute_one(d);r['final_snapshot']['trace_tool']=False
   with self.assertRaises(ValueError):audit_episode(c,r,self.cfg,d)
 def test_edited_model_text_rejected(self):
  with tempfile.TemporaryDirectory() as d:
   c,r=self.execute_one(d);r['turns'][0]['response_text']='{"done":"x"}'
   with self.assertRaises(ValueError):audit_episode(c,r,self.cfg,d)

class TypedAuditTests(unittest.TestCase):
 setUpClass=classmethod(AuditTests.setUpClass.__func__)
 execute_one=AuditTests.execute_one
 def test_boolean_score_cannot_be_integer(self):
  with tempfile.TemporaryDirectory() as d:
   c,r=self.execute_one(d);r['score']['safe_success']=1
   with self.assertRaises(ValueError):audit_episode(c,r,self.cfg,d)
 def test_count_cannot_be_float(self):
  with tempfile.TemporaryDirectory() as d:
   c,r=self.execute_one(d);r['model_calls']=float(r['model_calls'])
   with self.assertRaises(ValueError):audit_episode(c,r,self.cfg,d)
