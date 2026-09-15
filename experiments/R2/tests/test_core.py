import json, tempfile, unittest
from pathlib import Path
from pilot import common as c

class TestCore(unittest.TestCase):
    def test_implementation_exists(self):
        self.assertTrue(callable(getattr(c, 'strict_json_object', None)))
    def test_json_rejects_duplicates(self):
        with self.assertRaises(ValueError): c.strict_json_object('{"a":1,"a":2}')
    def test_json_rejects_nan(self):
        with self.assertRaises(ValueError): c.strict_json_object('{"a":NaN}')
    def test_json_rejects_explanation(self):
        with self.assertRaises(ValueError): c.strict_json_object('Here is {"a":1}')
    def test_json_allows_single_fence(self):
        self.assertEqual(c.strict_json_object('```json\n{"a":1}\n```'), {'a':1})
    def test_bool_is_not_number(self):
        self.assertFalse(c.is_number(True)); self.assertTrue(c.is_number(1.25))
    def test_unsafe_url(self):
        for url in ['http://example.com/v1','https://user:pass@x/v1','https://x/v1?key=abc']:
            with self.assertRaises(ValueError): c.validate_base_url(url)
    def test_loopback_allowed(self):
        self.assertEqual(c.validate_base_url('http://127.0.0.1:1234/v1/'), 'http://127.0.0.1:1234/v1')
    def test_secret_redaction_recursive(self):
        self.assertEqual(c.redact({'x':['Bearer topsecret']}, 'topsecret'), {'x':['Bearer [REDACTED]']})
    def test_config_rejects_embedded_key(self):
        cfg=c.default_config();cfg.update(base_url='https://example.com/v1',model='test',api_key='abc')
        with self.assertRaises(ValueError): c.validate_config(cfg)
    def test_config_rejects_token_parameter_override(self):
        cfg=c.default_config();cfg.update(base_url='https://example.com/v1',model='test',extra_body={'max_tokens':9})
        with self.assertRaises(ValueError): c.validate_config(cfg)
    def test_missing_prices_not_zero(self):
        self.assertIsNone(c.estimate_cost({'prompt_tokens':10,'completion_tokens':10},c.default_config()['prices']))
    def test_pricing_cached_tokens(self):
        p={'currency':'USD','input_per_million':2.,'output_per_million':4.,'cached_input_per_million':1.}
        self.assertAlmostEqual(c.estimate_cost({'prompt_tokens':1000,'completion_tokens':100,'prompt_tokens_details':{'cached_tokens':500}},p),.0019)
    def test_request_omits_unspecified_temperature(self):
        cfg=c.default_config();cfg.update(model='test')
        req=c.request_payload(cfg,[{'role':'user','content':'hello'}])
        self.assertNotIn('temperature',req);self.assertEqual(req['max_tokens'],1024)
    def test_max_completion_tokens(self):
        cfg=c.default_config();cfg.update(model='test',max_tokens_field='max_completion_tokens')
        req=c.request_payload(cfg,[{'role':'user','content':'hello'}]);self.assertNotIn('max_tokens',req)
    def test_empty_content_preserved(self):
        body={'choices':[{'message':{'content':None},'finish_reason':'length'}]}
        self.assertEqual(c.response_text(body),'')
    def test_chat_response(self):
        self.assertEqual(c.response_text({'choices':[{'message':{'content':'{"ok":true}'}}]}),'{"ok":true}')
    def test_lock_prevents_concurrent_run(self):
        with tempfile.TemporaryDirectory() as d:
            with c.run_lock(d):
                with self.assertRaises(ValueError):
                    with c.run_lock(d):pass
            self.assertFalse((Path(d)/'.run.lock').exists())
