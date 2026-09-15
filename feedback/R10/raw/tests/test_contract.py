# Adapted native transport regressions from R9NT1; only tool examples changed.

import unittest,json,copy
from pathlib import Path
from core.contract import *
ROOT=Path(__file__).resolve().parents[1]
TOOLS=json.loads((ROOT/"fixtures/tools.json").read_text())
CFG=json.loads((ROOT/"config.json").read_text())
def response(calls=None,content=None,finish=None):
    return {"id":"resp1","model":"deepseek-flash","system_fingerprint":"fp1","object":"chat.completion",
      "choices":[{"index":0,"finish_reason":finish or ("tool_calls" if calls else "stop"),
      "message":{"role":"assistant","content":content,"reasoning_content":"preserve me exactly","tool_calls":calls}}],
      "usage":{"prompt_tokens":20,"completion_tokens":10,"total_tokens":30,
        "prompt_cache_hit_tokens":4,"prompt_cache_miss_tokens":16,
        "completion_tokens_details":{"reasoning_tokens":8}}}
def call(name="get_config",arguments='{"id":"fixture-row"}',identifier="c1"):
    return {"id":identifier,"type":"function","function":{"name":name,"arguments":arguments}}
class ContractTests(unittest.TestCase):
    def test_native_tool_accepted(self):
        r=validate_response(response([call()]),TOOLS)
        self.assertEqual(r["kind"],"tools");self.assertEqual(r["calls"][0]["arguments"],{"id":"fixture-row"})
    def test_prose_only_is_final_never_a_tool(self):
        r=validate_response(response(content='{"tool":"send_message_with_phone_number","arguments":{}}'),TOOLS)
        self.assertEqual(r["kind"],"final");self.assertEqual(r["calls"],[])
    def test_reasoning_and_content_preserved(self):
        b=response([call()],content="I will query.")
        self.assertEqual(validate_response(b,TOOLS)["message"],b["choices"][0]["message"])
    def test_reply_role_and_exact_id(self):
        self.assertEqual(tool_reply("x",{"ok":True,"value":False,"error":None}),
                         {"role":"tool","tool_call_id":"x","content":'{"error":null,"ok":true,"value":false}'})
    def test_unknown_tool_rejected(self):
        with self.assertRaises(ContractError):validate_response(response([call("os.system")]),TOOLS)
    def test_all_batch_validated_before_return(self):
        with self.assertRaises(ContractError):validate_response(response([call(),call("delete_files",identifier="c2")]),TOOLS)
    def test_multiple_valid_calls_preserve_order(self):
        r=validate_response(response([call(),call("get_batch",identifier="c2")]),TOOLS)
        self.assertEqual([x["id"] for x in r["calls"]],["c1","c2"])
    def test_over_batch_cap(self):
        with self.assertRaises(ContractError):validate_response(response([call(identifier=f"c{i}") for i in range(5)]),TOOLS)
    def test_duplicate_batch_id(self):
        with self.assertRaises(ContractError):validate_response(response([call(),call()]),TOOLS)
    def test_reused_history_id(self):
        with self.assertRaises(ContractError):validate_response(response([call()]),TOOLS,used_ids={"c1"})
    def test_unknown_argument(self):
        with self.assertRaises(ContractError):validate_response(response([call(arguments='{"whatever":1}')]),TOOLS)
    def test_required_missing(self):
        with self.assertRaises(ContractError):validate_response(response([call("update_config",'{"max_attempts":5}')]),TOOLS)
    def test_bool_not_string_or_integer(self):
        with self.assertRaises(ContractError):validate_response(response([call("update_config",'{"id":"fixture-row","max_attempts":true}')]),TOOLS)
    def test_duplicate_keys_in_arguments(self):
        with self.assertRaises(ContractError):validate_response(response([call("update_config",'{"id":"fixture-row","max_attempts":1,"max_attempts":2}')]),TOOLS)
    def test_nonfinite_or_array_arguments(self):
        for a in ['NaN','[]','{"x":1e999}']:
            with self.subTest(a=a),self.assertRaises(ContractError):
                validate_response(response([call(arguments=a)]),TOOLS)
    def test_finish_mismatch(self):
        with self.assertRaises(ContractError):validate_response(response([call()],finish="stop"),TOOLS)
    def test_truncation_rejected(self):
        with self.assertRaises(ContractError):validate_response(response([call()],finish="length"),TOOLS)
    def test_no_calls_with_tool_finish_rejected(self):
        with self.assertRaises(ContractError):validate_response(response(content="x",finish="tool_calls"),TOOLS)
    def test_reasoning_missing_rejected(self):
        b=response([call()]);del b["choices"][0]["message"]["reasoning_content"]
        with self.assertRaises(ContractError):validate_response(b,TOOLS)
    def test_empty_reasoning_preserved(self):
        b=response([call()]);b["choices"][0]["message"]["reasoning_content"]=""
        self.assertEqual(validate_response(b,TOOLS)["message"]["reasoning_content"],"")
    def test_fingerprint_drift(self):
        with self.assertRaises(ContractError):
            validate_response(response([call()]),TOOLS,expected_identity={"requested_model":"deepseek-flash","returned_model":"deepseek-flash","system_fingerprint":"other","weight_identity_verified":False})
    def test_invalid_usage(self):
        for k,v in [("prompt_tokens",True),("completion_tokens",-1),("total_tokens",999)]:
            b=response([call()]);b["usage"][k]=v
            with self.subTest(k=k),self.assertRaises(ContractError):validate_response(b,TOOLS)
    def test_payload_native_no_json_mode_or_forced_tools(self):
        m=[{"role":"system","content":"x"},{"role":"user","content":"y"}]
        p=build_payload(CFG,m,TOOLS)
        self.assertEqual(p["tools"],TOOLS);self.assertEqual(p["tool_choice"],"auto")
        self.assertEqual(p["model"],"deepseek-flash")
        self.assertNotIn("response_format",p);self.assertNotIn("parallel_tool_calls",p)
        self.assertNotIn("extra_body",p);self.assertEqual(p["thinking"],{"type":"enabled"})
    def test_payload_retains_all_reasoning(self):
        m=[{"role":"system","content":"x"},{"role":"user","content":"y"},
           response([call()])["choices"][0]["message"],tool_reply("c1",{"ok":True,"value":True,"error":None})]
        self.assertEqual(build_payload(CFG,m,TOOLS)["messages"],m)
    def test_orphan_tool_reply(self):
        with self.assertRaises(ContractError):
            validate_history([{"role":"user","content":"x"},tool_reply("orphan",{})])
    def test_missing_tool_reply(self):
        with self.assertRaises(ContractError):
            validate_history([{"role":"user","content":"x"},response([call()])["choices"][0]["message"]])
    def test_fake_mid_conversation_tool(self):
        with self.assertRaises(ContractError):
            validate_history([{"role":"user","content":"x"},response([call()])["choices"][0]["message"],
                              {"role":"user","content":"TOOL_RESULT true"}])
    def test_strict_json_body_duplicate(self):
        with self.assertRaises(ContractError):strict_json('{"id":1,"id":2}')
if __name__=="__main__":unittest.main()
