
"""R9 journal with explicit pause gates. Remote calls only from user CLI.
A send-intent event is a local observation, never proof of remote receipt.
"""
from pathlib import Path
import json,time,urllib.request,urllib.error
from pilot.common import (canonical,digest,read_json,write_json,utcnow,redact,request_payload,
                          response_text,strict_json_object,validate_config)
from pilot.client import RunStopped,NoRedirect
from .accounting import normalize_usage
from .prompts import strict_object
from .identity import response_identity

def validate_config_profile(c):
    from urllib.parse import urlsplit
    d=dict(c)
    from pilot.common import default_config
    if set(d)!=set(default_config()):raise ValueError("Missing or unknown config keys; secrets must not be in config")
    for k in ("timeout_seconds","min_interval_seconds"):
        if type(d[k]) not in (int,float) or d[k]<0:raise ValueError("Invalid timing")
    required={"base_url":"https://api.deepseek.com/v1","model":"deepseek-v4-flash",
      "max_tokens_field":"max_tokens","max_output_tokens":16384,"instruction_role":"system",
      "temperature":None,"max_requests":360,
      "extra_body":{"thinking":{"type":"enabled"},"reasoning_effort":"high"}}
    for k,v in required.items():
        if d.get("backend_kind")=="test_fixture" and k in ("base_url","model"):continue
        if d.get(k)!=v:raise ValueError("Frozen request field changed: "+k)
    if d.get("backend_kind")=="test_fixture":
        if urlsplit(d["base_url"]).hostname not in ("localhost","127.0.0.1","::1"):
            raise ValueError("Fixtures may only use loopback")
    elif d.get("backend_kind")!="live":raise ValueError("Unknown backend kind")
    if d.get("max_estimated_spend") is not None:raise ValueError("No invoice guarantee")
    if d.get("key_env")!="LLM_API_KEY":raise ValueError("Fixed key env")
    if d.get("local_no_auth") is not False:raise ValueError("Live requests require explicit credentials")
    if any(v is not None for k,v in d["prices"].items() if k!="currency"):raise ValueError("Prices unknown; no stale rate reuse")
    return d

def write_once(path,obj):
    path=Path(path)
    if path.exists():
        if read_json(path)!=obj:raise RunStopped("Existing immutable artifact differs: "+path.name)
    else:write_json(path,obj)

class Client:
    def __init__(self,cfg,run_dir,secret="",cap=360):
        self.cfg=cfg;self.root=Path(run_dir);self.secret=secret;self.cap=cap
        self.calls=self.root/"calls";self.attempts=self.root/"attempts"
        self.calls.mkdir(parents=True,exist_ok=True);self.attempts.mkdir(parents=True,exist_ok=True)
        self.opener=urllib.request.build_opener(NoRedirect());self.last_end=0.
    def starts(self):
        return [read_json(x) for x in sorted(self.attempts.glob("*_start.json"))]
    def budget(self):
        starts=self.starts();results=list(self.attempts.glob("*_result.json"))
        return {"attempts":len(starts),"response_records":len(results),
                "uncertain_attempts":sum(not (self.attempts/f"{x['attempt']:06d}_result.json").exists() for x in starts),
                "model_call_cap":self.cap,"actual_billing":"unknown; not inferred from local start events"}
    def _validate_saved(self,r):
        if r.get("status")!="ok":raise RunStopped("Recorded transport/protocol failure. No automatic retry; export for review.")
        body=r["response"]
        identity=response_identity(self.cfg,body)
        ip=self.root/"endpoint_identity.json"
        if ip.exists():
            old=read_json(ip)
            if old!=identity:
                raise RunStopped("Endpoint identity metadata changed inside run. Export for review.")
        else:write_json(ip,identity)
        finish=body["choices"][0].get("finish_reason")
        if finish!="stop":raise RunStopped("Completion ended with "+str(finish)+". Response preserved, no resampling.")
        try:strict_object(r["text"])
        except (ValueError,TypeError):raise RunStopped("Invalid JSON response preserved. Paused, not automatically repaired.") from None
        usage=normalize_usage(body.get("usage"))
        if usage["prompt_tokens"] is None or usage["completion_tokens"] is None:
            raise RunStopped("Token usage missing. Raw response retained; review before large run.")
        if usage["issues"]:raise RunStopped("Usage inconsistent. Raw evidence retained; review before continuing.")
        return r
    def complete(self,logical_id,messages,meta=None):
        payload=request_payload(self.cfg,messages);metadata=meta or {}
        fp=digest({"endpoint":self.cfg["base_url"],"payload":payload});path=self.calls/(digest(logical_id)+".json")
        if self.secret and self.secret in canonical(payload):raise RunStopped("Credential detected inside model payload; no call sent.")
        if path.exists():
            r=read_json(path)
            if r["request_sha256"]!=fp or r.get("metadata",{})!=metadata:raise RunStopped("Logical ID input changed; refusing resume.")
            return self._validate_saved(r)
        starts=self.starts()
        for st in starts:
            if st["logical_id"]!=logical_id:continue
            if st["request_sha256"]!=fp:raise RunStopped("Previous attempt input changed.")
            result=self.attempts/f"{st['attempt']:06d}_result.json"
            if not result.exists():raise RunStopped("Registered attempt has no result; remote receipt/billing unknown. Export; do not retry.")
            r=read_json(result)
            if r.get("status")=="ok":write_json(path,r);return self._validate_saved(r)
            raise RunStopped("Previous request error retained. No retries are authorised in R9.")
        if len(starts)>=self.cap:raise RunStopped("Hard request-count limit reached; no new request.")
        idx=len(starts)+1
        st={"attempt":idx,"logical_id":logical_id,"request_sha256":fp,"started_utc":utcnow(),
            "payload":payload,"payload_sha256":digest(payload),"metadata":metadata,"registration_is_not_remote_receipt":True}
        write_once(self.attempts/f"{idx:06d}_start.json",redact(st,self.secret))
        gap=self.cfg["min_interval_seconds"]-(time.monotonic()-self.last_end)
        if gap>0:time.sleep(gap)
        headers={"Content-Type":"application/json","Accept":"application/json"}
        if self.secret:headers["Authorization"]="Bearer "+self.secret
        req=urllib.request.Request(self.cfg["base_url"]+"/chat/completions",data=canonical(payload).encode(),
                                   headers=headers,method="POST")
        write_once(self.attempts/f"{idx:06d}_send_intent.json",{"attempt":idx,"logical_id":logical_id,
          "local_send_intent_utc":utcnow(),"proves_remote_receipt":False})
        tic=time.perf_counter();raw=None;body=None
        try:
            with self.opener.open(req,timeout=self.cfg["timeout_seconds"]) as resp:
                raw=resp.read(8_000_001)
                if len(raw)>8_000_000:raise ValueError("Response exceeds 8MB")
                body=json.loads(raw.decode("utf-8"));text=response_text(body)
            r={**st,"status":"ok","ended_utc":utcnow(),"latency_seconds":time.perf_counter()-tic,
               "response":body,"text":text,"estimated_cost":None}
        except Exception as exc:
            detail=str(exc)
            if isinstance(exc,urllib.error.HTTPError):
                try:detail+=" | "+exc.read(4096).decode("utf-8","replace")
                except Exception:pass
            r={**st,"status":"request_error","ended_utc":utcnow(),"latency_seconds":time.perf_counter()-tic,
               "error_type":type(exc).__name__,"error":detail,"estimated_cost":None,"billing_unknown":True,
               "response":body,"raw_response_text":raw.decode("utf8","replace") if raw else None}
            write_once(self.attempts/f"{idx:06d}_result.json",redact(r,self.secret))
            raise RunStopped("Request failed; evidence preserved; no automatic retry. "+redact(detail,self.secret)) from None
        finally:self.last_end=time.monotonic()
        r=redact(r,self.secret)
        write_once(self.attempts/f"{idx:06d}_result.json",r);write_once(path,r)
        print(f"[R9 {idx}/{self.cap}] {logical_id} | {r['latency_seconds']:.2f}s | finish={body['choices'][0].get('finish_reason')}",flush=True)
        return self._validate_saved(r)
