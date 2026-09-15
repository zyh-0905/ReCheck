import unittest
from contract import terminal_valid, project, classify
class ContractTests(unittest.TestCase):
 def test_exact_true(self):self.assertTrue(terminal_valid({'wifi':True},'wifi',True))
 def test_exact_false(self):self.assertTrue(terminal_valid({'wifi':False},'wifi',False))
 def test_wrong_value(self):self.assertFalse(terminal_valid({'wifi':True},'wifi',False))
 def test_no_integer_coercion(self):self.assertFalse(terminal_valid({'wifi':1},'wifi',True))
 def test_missing(self):self.assertFalse(terminal_valid({},'wifi',False))
 def test_other_fields_do_not_change_target(self):self.assertTrue(terminal_valid({'wifi':False,'cellular':True},'wifi',False))
 def test_false_accept(self):self.assertEqual(classify(1.0,False),'full_score_terminal_mismatch')
 def test_partial_is_not_full(self):self.assertEqual(classify(0.5,False),'not_full_score_terminal_false')
 def test_agreement(self):self.assertEqual(classify(1.0,True),'full_score_terminal_true')
 def test_projection_only_drops_elapsed(self):
  self.assertEqual(project({'elapsed_seconds':1,'value':3,'nested':[{'elapsed_seconds':2,'x':False}]}),{'value':3,'nested':[{'x':False}]})
 def test_not_drop_uuid_or_error(self):self.assertEqual(project({'error':'ValueError','id':'abc'}),{'error':'ValueError','id':'abc'})
