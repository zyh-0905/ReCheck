
import copy,unittest
from r2lib import protocol as p
class ProtocolTests(unittest.TestCase):
    def spec(self):
        self.assertTrue(callable(getattr(p,"load_protocol",None)),"load_protocol missing")
        return p.load_protocol()
    def test_fixed_calls_and_methods(self):
        s=self.spec();self.assertEqual(s["logical_calls"],484)
        self.assertEqual(s["methods"],["recheck","myopic","ttl","always","never"])
    def test_outcome_blind_preflight(self):
        s=self.spec();r=p.preflight(s)
        self.assertTrue(r["pass"]);self.assertEqual(r["outcome_labels_inspected"],0)
        self.assertEqual(r["hidden_modes_constructed"],0)
        self.assertEqual(sum(x["trajectory_probe_disagreements"] for x in r["streams"]),8)
        self.assertEqual([x["trajectory_probe_disagreements"] for x in r["streams"][:2]],[0,0])
    def test_seeds_new_and_fixed(self):
        s=self.spec();c=p.make_cases(s)
        self.assertEqual([x["seed"] for x in c],[920101,920102,920103,920104])
        self.assertEqual(p.make_cases(s),c)
    def test_public_task_sequence_not_affected_by_world_seed(self):
        s=self.spec();alt=copy.deepcopy(s)
        for x in alt["streams"]:x["world_seed"]+=100
        a=p.make_cases(s);b=p.make_cases(alt)
        self.assertEqual([[t["type"] for t in c["tasks"]] for c in a],[[t["type"] for t in c["tasks"]] for c in b])
    def test_call_cap_cannot_diverge(self):
        s=self.spec();s["logical_calls"]-=1
        with self.assertRaises(ValueError):p.validate_protocol(s)
