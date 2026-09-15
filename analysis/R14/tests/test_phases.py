import unittest,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from phase_audit import phase_check

def u(s,rel=None):
 d={'role':'user','content':s}
 if rel is not None:d['user_details']={'database_update':{'CONTACT':[{'person_id':'a','relationship':rel}]}}
 return d
class Tests(unittest.TestCase):
 def test_no_revision_boundary(self):self.assertIsNone(phase_check({'trajectory':[[u('Make enemy','friend')]]})['scoped_complete'])
 def test_restoring_initial_without_first_effect_not_success(self):
  r=phase_check({'trajectory':[[u('Make enemy','friend')],[u('back to friend')]]});self.assertFalse(r['scoped_complete'])
 def test_correct_scoped_sequence(self):
  s={'trajectory':[[u('Make enemy','friend'),u('checking','enemy')],[u('back to friend','friend')]]};self.assertTrue(phase_check(s)['scoped_complete'])
 def test_missing_second_goal_not_complete(self):
  s={'trajectory':[[u('Make enemy','friend'),u('checking','enemy')],[u('back to friend')]]};self.assertFalse(phase_check(s)['scoped_complete'])
 def test_unknown_not_failure(self):
  self.assertIsNone(phase_check({'trajectory':[[u('Make enemy')],[u('back to friend')]]})['scoped_complete'])
