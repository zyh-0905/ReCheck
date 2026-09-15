import unittest,tempfile
from pathlib import Path
from r7c.core import ROOT,read,digest
from r7c.journal import Journal,Paused
from r7c.actor import SMOKE_MESSAGES
from http_fixture import server
class TransportTests(unittest.TestCase):
 def test_no_repeat(self):
  with tempfile.TemporaryDirectory() as d,server() as (url,state):
   j=Journal(Path(d),read(ROOT/'configs/protocol.json'),endpoint=url,fixture=True);j.complete('smoke',SMOKE_MESSAGES,{'phase':'smoke'})
   with self.assertRaises(Paused):j.complete('smoke',SMOKE_MESSAGES,{'phase':'smoke'})
   self.assertEqual(len(state['requests']),1)
 def test_invalid_saved(self):
  with tempfile.TemporaryDirectory() as d,server('invalid_json') as (url,state):
   j=Journal(Path(d),read(ROOT/'configs/protocol.json'),endpoint=url,fixture=True)
   with self.assertRaises(Paused):j.complete('smoke',SMOKE_MESSAGES,{})
   self.assertTrue((Path(d)/'calls'/(digest('smoke')+'.json')).exists())
 def test_truncated_saved(self):
  with tempfile.TemporaryDirectory() as d,server('length') as (url,state):
   j=Journal(Path(d),read(ROOT/'configs/protocol.json'),endpoint=url,fixture=True)
   with self.assertRaises(Paused):j.complete('smoke',SMOKE_MESSAGES,{})
   self.assertTrue((Path(d)/'attempts/000001_result.json').exists())
 def test_external_fixture_rejected(self):
  with tempfile.TemporaryDirectory() as d:
   with self.assertRaises(ValueError):Journal(Path(d),read(ROOT/'configs/protocol.json'),endpoint='https://example.com',fixture=True)
 def test_secret_guard(self):
  with tempfile.TemporaryDirectory() as d,server() as (url,state):
   j=Journal(Path(d),read(ROOT/'configs/protocol.json'),secret='FAKE_TEST_CREDENTIAL',endpoint=url,fixture=True)
   with self.assertRaises(Paused):j.complete('x',[{'role':'user','content':'FAKE_TEST_CREDENTIAL'}],{})
   self.assertEqual(len(state['requests']),0)
if __name__=='__main__':unittest.main()
