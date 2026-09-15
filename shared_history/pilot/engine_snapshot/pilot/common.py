"""Small, audited utilities. No model or provider calls are made here."""
from __future__ import annotations
import hashlib, json, math, platform, re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

VERSION = 'llm-pilot-0.1'
ROOT = Path(__file__).resolve().parents[1]


def utcnow():
    return datetime.now(timezone.utc).isoformat()


def canonical(obj):
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)


def digest(obj):
    return hashlib.sha256(canonical(obj).encode('utf-8')).hexdigest()


def write_json(path, obj):
    path=Path(path);path.parent.mkdir(parents=True, exist_ok=True)
    tmp=path.with_suffix(path.suffix+'.tmp')
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=2, allow_nan=False)+'\n', encoding='utf-8')
    tmp.replace(path)


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def strict_json_object(text):
    if not isinstance(text,str): raise ValueError('model output is not text')
    text=text.strip()
    match=re.fullmatch(r'```(?:json)?\s*\n?(.*?)\n?```',text,flags=re.S)
    if match: text=match.group(1).strip()
    def unique(pairs):
        out={}
        for k,v in pairs:
            if k in out: raise ValueError('duplicate JSON key')
            out[k]=v
        return out
    def bad_constant(x): raise ValueError('non-finite JSON number')
    out=json.loads(text,object_pairs_hook=unique,parse_constant=bad_constant)
    if not isinstance(out,dict): raise ValueError('expected a JSON object')
    return out


def is_number(x):
    return isinstance(x,(int,float)) and not isinstance(x,bool) and math.isfinite(x)


def redact(obj, secret):
    if isinstance(obj,str): return obj.replace(secret,'[REDACTED]') if secret else obj
    if isinstance(obj,list): return [redact(x,secret) for x in obj]
    if isinstance(obj,dict): return {k:redact(v,secret) for k,v in obj.items()}
    return obj


def validate_base_url(url):
    url=url.strip().rstrip('/')
    p=urlsplit(url)
    if p.scheme not in ('https','http') or not p.hostname or p.username or p.password or p.query or p.fragment:
        raise ValueError('Use a credential-free base URL, without query or fragment.')
    if p.scheme=='http' and p.hostname not in ('localhost','127.0.0.1','::1'):
        raise ValueError('Remote endpoints must use HTTPS. HTTP is permitted only on loopback.')
    if p.path.endswith('/chat/completions'):
        raise ValueError('Enter the base URL, usually ending in /v1, not /chat/completions.')
    return url


def default_config():
    return {
        'base_url':'CHANGE_ME', 'model':'CHANGE_ME', 'provider_label':'user-supplied',
        'key_env':'LLM_API_KEY', 'local_no_auth':False, 'backend_kind':'live',
        'max_tokens_field':'max_tokens', 'max_output_tokens':1024,
        'temperature':None, 'extra_body':{}, 'instruction_role':'system',
        'timeout_seconds':180, 'min_interval_seconds':0.5, 'max_requests':300,
        'max_estimated_spend':None,
        'prices':{'currency':'UNSPECIFIED','input_per_million':None,
                  'output_per_million':None,'cached_input_per_million':None}
    }


def validate_config(cfg):
    allowed=set(default_config())
    if set(cfg)-allowed: raise ValueError('Unknown config fields (secrets must not be stored here): '+', '.join(sorted(set(cfg)-allowed)))
    d=default_config();d.update(cfg)
    d['base_url']=validate_base_url(d['base_url'])
    if not isinstance(d['model'],str) or not d['model'].strip() or d['model']=='CHANGE_ME':
        raise ValueError('Set the exact accessible model ID.')
    if d['backend_kind'] not in ('live','test_fixture'): raise ValueError('invalid backend_kind')
    if d['max_tokens_field'] not in ('max_tokens','max_completion_tokens'): raise ValueError('invalid max_tokens_field')
    if d['instruction_role'] not in ('system','developer'): raise ValueError('invalid instruction_role')
    for k in ('max_output_tokens','max_requests'):
        if not isinstance(d[k],int) or isinstance(d[k],bool) or d[k]<1: raise ValueError(k+' must be positive integer')
    if not 1<=d['timeout_seconds']<=1800: raise ValueError('timeout_seconds out of range')
    if not is_number(d['min_interval_seconds']) or d['min_interval_seconds']<0: raise ValueError('invalid interval')
    if d['temperature'] is not None and (not is_number(d['temperature']) or not 0<=d['temperature']<=2): raise ValueError('invalid temperature')
    if not isinstance(d['extra_body'],dict): raise ValueError('extra_body must be an object')
    # Explicit optional provider settings only. Do not allow model, credentials or limits to be overridden.
    if set(d['extra_body'])-{'reasoning_effort','enable_thinking','chat_template_kwargs'}:
        raise ValueError('extra_body supports only reasoning_effort, enable_thinking, chat_template_kwargs')
    blob=canonical(d['extra_body']).lower()
    if any(x in blob for x in ('api_key','authorization','bearer ','password','secret')): raise ValueError('secret-like extra_body prohibited')
    price_keys=set(default_config()['prices'])
    if not isinstance(d['prices'],dict) or set(d['prices'])!=price_keys: raise ValueError('prices fields do not match example')
    for k,v in d['prices'].items():
        if k!='currency' and v is not None and (not is_number(v) or v<0): raise ValueError('invalid token price')
    if d['max_estimated_spend'] is not None:
        if not is_number(d['max_estimated_spend']) or d['max_estimated_spend']<=0: raise ValueError('invalid spend guard')
        if d['prices']['input_per_million'] is None or d['prices']['output_per_million'] is None:
            raise ValueError('Spend guard needs input and output prices; otherwise use a provider-side spending cap.')
    if d['local_no_auth'] and urlsplit(d['base_url']).hostname not in ('localhost','127.0.0.1','::1'):
        raise ValueError('local_no_auth only applies to a local loopback endpoint')
    if not isinstance(d['key_env'],str) or not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*',d['key_env']):
        raise ValueError('key_env must be an environment variable NAME, not a key')
    return d


def public_config(cfg):
    out=dict(cfg);out.pop('base_url');out['base_url_sha256']=digest(cfg['base_url'])
    return out


def request_payload(cfg,messages):
    body={'model':cfg['model'],'messages':messages,'stream':False,
          cfg['max_tokens_field']:cfg['max_output_tokens']}
    if cfg['temperature'] is not None: body['temperature']=cfg['temperature']
    body.update(cfg['extra_body'])
    return body


def response_text(body):
    choices=body.get('choices')
    if not isinstance(choices,list) or len(choices)!=1: raise ValueError('Expected exactly one Chat Completions choice')
    value=choices[0].get('message',{}).get('content')
    if value is None: return ''
    if isinstance(value,str): return value
    if isinstance(value,list):
        return ''.join(p.get('text','') for p in value if isinstance(p,dict) and p.get('type') in ('text','output_text'))
    raise ValueError('Unsupported content field')


def estimate_cost(usage,prices):
    """List-price estimate, not a provider invoice. Missing usage is never zero."""
    if not isinstance(usage,dict): return None
    pi=prices.get('input_per_million');po=prices.get('output_per_million')
    ni=usage.get('prompt_tokens');no=usage.get('completion_tokens')
    if None in (pi,po,ni,no) or not is_number(ni) or not is_number(no) or ni<0 or no<0:return None
    cached=(usage.get('prompt_tokens_details') or {}).get('cached_tokens',0) or 0
    if not is_number(cached) or not 0<=cached<=ni:return None
    pc=prices.get('cached_input_per_million')
    if pc is None:pc=pi  # conservative: no guessed cache discount
    return ((ni-cached)*pi+cached*pc+no*po)/1e6


def source_files():
    paths=[ROOT/'run.py', ROOT/'requirements.txt', ROOT/'config.example.json']
    paths+=sorted((ROOT/'pilot').glob('*.py'))+sorted((ROOT/'vendor').glob('*.py'))
    paths+=sorted((ROOT/'docs').glob('*.md'))
    return [p for p in paths if p.exists()]


def source_hashes():
    return {p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in source_files()}


def freeze_run(run_dir,cfg,study,spec):
    """No output directory can silently change model, code, or experiment design."""
    import numpy as np
    run_dir=Path(run_dir);run_dir.mkdir(parents=True,exist_ok=True)
    contract={'version':VERSION,'config':public_config(cfg),'study':study,'spec':spec,'source_hashes':source_hashes()}
    fingerprint=digest(contract);path=run_dir/'manifest.json'
    if path.exists():
        old=read_json(path)
        if old['fingerprint']!=fingerprint: raise ValueError('Run is frozen: code/config/model/protocol changed. Use a NEW output directory; do not mix results.')
        return old
    manifest={**contract,'fingerprint':fingerprint,'created_utc':utcnow(),
              'runtime':{'python':platform.python_version(),'numpy':np.__version__,'os':platform.system()},
              'evidence_label':'SOFTWARE_TEST_NOT_RESEARCH' if cfg['backend_kind']=='test_fixture' else 'REAL_ENDPOINT_CONTROLLED_PILOT_NOT_CONFIRMATORY'}
    write_json(path,manifest)
    for p in source_files():
        target=run_dir/'code_snapshot'/p.relative_to(ROOT);target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(p.read_bytes())
    return manifest


from contextlib import contextmanager
@contextmanager
def run_lock(run_dir):
    """Exclusive writer lock. A killed process leaves a deliberate manual-unlock gate."""
    import os
    root=Path(run_dir);root.mkdir(parents=True,exist_ok=True);lock=root/'.run.lock'
    try:fd=os.open(lock,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    except FileExistsError:raise ValueError('Another process or interrupted run owns .run.lock. Stop it first; then use unlock --confirm-stopped.') from None
    try:
        with os.fdopen(fd,'w',encoding='utf-8') as f:f.write(canonical({'pid':os.getpid(),'created_utc':utcnow()}))
        yield
    finally:
        try:lock.unlink()
        except FileNotFoundError:pass
