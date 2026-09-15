import unittest
from r4lib import protocol,offline,experiment

class ProtocolTests(unittest.TestCase):
    def test_call_count(self):
        p=protocol.load_protocol();ids=protocol.logical_ids(p)
        self.assertEqual(len(ids),408);self.assertEqual(len(set(ids)),408)
        self.assertEqual(sum(i.endswith('/repeat') for i in ids),24)
    def test_all_cases_retained(self):
        p=protocol.load_protocol();cs=protocol.make_cases(p)
        self.assertEqual(len(cs),12)
        self.assertEqual([c['stream'] for c in cs],list(range(12)))
    def test_distinct_seed_streams(self):
        p=protocol.load_protocol()
        for key in ['task_seed','world_seed','data_seed']:
            self.assertEqual(len({s[key] for s in p['streams']}),12)
    def test_counterexample_available(self):
        self.assertTrue(callable(getattr(offline,'coupling_counterexample',None)))
    def test_preflight_excludes_private_world(self):
        from unittest.mock import patch
        with patch.object(protocol,'make_cases',side_effect=AssertionError('hidden-world use')):
            self.assertTrue(offline.preflight(protocol.load_protocol())['pass'])
    def test_executable_experiment(self):
        self.assertTrue(callable(getattr(experiment,'run',None)))
