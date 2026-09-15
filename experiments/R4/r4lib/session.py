
"""R4 journal with explicit pause gates. Remote calls only from user CLI.
A send-intent event is a local observation, never proof of remote receipt.
"""
from pathlib import Path
import json,time,urllib.request,urllib.error
from pilot.common import (canonical,digest,read_json,write_json,utcnow,redact,request_payload,
                          response_text,strict_json_object,validate_config)
from pilot.client import RunStopped,NoRedirect
from .accounting import normalize_usage

def validate_r4_config(c):
    d=dict(c);extra=dict(d.get("extra_body",{}));thinking=extra.pop("thinking",None)
    d["extra_body"]=extra;d=validate_config(d)
    if thinking is not None:
        if thinking not in ({"type":"enabled"},{"type":"disabled"}):raise ValueError("Invalid thinking toggle")
        d["extra_body"]={**d["extra_body"],"thinking":thinking}
    from urllib.parse import urlsplit
    if d["backend_kind"]=="test_fixture" and urlsplit(d["base_url"]).hostname not in ("localhost","127.0.0.1","::1"):
        raise ValueError("Software fixture label is permitted only on a loopback test server.")
    if d["max_output_tokens"]!=16384:raise ValueError("R4 fixed output cap is 16384. Do not silently change it.")
    if d["max_requests"]!=408:raise ValueError("R4 main cap fixed at 408; smoke is separately capped at one.")
    if d["max_estimated_spend"] is not None:raise ValueError("R4 uses explicit request cap; fee schedules are offline estimates, not hard billing caps.")
    if any(v is not None for k,v in d["prices"].items() if k!="currency"):
        raise ValueError("Do not reuse R1 flat prices. Use scoped billing.local.json for offline estimates.")
    if d["extra_body"] != {"thinking":{"type":"enabled"},"reasoning_effort":"high"}:raise ValueError("Frozen R4 thinking settings changed")
    if d["temperature"] is not None:raise ValueError("R4 omits temperature")
    if d["backend_kind"]=="live" and (d["model"]!="deepseek-flash" or d["base_url"]!="https://api.deepseek.com/v1" or d["max_tokens_field"]!="max_tokens" or d["instruction_role"]!="system"):
        raise ValueError("R4 live model/endpoint/request profile frozen to the previously tested R2 endpoint. Export on incompatibility.")
    return d

def write_once(path,obj):
    path=Path(path)
    if path.exists():
        if read_json(path)!=obj:raise RunStopped("Existing immutable artifact differs: "+path.name)
    else:write_json(path,obj)

class Client:
    def __init__(self,cfg,run_dir,secret="",cap=408):
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
        if self.cfg["backend_kind"]=="live" and body.get("model")!=self.cfg["model"]:
            raise RunStopped("Returned model differs from requested exact ID. Raw response retained; no fallback.")
        identity={"returned_model":body.get("model"),"system_fingerprint":body.get("system_fingerprint")}
        ip=self.root/"endpoint_identity.json"
        if ip.exists():
            old=read_json(ip)
            if old["returned_model"]!=identity["returned_model"] or old["system_fingerprint"]!=identity["system_fingerprint"]:
                raise RunStopped("Endpoint identity metadata changed inside run. Export for review.")
        else:write_json(ip,identity)
        finish=body["choices"][0].get("finish_reason")
        if finish!="stop":raise RunStopped("Completion ended with "+str(finish)+". Response preserved, no resampling.")
        try:strict_json_object(r["text"])
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
            raise RunStopped("Previous request error retained. No retries are authorised in R4.")
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
        tic=time.perf_counter()
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
               "error_type":type(exc).__name__,"error":detail,"estimated_cost":None,"billing_unknown":True}
            write_once(self.attempts/f"{idx:06d}_result.json",redact(r,self.secret))
            raise RunStopped("Request failed; evidence preserved; no automatic retry. "+redact(detail,self.secret)) from None
        finally:self.last_end=time.monotonic()
        r=redact(r,self.secret)
        write_once(self.attempts/f"{idx:06d}_result.json",r);write_once(path,r)
        print(f"[R4 {idx}/{self.cap}] {logical_id} | {r['latency_seconds']:.2f}s | finish={body['choices'][0].get('finish_reason')}",flush=True)
        return self._validate_saved(r)
