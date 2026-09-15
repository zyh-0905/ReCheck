import unittest,tempfile,copy
from pathlib import Path
from r7c import journal

def body():return {'id':'response1','model':'deepseek-flash','system_fingerprint':'f','choices':[{'finish_reason':'stop','message':{'content':'{"ok":true}'}}], 'usage':{'prompt_tokens':10,'completion_tokens':5,'total_tokens':15,'completion_tokens_details':{'reasoning_tokens':2}}}
class ClientTests(unittest.TestCase):
 def test_valid(self):self.assertEqual(journal.validate_response(body(),None)[0],{'ok':True})
 def test_missing_usage(self):
  b=body();del b['usage']
  with self.assertRaises(journal.Paused):journal.validate_response(b,None)
 def test_wrong_model(self):
  b=body();b['model']='other'
  with self.assertRaises(journal.Paused):journal.validate_response(b,None)
 def test_bad_total(self):
  b=body();b['usage']['total_tokens']=16
  with self.assertRaises(journal.Paused):journal.validate_response(b,None)
 def test_truncated(self):
  b=body();b['choices'][0]['finish_reason']='length'
  with self.assertRaises(journal.Paused):journal.validate_response(b,None)
 def test_identity_change(self):
  with self.assertRaises(journal.Paused):journal.validate_response(body(),{'model':'deepseek-flash','system_fingerprint':'x'})
 def test_strict_json(self):
  b=body();b['choices'][0]['message']['content']='{"x":1,"x":2}'
  with self.assertRaises(journal.Paused):journal.validate_response(b,None)
 def test_negative_usage(self):
  b=body();b['usage']['prompt_tokens']=-1
  with self.assertRaises(journal.Paused):journal.validate_response(b,None)
 def test_reasoning_usage(self):
  b=body();b['usage']['completion_tokens_details']['reasoning_tokens']=9
  with self.assertRaises(journal.Paused):journal.validate_response(b,None)
if __name__=='__main__':unittest.main()
