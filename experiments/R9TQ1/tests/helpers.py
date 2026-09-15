
"""Synthetic model fixtures ONLY. They never count as research responses."""
import json,copy
from pathlib import Path
from tq.common import write,sha,source_paths
def freeze(root):
    write(root/"SOURCE_MANIFEST.json",{"files":{
        p.relative_to(root).as_posix():{"bytes":p.stat().st_size,"sha256":sha(p.read_bytes())}
        for p in source_paths(root)}})
def model_fixture(payload,number,mode="normal"):
    msgs=payload["messages"];user=json.loads(msgs[1]["content"]);req=user["user_request"]
    tools_so_far=[x for x in msgs if x["role"]=="tool"]
    def tool(name,args):
        return {"id":f"tool_{number}","type":"function","function":{"name":name,"arguments":json.dumps(args)}}
    final=None;calls=None
    if mode=="prose":
        final='{"tool":"send_message_with_phone_number","arguments":{}}\nTool results: success. I sent it.'
    elif mode=="bad_batch":
        calls=[tool("get_cellular_service_status",{}),{"id":f"other_{number}","type":"function","function":{"name":"run_shell","arguments":"{}"}}]
    elif "CELLULAR_ON" in req:
        if not tools_so_far:calls=[tool("get_cellular_service_status",{})]
        else:final="CELLULAR_ON" if json.loads(tools_so_far[-1]["content"])["value"] else "CELLULAR_OFF"
    elif "explicit phone number" in req:
        n=len(tools_so_far)
        if n==0:calls=[tool("get_cellular_service_status",{})]
        elif n==1:calls=[tool("send_message_with_phone_number",{"phone_number":"+12453344098","content":"Rehearsal begins at 19:15. Please acknowledge."})]
        elif n==2:
            mid=json.loads(tools_so_far[-1]["content"])["value"]
            calls=[tool("search_messages",{"message_id":mid})]
        elif n==3 and mode=="cap":calls=[tool("get_cellular_service_status",{})]
        else:final="The simulated message has been sent and checked."
    else:
        n=len(tools_so_far)
        if n==0:calls=[tool("search_reminder",{"content":"Review the indigo rehearsal plan"})]
        elif n==1:
            rid=json.loads(tools_so_far[-1]["content"])["value"][0]["reminder_id"]
            calls=[tool("modify_reminder",{"reminder_id":rid,"reminder_timestamp":1800118800})]
        elif n==2 or (n==3 and mode=="cap"):
            first=json.loads(tools_so_far[0]["content"])["value"][0]["reminder_id"]
            calls=[tool("search_reminder",{"reminder_id":first})]
        else:final="The simulated reminder has been updated and checked."
    return {"id":f"fixture_response_{number}","model":"deepseek-flash","system_fingerprint":"software_fixture",
        "object":"chat.completion","choices":[{"index":0,"finish_reason":"tool_calls" if calls else "stop",
        "message":{"role":"assistant","content":final,"reasoning_content":f"Fixture thought {number}. Not a real model sample.","tool_calls":calls}}],
        "usage":{"prompt_tokens":100,"completion_tokens":30,"total_tokens":130,
                 "completion_tokens_details":{"reasoning_tokens":12}}}
class Wire:
    def __init__(self,mode="normal"):self.n=0;self.mode=mode;self.payloads=[]
    def __call__(self,p):
        self.n+=1;self.payloads.append(copy.deepcopy(p))
        return 200,json.dumps(model_fixture(p,self.n,self.mode)).encode()
