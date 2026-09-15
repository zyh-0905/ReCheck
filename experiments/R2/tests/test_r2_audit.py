
import copy,unittest
from r2lib import audit
class AuditTests(unittest.TestCase):
    def base(self):
        case={"stream":1,"cents":[50000,52335],"tasks":[{"type":0,"cutoff":0,"modes":[0,0]}]}
        r={"step":0,"task_type":0,"method":"ttl","worker_view":{"memory":{"amount_divisor":100,"endpoint_inclusive":False}},
           "plan":{"amount_divisor":100,"time_bound":None},"plan_json_error":None,"plan_schema_valid":True,
           "tool_result":{"sum_amount_raw":1023.35},"answer":{"total":10.2335,"count":None},
           "answer_json_error":None,"logical_calls":["p","a"]}
        calls={k:{"response":{"choices":[{"finish_reason":"stop"}]}} for k in ["p","a"]}
        return r,case,calls
    def ev(self,r,c,b):
        self.assertTrue(callable(getattr(audit,"evaluate_record",None)),"evaluate_record missing")
        return audit.evaluate_record(r,c,b)
    def test_legal_old_value_is_stale_not_fresh(self):
        r,c,b=self.base();e=self.ev(r,c,b)
        self.assertTrue(e["stale_related"]);self.assertFalse(e["missing_related"])
        self.assertFalse(e["end_to_end_success"]);self.assertTrue(e["stale_propagation_consistent"])
        self.assertEqual(e["amount_status"],"stale");self.assertFalse(e.get("reference_executor_correct",True))
    def test_correct_fresh_memory(self):
        r,c,b=self.base();r["worker_view"]["memory"]["amount_divisor"]=1;r["plan"]["amount_divisor"]=1;r["answer"]["total"]=1023.35
        e=self.ev(r,c,b);self.assertTrue(e["end_to_end_success"]);self.assertFalse(e["stale_related"])
    def test_irrelevant_stale_value_not_an_exposure(self):
        r,c,b=self.base();c["tasks"][0]["type"]=3;r["task_type"]=3
        r["plan"]={"amount_divisor":None,"time_bound":None};r["tool_result"]={"count_all":2};r["answer"]={"total":None,"count":2}
        e=self.ev(r,c,b);self.assertFalse(e["stale_related"]);self.assertTrue(e["end_to_end_success"])
    def test_count_unused_field_is_contract_error(self):
        r,c,b=self.base();c["tasks"][0]["type"]=3;r["task_type"]=3
        r["plan"]={"amount_divisor":1,"time_bound":None};r["tool_result"]={"error":"INVALID_TOOL_PLAN"}
        r["answer"]={"total":None,"count":None}
        e=self.ev(r,c,b);self.assertTrue(e["interface_failure"]);self.assertFalse(e["json_parse_failure"])
    def test_truncated_and_json_error_are_separate_axes(self):
        r,c,b=self.base();r["answer"]=None;r["answer_json_error"]="JSONDecodeError"
        b["a"]["response"]["choices"][0]["finish_reason"]="length"
        e=self.ev(r,c,b);self.assertTrue(e["truncated"]);self.assertTrue(e["json_parse_failure"])
    def test_missing_memory_not_stale(self):
        r,c,b=self.base();r["worker_view"]["memory"]["amount_divisor"]=None
        e=self.ev(r,c,b);self.assertTrue(e["missing_related"]);self.assertFalse(e["stale_related"])
    def test_float_count_contract_violation(self):
        r,c,b=self.base();c["tasks"][0]["type"]=3;r["task_type"]=3
        r["plan"]={"amount_divisor":None,"time_bound":None};r["tool_result"]={"count_all":2};r["answer"]={"total":None,"count":2.0}
        e=self.ev(r,c,b);self.assertFalse(e["answer_schema_valid"]);self.assertFalse(e["end_to_end_success"]);self.assertTrue(e["answer_value_correct"])
    def test_missing_call_not_silently_success(self):
        r,c,b=self.base();b.pop("a");e=self.ev(r,c,b);self.assertEqual(e["missing_call_records"],1)
