
"""Raw token accounting and optional user-sourced UTC price schedules.
No live price lookup, currency conversion, or inference that a start record was billed.
"""
from datetime import datetime,timedelta,timezone
import math

def _count(v):
    return isinstance(v,int) and not isinstance(v,bool) and v>=0
def normalize_usage(u):
    u=u if isinstance(u,dict) else {};issues=[]
    def field(k):
        x=u.get(k)
        if x is not None and not _count(x):issues.append("invalid_"+k);return None
        return x
    ni=field("prompt_tokens");no=field("completion_tokens")
    direct=u.get("prompt_cache_hit_tokens");details=u.get("prompt_tokens_details")
    if details is not None and not isinstance(details,dict):issues.append("invalid_prompt_details");details={}
    detail=(details or {}).get("cached_tokens")
    cache=direct if direct is not None else detail
    if direct is not None and detail is not None and direct!=detail:
        issues.append("cache_fields_disagree");cache=None
    if cache is not None and (not _count(cache) or ni is None or cache>ni):issues.append("invalid_cache");cache=None
    miss=u.get("prompt_cache_miss_tokens")
    if miss is not None and (not _count(miss) or (ni is not None and cache is not None and miss+cache!=ni)):issues.append("cache_sum_disagrees")
    details=u.get("completion_tokens_details")
    if details is not None and not isinstance(details,dict):issues.append("invalid_completion_details");details={}
    reason=(details or {}).get("reasoning_tokens")
    if reason is not None and (not _count(reason)):issues.append("invalid_reasoning");reason=None
    if reason is not None and no is not None and reason>no:issues.append("reasoning_exceeds_completion")
    total=u.get("total_tokens")
    if total is not None and ni is not None and no is not None and total!=ni+no:issues.append("total_tokens_disagree")
    return {"prompt_tokens":ni,"completion_tokens":no,"cached_input_tokens":cache,
            "reasoning_tokens":reason,"visible_token_difference":no-reason if no is not None and reason is not None and no>=reason else None,
            "issues":issues}

def stamp(s):
    d=datetime.fromisoformat(s.replace("Z","+00:00"))
    if d.tzinfo is None:raise ValueError("Timestamp needs timezone")
    return d.astimezone(timezone.utc)

def validate_schedule(s):
    if not s.get("enabled",False):return s
    if not s.get("currency") or not s.get("source") or not s.get("model_ids"):raise ValueError("Prices require currency, source and model_ids.")
    start=stamp(s["valid_from_utc"]);end=stamp(s["valid_until_utc"])
    if end<=start:raise ValueError("Invalid price validity interval")
    for name in ("off_peak","peak"):
        for k in ("input_per_million","cached_input_per_million","output_per_million"):
            v=s[name][k]
            if isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) or v<0:raise ValueError("Invalid price")
    for w in s.get("peak_windows_utc",[]):
        for k in ("start","end"):
            hh,mm=map(int,w[k].split(":"))
            if not (0<=hh<=24 and 0<=mm<60) or (hh==24 and mm):raise ValueError("Invalid window")
        if _minute(w["start"])>=_minute(w["end"]):raise ValueError("Split midnight windows into two entries.")
        if any(type(i) is not int or i not in range(7) for i in w["weekdays"]):raise ValueError("Monday=0..Sunday=6")
    return s

def _minute(x):
    h,m=map(int,x.split(":"));return h*60+m
def period(t,s):
    minute=t.hour*60+t.minute+t.second/60+t.microsecond/60000000
    for w in s.get("peak_windows_utc",[]):
        if t.weekday() in w["weekdays"] and _minute(w["start"])<=minute<_minute(w["end"]):return "peak"
    return "off_peak"

def price_call(c,s):
    result={"estimate":None,"currency":s.get("currency","UNKNOWN"),"rate_period":None,
            "reason":"prices_unknown","billing_status":"LIST_PRICE_ESTIMATE_NOT_INVOICE"}
    if not s.get("enabled",False):return result
    validate_schedule(s)
    if c.get("status")!="ok":result["reason"]="response_or_billing_unknown";return result
    if c.get("payload",{}).get("model") not in s["model_ids"]:result["reason"]="model_not_covered";return result
    try:a=stamp(c["started_utc"]);b=stamp(c["ended_utc"])
    except (ValueError,KeyError,TypeError):result["reason"]="time_unknown";return result
    if b<a:result["reason"]="invalid_time_interval";return result
    if (b-a).total_seconds()>86400:result["reason"]="request_interval_too_long";return result
    if a<stamp(s["valid_from_utc"]) or b>=stamp(s["valid_until_utc"]):result["reason"]="outside_price_validity";return result
    # Explicitly detect any boundary crossed, including a full peak interval between endpoints.
    points=[a,b];day=a.replace(hour=0,minute=0,second=0,microsecond=0)
    while day<=b:
        for w in s.get("peak_windows_utc",[]):
            if day.weekday() in w["weekdays"]:
                for k in ("start","end"):
                    point=day+timedelta(minutes=_minute(w[k]))
                    if a<point<=b:
                        points += [point,point-timedelta(microseconds=1)]
        day+=timedelta(days=1)
    labels={period(t,s) for t in points}
    if len(labels)>1:result["reason"]="crosses_rate_boundary";return result
    u=normalize_usage(c.get("response",{}).get("usage"))
    if u["issues"]:result["reason"]="usage_inconsistent";return result
    ni,no,nc=u["prompt_tokens"],u["completion_tokens"],u["cached_input_tokens"]
    if ni is None or no is None:result["reason"]="usage_missing";return result
    label=labels.pop();rates=s[label]
    if nc is None and rates["input_per_million"]!=rates["cached_input_per_million"]:
        result["reason"]="cache_usage_missing";return result
    nc=nc or 0
    result.update(estimate=((ni-nc)*rates["input_per_million"]+nc*rates["cached_input_per_million"]+no*rates["output_per_million"])/1e6,
                  rate_period=label,reason="known_scoped_list_prices")
    return result
