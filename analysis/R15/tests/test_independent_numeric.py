import unittest,sys
from pathlib import Path
from datetime import datetime,timezone
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from independent_numeric import calendar_violation

def epoch(y,m,d,h=9):return datetime(y,m,d,h,tzinfo=timezone.utc).timestamp()
class IndependentNumericTests(unittest.TestCase):
 def test_past_not_tomorrow(self):self.assertTrue(calendar_violation(epoch(2025,9,16),epoch(2023,10,17),28800,'tomorrow'))
 def test_saturday_not_friday(self):self.assertTrue(calendar_violation(epoch(2025,9,16),epoch(2025,9,20),28800,'friday'))
 def test_near_friday_allowed(self):self.assertFalse(calendar_violation(epoch(2025,9,16),epoch(2025,9,19),28800,'friday'))
 def test_following_friday_allowed(self):self.assertFalse(calendar_violation(epoch(2025,9,16),epoch(2025,9,26),28800,'friday'))
 def test_imprecise_minutes_not_calendar_error(self):self.assertFalse(calendar_violation(epoch(2025,9,16),epoch(2025,9,17)+1200,28800,'tomorrow'))
 def test_no_user_target_claim(self):self.assertIsNone(calendar_violation(epoch(2025,9,16),epoch(2025,9,20),28800,'unsupported'))
