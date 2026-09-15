"""Persistent non-streaming Chat Completions client. Calls occur only on user run.

No prompt/answer repair, silent model fallback, or cross-condition response cache.
A completed response is replayed only at its original logical call ID on resume.
"""
from __future__ import annotations
import json, time, urllib.request, urllib.error
from pathlib import Path
from .common import canonical,digest,write_json,read_json,utcnow,redact,request_payload,response_text,estimate_cost

class RunStopped(RuntimeError): pass
class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,req,fp,code,msg,headers,newurl): return None

class JournalClient:
    def __init__(self,cfg,run_dir,secret='',retry_failed=False,retry_uncertain=False):
        self.cfg=cfg;self.root=Path(run_dir);self.secret=secret
        self.retry_failed=retry_failed;self.retry_uncertain=retry_uncertain
        self.calls=self.root/'calls';self.attempts=self.root/'attempts'
        self.calls.mkdir(parents=True,exist_ok=True);self.attempts.mkdir(parents=True,exist_ok=True)
        self.opener=urllib.request.build_opener(NoRedirect())
        self.last_end=0.

    def _attempt_records(self):
        return [read_json(p) for p in sorted(self.attempts.glob('*_start.json'))]

    def budget(self):
        starts=self._attempt_records();known=0.;reserve=0.;unknown=0
        for st in starts:
            p=self.attempts/f"{st['attempt']:06d}_result.json"
            res=read_json(p) if p.exists() else {}
            value=res.get('estimated_cost')
            if value is None:reserve+=st.get('reserved_estimated_cost') or 0.;unknown+=1
            else:known+=value
        return {'attempts':len(starts),'known_estimated_spend':known,'unknown_or_unbilled_attempts':unknown,
                'conservative_reserved_spend':reserve,'guard_spend':known+reserve}

    def complete(self,logical_id,messages,meta=None):
        payload=request_payload(self.cfg,messages);fp=digest({'endpoint':self.cfg['base_url'],'payload':payload})
        f=self.calls/(digest(logical_id)+'.json')
        if f.exists():
            old=read_json(f)
            if old['request_sha256']!=fp:raise RunStopped('Completed logical call has different input; refusing to reuse or resample.')
            return old
        starts=self._attempt_records()
        previous=[x for x in starts if x['logical_id']==logical_id]
        for st in previous:
            if st['request_sha256']!=fp:raise RunStopped('Previous attempt input changed; use a new run.')
            outcome=self.attempts/f"{st['attempt']:06d}_result.json"
            if not outcome.exists() and not self.retry_uncertain:
                raise RunStopped('Interrupted request may already have been billed. Inspect logs; explicitly pass --retry-uncertain to issue it again.')
            if outcome.exists():
                res=read_json(outcome)
                if res.get('status')=='ok':write_json(f,res);return res
                if not self.retry_failed:raise RunStopped('A request previously failed. Inspect logs and use --retry-failed-requests only for infrastructure retry.')
        b=self.budget()
        if b['attempts']>=self.cfg['max_requests']:raise RunStopped('Hard request-count cap reached; no request sent.')
        # Intentionally labelled an estimate: bytes+padding is NOT a universal tokenizer bound.
        reserved=estimate_cost({'prompt_tokens':len(canonical(payload).encode())+256,
                               'completion_tokens':self.cfg['max_output_tokens']},self.cfg['prices'])
        limit=self.cfg['max_estimated_spend']
        if limit is not None and b['guard_spend']+(reserved or 0)>limit:
            raise RunStopped('Estimated-spend guard reached; no request sent. Provider billing remains authoritative.')
        index=len(starts)+1
        st={'attempt':index,'logical_id':logical_id,'request_sha256':fp,'started_utc':utcnow(),
            'payload':payload,'metadata':meta or {},'reserved_estimated_cost':reserved}
        # Guard accidental inclusion of secret in content before logging or transmission.
        if self.secret and self.secret in canonical(payload):raise RunStopped('Credential appeared inside model payload; stopped.')
        write_json(self.attempts/f'{index:06d}_start.json',redact(st,self.secret))
        gap=self.cfg['min_interval_seconds']-(time.monotonic()-self.last_end)
        if gap>0:time.sleep(gap)
        headers={'Content-Type':'application/json','Accept':'application/json'}
        if self.secret:headers['Authorization']='Bearer '+self.secret
        request=urllib.request.Request(self.cfg['base_url']+'/chat/completions',
                    data=canonical(payload).encode(),headers=headers,method='POST')
        tic=time.perf_counter()
        try:
            with self.opener.open(request,timeout=self.cfg['timeout_seconds']) as response:
                raw=response.read(8_000_001)
                if len(raw)>8_000_000:raise ValueError('Response exceeds 8 MB limit')
                body=json.loads(raw.decode('utf-8'))
                text=response_text(body)
                record={**st,'status':'ok','ended_utc':utcnow(),'latency_seconds':time.perf_counter()-tic,
                        'response':body,'text':text,'estimated_cost':estimate_cost(body.get('usage'),self.cfg['prices'])}
        except Exception as exc:
            # Error bodies can echo secrets. Never export headers; recursively redact body/message.
            detail=str(exc)
            if isinstance(exc,urllib.error.HTTPError):
                try:detail+=' | '+exc.read(4096).decode('utf-8','replace')
                except Exception:pass
            record={**st,'status':'request_error','ended_utc':utcnow(),'latency_seconds':time.perf_counter()-tic,
                    'error_type':type(exc).__name__,'error':detail,'estimated_cost':None,
                    'billing_unknown':True}
            record=redact(record,self.secret);write_json(self.attempts/f'{index:06d}_result.json',record)
            raise RunStopped('API/network/protocol error; run paused and logs saved. '+record['error']) from None
        finally:self.last_end=time.monotonic()
        record=redact(record,self.secret)
        write_json(self.attempts/f'{index:06d}_result.json',record);write_json(f,record)
        print(f"[request {index}/{self.cfg['max_requests']}] {logical_id} | {record['latency_seconds']:.2f}s",flush=True)
        return record
