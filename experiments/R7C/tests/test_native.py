import unittest
from r7c import native
class NativeTests(unittest.TestCase):
 def test_catalog_size(self):self.assertEqual(len(native.specs()),24)
 def test_families(self):self.assertEqual(len({x['family'] for x in native.specs()}),4)
 def test_public_hidden(self):
  c=native.make_case(native.specs()[2]);p=native.public_input(c,'memory_standard')
  self.assertNotIn('private',p);self.assertNotIn('snapshot',p);self.assertNotIn('condition',p)
 def test_console_reject(self):
  c=native.make_case(native.specs()[0]);c['snapshot']['interactive_console']='bad'
  with self.assertRaises(ValueError):native.Session(c)
 def test_disallowed_tool(self):
  s=native.Session(native.make_case(native.specs()[0]))
  r=s.call('rapid_api_get_request',{'url':'https://example.com'})
  self.assertFalse(r['ok']);self.assertEqual(r['error_type'],'InterfaceError')
 def test_empty_state(self):
  c=native.make_case(native.specs()[0]);s=native.Session(c)
  self.assertEqual(len(s.state()['MESSAGING']),0)
if __name__=='__main__':unittest.main()
