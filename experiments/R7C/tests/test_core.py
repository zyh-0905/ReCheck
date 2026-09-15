import unittest,json,tempfile
from pathlib import Path
from r7c import core
class CoreTests(unittest.TestCase):
 def test_object(self):self.assertEqual(core.strict_json('{"a":1}'),{'a':1})
 def test_dupe(self):
  with self.assertRaises(ValueError):core.strict_json('{"a":1,"a":2}')
 def test_nan(self):
  with self.assertRaises(ValueError):core.strict_json('{"a":NaN}')
 def test_list(self):
  with self.assertRaises(ValueError):core.strict_json('[]')
 def test_code_fence(self):
  with self.assertRaises(ValueError):core.strict_json('```json\n{}\n```')
 def test_finish(self):self.assertEqual(core.action({'action':'finish','summary':'done'})['action'],'finish')
 def test_tool(self):self.assertEqual(core.action({'action':'tool','name':'get_wifi_status','arguments':{}})['arguments'],{})
 def test_extra(self):
  with self.assertRaises(ValueError):core.action({'action':'finish','summary':'ok','code':'rm'})
 def test_missing(self):
  with self.assertRaises(ValueError):core.action({'action':'tool','name':'x'})
 def test_write_once(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'a';core.write_once(p,{'a':1});core.write_once(p,{'a':1})
   with self.assertRaises(ValueError):core.write_once(p,{'a':2})
if __name__=='__main__':unittest.main()
