import unittest
from paper_tables import flag, summarize, validate_rows

def row(key='a', full='True', conflict='False', review='NOT_A_FULL_SCORE_NEGATIVE_CANDIDATE', task='t', model='m', persona='expert'):
    return dict(key=key,source_full=full,conservative_conflict=conflict,review_class=review,sample_id=task,model=model,persona=persona)

class PaperTableTests(unittest.TestCase):
    def test_bool_true(self): self.assertTrue(flag('True'))
    def test_bool_false(self): self.assertFalse(flag('False'))
    def test_reject_unknown_bool(self):
        with self.assertRaises(ValueError): flag('unknown')
    def test_duplicate_rejected(self):
        with self.assertRaises(ValueError): validate_rows([row(),row()])
    def test_conflict_requires_full(self):
        with self.assertRaises(ValueError): validate_rows([row(full='False',conflict='True',review='CALENDAR_EFFECT_CONFLICT')])
    def test_count_records_not_tasks(self):
        s=summarize([row('a'),row('b')]); self.assertEqual((s['records'],s['tasks']), (2,1))
    def test_count_full(self): self.assertEqual(summarize([row('a'),row('b',full='False')])['source_full'],1)
    def test_calendar_and_no_commit_separate(self):
        s=summarize([row('a',conflict='True',review='CALENDAR_EFFECT_CONFLICT'),row('b',conflict='True',review='NO_NATIVE_ADD_TEXT_ONLY')])
        self.assertEqual((s['conflicts'],s['calendar'],s['no_commit']),(2,1,1))
    def test_authorized_not_counted(self):
        s=summarize([row(review='EXPLICIT_USER_DATE_REVISION')]); self.assertEqual(s['conflicts'],0)
    def test_empty(self): self.assertEqual(summarize([])['records'],0)
if __name__=='__main__': unittest.main()
