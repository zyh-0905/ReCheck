
import unittest
from r2lib import accounting as a
class AccountingTests(unittest.TestCase):
    def fn(self,name):
        self.assertTrue(callable(getattr(a,name,None)),name+" missing");return getattr(a,name)
    def rates(self):
        return {"enabled":True,"currency":"TEST_NOT_REAL","source":"unit-test fixture, not real provider prices",
                "model_ids":["test"],"valid_from_utc":"2026-09-01T00:00:00+00:00","valid_until_utc":"2026-10-01T00:00:00+00:00",
                "off_peak":{"input_per_million":1,"cached_input_per_million":0.02,"output_per_million":4},
                "peak":{"input_per_million":2,"cached_input_per_million":0.04,"output_per_million":8},
                "peak_windows_utc":[{"weekdays":[0,1,2,3,4],"start":"06:00","end":"10:00"}]}
    def call(self):
        return {"started_utc":"2026-09-12T08:00:00+00:00","ended_utc":"2026-09-12T08:01:00+00:00",
                "payload":{"model":"test"},"status":"ok","response":{"usage":{"prompt_tokens":1000,"prompt_cache_hit_tokens":500,"prompt_cache_miss_tokens":500,"completion_tokens":100}}}
    def test_saturday_is_not_weekday_peak(self):
        q=self.fn("price_call")(self.call(),self.rates());self.assertEqual(q["rate_period"],"off_peak")
        self.assertAlmostEqual(q["estimate"],.00091)
    def test_unknown_price_not_zero(self):
        self.assertIsNone(self.fn("price_call")(self.call(),{"enabled":False})["estimate"])
    def test_conflicting_cache_uses_unknown_not_guess(self):
        c=self.call();c["response"]["usage"]["prompt_tokens_details"]={"cached_tokens":20}
        q=self.fn("price_call")(c,self.rates());self.assertIsNone(q["estimate"])
    def test_crossing_period_unknown(self):
        c=self.call();c["started_utc"]="2026-09-11T09:59:59+00:00";c["ended_utc"]="2026-09-11T10:00:01+00:00"
        q=self.fn("price_call")(c,self.rates());self.assertIsNone(q["estimate"]);self.assertEqual(q["reason"],"crosses_rate_boundary")
    def test_missing_usage_never_zero(self):
        n=self.fn("normalize_usage")({});self.assertIsNone(n["prompt_tokens"]);self.assertIsNone(n["completion_tokens"])
    def test_invalid_reasoning_flagged(self):
        n=self.fn("normalize_usage")({"prompt_tokens":10,"completion_tokens":5,"completion_tokens_details":{"reasoning_tokens":6}})
        self.assertIn("reasoning_exceeds_completion",n["issues"])
    def test_other_model_not_priced(self):
        c=self.call();c["payload"]["model"]="other"
        self.assertIsNone(self.fn("price_call")(c,self.rates())["estimate"])
    def test_expired_schedule_not_priced(self):
        c=self.call();c["started_utc"]="2026-10-02T08:00:00+00:00";c["ended_utc"]="2026-10-02T08:01:00+00:00"
        self.assertIsNone(self.fn("price_call")(c,self.rates())["estimate"])
