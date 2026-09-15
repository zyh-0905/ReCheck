
"""Native Chat Completions contract; assistant prose NEVER authorizes tools."""
import copy,json,math
class ContractError(ValueError): pass

def canonical(obj):
    return json.dumps(obj,ensure_ascii=False,sort_keys=True,separators=(",",":"),allow_nan=False)
def strict_json(text):
    def pairs(items):
        out={}
        for k,v in items:
            if k in out:raise ContractError("Duplicate JSON key")
            out[k]=v
        return out
    def bad(v):raise ContractError("Non-finite JSON constant")
    try:obj=json.loads(text,object_pairs_hook=pairs,parse_constant=bad)
    except (ValueError,TypeError) as e:raise ContractError("Malformed JSON document") from e
    def finite(v):
        if type(v) is float and not math.isfinite(v):raise ContractError("Non-finite number")
        if isinstance(v,dict):
            for x in v.values():finite(x)
        if isinstance(v,list):
            for x in v:finite(x)
    finite(obj);return obj

def schema_check(value,schema,path="$"):
    if "anyOf" in schema:
        for s in schema["anyOf"]:
            try:schema_check(value,s,path);return
            except ContractError:pass
        raise ContractError("Value does not match schema at "+path)
    t=schema.get("type")
    good={"object":type(value) is dict,"string":type(value) is str,
          "number":type(value) in (int,float) and math.isfinite(value),
          "integer":type(value) is int,"boolean":type(value) is bool,"null":value is None,
          "array":type(value) is list}.get(t,False)
    if not good:raise ContractError("Wrong schema type at "+path)
    if t=="object":
        props=schema.get("properties",{})
        if any(k not in value for k in schema.get("required",[])):raise ContractError("Required field missing at "+path)
        if schema.get("additionalProperties") is False and set(value)-set(props):raise ContractError("Unknown field at "+path)
        for k,v in value.items():
            if k in props:schema_check(v,props[k],path+"."+k)
    if t=="array":
        for i,v in enumerate(value):schema_check(v,schema["items"],path+f"[{i}]")
    if "enum" in schema and value not in schema["enum"]:raise ContractError("Invalid enum at "+path)

def usage_counts(u):
    if type(u) is not dict:raise ContractError("Missing usage")
    def count(k,v):
        if type(v) is not int or v<0:raise ContractError("Invalid token count: "+k)
        return v
    ni=count("prompt_tokens",u.get("prompt_tokens"));no=count("completion_tokens",u.get("completion_tokens"))
    nt=count("total_tokens",u.get("total_tokens"))
    if nt!=ni+no:raise ContractError("Inconsistent total_tokens")
    reason=u.get("completion_tokens_details",{})
    if reason is None:reason={}
    if type(reason) is not dict:raise ContractError("Malformed completion details")
    nr=reason.get("reasoning_tokens")
    if nr is not None and count("reasoning",nr)>no:raise ContractError("Reasoning exceeds output")
    details=u.get("prompt_tokens_details") or {}
    if type(details) is not dict:raise ContractError("Malformed prompt details")
    cache=u.get("prompt_cache_hit_tokens",details.get("cached_tokens"))
    if cache is not None:
        if count("cache",cache)>ni:raise ContractError("Cache exceeds input")
        if "cached_tokens" in details and count("cached",details["cached_tokens"])!=cache:raise ContractError("Cache mismatch")
    miss=u.get("prompt_cache_miss_tokens")
    if miss is not None:
        count("cache_miss",miss)
        if cache is not None and miss+cache!=ni:raise ContractError("Cache sum mismatch")
    return {"prompt_tokens":ni,"completion_tokens":no,"total_tokens":nt,
            "reasoning_tokens":nr,"cached_input_tokens":cache}

def validate_response(body,tools,used_ids=(),expected_identity=None):
    if type(body) is not dict:raise ContractError("Response must be object")
    if not isinstance(body.get("id"),str) or not body["id"]:raise ContractError("Missing response ID")
    returned=body.get("model");fp=body.get("system_fingerprint")
    if returned not in ("deepseek-flash","deepseek-v4-flash"):raise ContractError("Unexpected response model label")
    if type(fp) is not str or not fp.strip():raise ContractError("Missing fingerprint")
    identity={"requested_model":"deepseek-flash","returned_model":returned,"system_fingerprint":fp,"weight_identity_verified":False}
    if expected_identity is not None and identity!=expected_identity:raise ContractError("Response metadata changed")
    usage=usage_counts(body.get("usage"))
    choices=body.get("choices")
    if type(choices) is not list or len(choices)!=1:raise ContractError("Expected exactly one choice")
    ch=choices[0]
    if type(ch) is not dict or ch.get("index")!=0:raise ContractError("Unexpected choice")
    m=ch.get("message")
    if type(m) is not dict or m.get("role")!="assistant":raise ContractError("Missing assistant message")
    if "content" not in m or (m["content"] is not None and type(m["content"]) is not str):raise ContractError("Invalid content")
    if "reasoning_content" not in m or (m["reasoning_content"] is not None and type(m["reasoning_content"]) is not str):
        raise ContractError("Missing or malformed reasoning_content; cannot preserve native tool history")
    calls=m.get("tool_calls")
    finish=ch.get("finish_reason")
    # Copy only documented message fields; the response itself is kept intact in the journal.
    msg={k:copy.deepcopy(m[k]) for k in ("role","content","reasoning_content","tool_calls") if k in m}
    if calls is None or calls==[]:
        if finish!="stop":raise ContractError("Unexpected non-tool finish_reason: "+str(finish))
        if type(m["content"]) is not str or not m["content"].strip():raise ContractError("Empty final content")
        return {"kind":"final","message":msg,"calls":[],"identity":identity,"usage":usage}
    if finish!="tool_calls":raise ContractError("tool_calls and finish_reason disagree")
    if type(calls) is not list or not 1<=len(calls)<=4:raise ContractError("Tool batch outside 1..4 limit")
    mapping={x["function"]["name"]:x["function"]["parameters"] for x in tools}
    seen=set(used_ids);decoded=[]
    for c in calls:
        if type(c) is not dict or c.get("type")!="function":raise ContractError("Unsupported tool-call type")
        ident=c.get("id")
        if type(ident) is not str or not ident or len(ident)>256 or ident in seen:raise ContractError("Missing/duplicate tool call ID")
        seen.add(ident)
        f=c.get("function")
        if type(f) is not dict or f.get("name") not in mapping:raise ContractError("Unknown tool name")
        if type(f.get("arguments")) is not str or len(f["arguments"])>12000:raise ContractError("Invalid argument string")
        a=strict_json(f["arguments"]);schema_check(a,mapping[f["name"]])
        decoded.append({"id":ident,"name":f["name"],"arguments":a})
    return {"kind":"tools","message":msg,"calls":decoded,"identity":identity,"usage":usage}

def tool_reply(call_id,result):
    return {"role":"tool","tool_call_id":call_id,"content":canonical(result)}

def validate_history(messages):
    if type(messages) is not list or not messages:raise ContractError("Missing history")
    pending=[];seen=set()
    for m in messages:
        if type(m) is not dict:raise ContractError("Invalid message")
        r=m.get("role")
        if pending and r!="tool":raise ContractError("Missing real tool reply before next message")
        if r=="tool":
            if not pending or m.get("tool_call_id")!=pending[0]:raise ContractError("Orphan or reordered tool result ID")
            if type(m.get("content")) is not str:raise ContractError("Tool result must be serialized real result")
            pending.pop(0)
        elif r=="assistant":
            if "reasoning_content" not in m:raise ContractError("Reasoning history missing")
            for c in m.get("tool_calls") or []:
                if c["id"] in seen:raise ContractError("Tool ID reused")
                seen.add(c["id"]);pending.append(c["id"])
        elif r not in ("system","user"):raise ContractError("Unexpected role")
    if pending:raise ContractError("Outstanding tool calls lack results")

def build_payload(config,messages,tools):
    validate_history(messages)
    if config.get("model")!="deepseek-flash":raise ContractError("Frozen request model changed")
    return {"model":config["model"],"messages":copy.deepcopy(messages),"tools":copy.deepcopy(tools),
            "tool_choice":"auto","stream":False,"max_tokens":16384,
            "thinking":{"type":"enabled"},"reasoning_effort":"high"}
