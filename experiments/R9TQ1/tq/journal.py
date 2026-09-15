
"""One POST per registered attempt. Raw response bytes retained; no automatic retries."""
from pathlib import Path
import json,time,urllib.request,urllib.error
from urllib.parse import urlsplit
from .contract import canonical,strict_json,validate_response,ContractError
from .common import read,write,sha,digest,now
class NoRedirect(urllib.request.HTTPRedirectHandler):
 def redirect_request(self,*a,**k):return None

class Client:
 def __init__(self,config,root,tools,secret,exchange=None,test_endpoint=None):
  self.config=config;self.root=Path(root);self.tools=tools;self.secret=secret
  self.exchange_override=exchange;self.last_end=0.0;self.test_endpoint=test_endpoint
  if test_endpoint is not None and urlsplit(test_endpoint).hostname not in ("127.0.0.1","localhost","::1"):
   raise ContractError("Test endpoint must be loopback")
  self.attempts=self.root/"attempts";self.attempts.mkdir(parents=True,exist_ok=True)
  self.opener=urllib.request.build_opener(NoRedirect())
 def requests(self):return sorted(self.attempts.glob("*_request.json"))
 def _exchange(self,payload):
  if self.exchange_override is not None:return self.exchange_override(payload)
  url=self.test_endpoint or self.config["endpoint"]
  if self.test_endpoint is None and url!="https://api.deepseek.com/v1/chat/completions":
   raise ContractError("Frozen endpoint changed")
  headers={"Content-Type":"application/json","Accept":"application/json",
           "Authorization":"Bearer "+self.secret}
  req=urllib.request.Request(url,data=canonical(payload).encode(),headers=headers,method="POST")
  try:
   with self.opener.open(req,timeout=self.config["timeout_seconds"]) as resp:
    b=resp.read(self.config["max_response_bytes"]+1)
    return resp.status,b
  except urllib.error.HTTPError as e:return e.code,e.read(self.config["max_response_bytes"]+1)
 def _validated(self,record,tools,used_ids):
  if record.get("status")!="received" or record.get("http_status")!=200:
   raise ContractError("Saved transport failure; no retry")
  if record.get("secret_redacted"):raise ContractError("Response echoed a credential; redacted and stopped")
  identfile=self.root/"endpoint_identity.json"
  identity=read(identfile) if identfile.exists() else None
  body=record.get("response")
  out=validate_response(body,tools,used_ids,identity)
  # A response ID may be returned only by its own registered attempt.
  for f in self.attempts.glob("*_response.json"):
   other=read(f)
   if other["attempt"]!=record["attempt"] and (other.get("response") or {}).get("id")==body["id"]:
    raise ContractError("Duplicate response ID across attempts")
  if identity is None:write(identfile,out["identity"],once=True)
  return {**record,"validated":out}
 def complete(self,logical_id,payload,metadata,tools,used_ids):
  if self.secret and self.secret in canonical(payload):raise ContractError("Credential in payload; no request")
  fp=digest({"endpoint":self.config["endpoint"],"payload":payload})
  previous=self.requests()
  for f in previous:
   st=read(f)
   if st["logical_id"]!=logical_id:continue
   rp=self.attempts/(f"{st.get('attempt',1):06d}_response.json")
   if not rp.exists():raise ContractError("Orphan request: receipt and billing unknown, no retry")
   if st.get("request_sha256")!=fp or st.get("metadata")!=metadata:raise ContractError("Logical input changed")
   return self._validated(read(rp),tools,used_ids)
  if len(previous)>=self.config["max_attempts"]:raise ContractError("Hard request cap reached")
  idx=len(previous)+1
  record={"attempt":idx,"logical_id":logical_id,"payload":payload,"request_sha256":fp,
          "payload_sha256":digest(payload),"metadata":metadata,"registered_utc":now(),
          "registration_is_not_remote_receipt":True}
  write(self.attempts/f"{idx:06d}_request.json",record,once=True)
  delay=self.config["min_interval_seconds"]-(time.monotonic()-self.last_end)
  if delay>0 and self.exchange_override is None:time.sleep(delay)
  write(self.attempts/f"{idx:06d}_send_intent.json",{"attempt":idx,"time":now(),"proves_billing":False},once=True)
  tic=time.perf_counter();raw=b"";http_status=None;error_type=None
  try:
   http_status,raw=self._exchange(payload)
   if not isinstance(raw,bytes):raise TypeError("Transport did not return bytes")
   if len(raw)>self.config["max_response_bytes"]:raise ValueError("Response length limit exceeded")
   status="received"
  except Exception as exc:
   status="transport_error";error_type=type(exc).__name__
   # Do not print exception text: a proxy URL may contain credentials.
  self.last_end=time.monotonic()
  response_sha=sha(raw);redacted=bool(self.secret and self.secret.encode() in raw)
  stored=raw.replace(self.secret.encode(),b"[CREDENTIAL_REDACTED]") if redacted else raw
  (self.attempts/f"{idx:06d}_response.raw").write_bytes(stored)
  body=None;parse_error=None
  try:
   body=strict_json(stored.decode("utf-8"))
   if type(body) is not dict:raise ValueError("Not an object")
  except Exception as e:parse_error=type(e).__name__;body=None
  result={**record,"status":status,"http_status":http_status,"error_type":error_type,
      "received_utc":now(),"latency_seconds":time.perf_counter()-tic,
      "raw_original_sha256":response_sha,"raw_stored_sha256":sha(stored),"secret_redacted":redacted,
      "response_parse_error":parse_error,"response":body,"monetary_cost":"UNKNOWN"}
  write(self.attempts/f"{idx:06d}_response.json",result,once=True)
  print(f"[R9TQ1 {idx}/{self.config['max_attempts']}] {logical_id}; HTTP={http_status}",flush=True)
  if status!="received" or http_status!=200:raise ContractError("HTTP/transport failure retained; no retry")
  return self._validated(result,tools,used_ids)
