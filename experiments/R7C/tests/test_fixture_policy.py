import unittest
from r7c.core import ROOT,read
from r7c.actor import messages
from r7c.journal import payload
from http_fixture import decide
class FixturePolicyTests(unittest.TestCase):
 def test_all_initial_actions(self):
  p=read(ROOT/'configs/protocol.json')
  for c in read(ROOT/'fixtures/cases.json'):
   obj=decide(payload(messages(c,'memory_standard',[]),p));self.assertEqual(obj['action'],'tool')
if __name__=='__main__':unittest.main()
