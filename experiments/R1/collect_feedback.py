#!/usr/bin/env python3
"""R1 offline evidence collection. No API calls, shell execution, or source writes.

Only explicitly selected files under the given run are read. Experiment modules
are never imported. This tool checks evidence packaging, NOT scientific validity.
Python 3.10+; standard library only.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import stat
import sys
from typing import Any
import zipfile

VERSION = 'handoff-1.0'
TOP = {'manifest.json', 'status.json', 'summary.json', 'SUMMARY.md', 'per_task.csv',
       'method_summary.csv', 'controller_metadata.json', 'smoke_result.json', 'EXPORT_MANIFEST.json'}
DIRS = {'calls', 'attempts', 'records', 'prefixes', 'private', 'code_snapshot'}
BLOCKED_NAMES = {'config.local.json', 'credentials.json', 'cookies.json', 'id_rsa', 'id_ed25519'}
MAX_FILE = 32 * 1024 * 1024
MAX_TOTAL = 256 * 1024 * 1024
MAX_FILES = 10000


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def encoded(obj: Any) -> bytes:
    return (json.dumps(obj, ensure_ascii=False, indent=2, allow_nan=False)+'\n').encode('utf-8')


def digest(obj: Any) -> str:
    return sha(json.dumps(obj, ensure_ascii=False, sort_keys=True,
                          separators=(',', ':'), allow_nan=False).encode('utf-8'))


def strict_json(data: bytes) -> Any:
    def unique(pairs):
        out = {}
        for k, v in pairs:
            if k in out:
                raise ValueError('duplicate JSON key')
            out[k] = v
        return out
    def bad_constant(_):
        raise ValueError('nonfinite JSON number')
    return json.loads(data.decode('utf-8-sig'), object_pairs_hook=unique, parse_constant=bad_constant)


def issue(report: dict, code: str, path: str = '', severity: str = 'warning') -> None:
    report['issues'].append({'code':code, 'path':path, 'severity':severity})


def safe_relative(name: str) -> bool:
    p = PurePosixPath(name)
    return bool(name) and not p.is_absolute() and '\\' not in name and ':' not in name and all(x not in {'.','..'} for x in name.split('/'))


def forbidden_name(name: str) -> bool:
    p = PurePosixPath(name)
    return any(x.startswith('.') or x.lower() in BLOCKED_NAMES for x in p.parts) or p.suffix.lower() in {'.key','.pem','.p12','.pfx','.pyc','.tmp','.exe','.dll'}


def sensitive(data: bytes) -> bool:
    """Conservative common-pattern screening, not a general PII/authenticity test."""
    text = data.decode('utf-8', errors='replace')
    patterns = (
        r'\bsk-(?:proj-|ant-)?[A-Za-z0-9_-]{16,}',
        r'(?i)\bBearer\s+[A-Za-z0-9_.~+/=-]{16,}',
        r'-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----',
        r'\bAKIA[0-9A-Z]{16}\b',
        r'\bgh[pousr]_[A-Za-z0-9]{25,}',
        r'\beyJ[A-Za-z0-9_-]{12,}\.[A-Za-z0-9_-]{12,}\.[A-Za-z0-9_-]{12,}',
        r'(?i)https?://[^\s/]+:[^\s/@]+@',
        r'(?i)[?&](?:api_key|access_token|secret|password)=[^\s&"\']{6,}',
    )
    if any(re.search(p, text) for p in patterns):
        return True
    try:
        obj = strict_json(data)
    except (ValueError, UnicodeError, RecursionError):
        obj = None
    secret_keys = {'api_key','apikey','api-key','authorization','proxy-authorization',
                   'password','private_key','access_token','refresh_token','cookie','set-cookie','secret'}
    placeholders = {'', 'unknown', 'none', 'null', '[redacted]', '<redacted>', 'redacted',
                    'your_api_key', 'your-key', 'not_provided'}
    def walk(x):
        if isinstance(x, dict):
            for k, v in x.items():
                if k.lower() in secret_keys and v is not None:
                    if isinstance(v, str) and v.lower().strip() not in placeholders:
                        return True
                    if not isinstance(v, str):
                        return True
                if walk(v): return True
        elif isinstance(x, list):
            return any(walk(v) for v in x)
        return False
    return walk(obj)


def read_regular(path: Path, limit: int = MAX_FILE) -> bytes:
    s = path.lstat()
    if not stat.S_ISREG(s.st_mode) or path.is_symlink():
        raise ValueError('Only regular, non-symlink files are allowed')
    if s.st_size > limit:
        raise ValueError('File exceeds collection limit')
    with path.open('rb') as f:
        data = f.read(limit+1)
    if len(data) > limit:
        raise ValueError('File exceeds collection limit')
    return data


def gather(root: Path, report: dict) -> dict[str, bytes]:
    files: dict[str, bytes] = {}
    source_names: set[str] = set()
    manifest_path = root/'manifest.json'
    if manifest_path.exists():
        try:
            raw = read_regular(manifest_path)
            files['manifest.json'] = raw
            m = strict_json(raw)
            if isinstance(m, dict) and isinstance(m.get('source_hashes'), dict):
                source_names = set(m['source_hashes'])
        except (OSError, ValueError, RecursionError):
            issue(report, 'MANIFEST_UNREADABLE', 'manifest.json', 'error')
    else:
        issue(report, 'MANIFEST_MISSING', 'manifest.json', 'error')
    total = sum(map(len, files.values()))
    def visit(folder: Path):
        nonlocal total
        for p in sorted(folder.iterdir()):
            rel = p.relative_to(root).as_posix()
            if forbidden_name(rel): continue
            if p.is_symlink():
                issue(report, 'SYMLINK_NOT_COLLECTED', rel, 'error'); continue
            if p.is_dir():
                visit(p); continue
            if not p.is_file():
                issue(report, 'NONREGULAR_NOT_COLLECTED', rel, 'error'); continue
            if rel.startswith('code_snapshot/') and rel[len('code_snapshot/'):] not in source_names:
                continue
            if rel in files: continue
            b = read_regular(p)
            total += len(b)
            if total > MAX_TOTAL or len(files) >= MAX_FILES:
                raise ValueError('Collection limit exceeded; no partial raw export')
            files[rel] = b
    for name in sorted(TOP - {'manifest.json'}):
        p = root/name
        if p.is_symlink(): issue(report,'SYMLINK_NOT_COLLECTED',name,'error')
        elif p.exists():
            files[name] = read_regular(p); total += len(files[name])
    for name in sorted(DIRS):
        p = root/name
        if p.is_symlink(): issue(report, 'SYMLINK_NOT_COLLECTED', name, 'error')
        elif p.is_dir(): visit(p)
        elif p.exists(): issue(report, 'EXPECTED_DIRECTORY', name, 'error')
    if total > MAX_TOTAL: raise ValueError('Collection limit exceeded')
    return files


def inspect_evidence(blobs: dict[str, bytes], contract: dict, report: dict) -> None:
    objects = {}
    for name, data in blobs.items():
        if not name.endswith('.json') or name.startswith('code_snapshot/'): continue
        try:
            objects[name] = strict_json(data)
        except (ValueError, UnicodeError, RecursionError):
            issue(report, 'UNREADABLE_JSON', name, 'error')
    m = objects.get('manifest.json', {})
    if not isinstance(m, dict): m = {}
    cfg = m.get('config', {})
    if not isinstance(cfg, dict): cfg = {}
    identity = True
    checks = [('study',m.get('study'),contract.get('expected_study'),'STUDY_MISMATCH'),
              ('cap',cfg.get('max_output_tokens'),contract.get('expected_output_cap'),'OUTPUT_CAP_MISMATCH'),
              ('fingerprint',m.get('fingerprint'),contract.get('expected_fingerprint'),'RUN_FINGERPRINT_DIFFERS_FROM_PRIOR')]
    for _, actual, expected, code in checks:
        if expected is not None and actual != expected:
            issue(report,code,'manifest.json','error'); identity = False
    report['checks']['matches_requested_run'] = identity and bool(m)
    expected_sha = contract.get('prior_manifest_sha256')
    report['checks']['prior_manifest_bytes_match'] = None if not expected_sha else sha(blobs.get('manifest.json',b'')) == expected_sha
    if report['checks']['prior_manifest_bytes_match'] is False:
        issue(report,'MANIFEST_BYTES_DIFFER_FROM_PRIOR','manifest.json','error')
    keys = ['version','config','study','spec','source_hashes']
    frozen_ok = all(k in m for k in keys) and m.get('fingerprint') == digest({k:m[k] for k in keys})
    report['checks']['manifest_fingerprint_valid'] = frozen_ok
    if not frozen_ok: issue(report,'MANIFEST_FINGERPRINT_INVALID','manifest.json','error')
    sources = m.get('source_hashes', {})
    if not isinstance(sources, dict):
        sources = {}; issue(report,'SOURCE_HASH_LIST_INVALID','manifest.json','error')
    for rel, expected in sources.items():
        if not safe_relative(rel) or forbidden_name(rel):
            issue(report,'SOURCE_PATH_REJECTED','manifest.json','error');continue
        name = 'code_snapshot/'+rel
        if name not in blobs:issue(report,'SOURCE_SNAPSHOT_MISSING',name,'error')
        elif sha(blobs[name]) != expected:issue(report,'SOURCE_HASH_MISMATCH',name,'error')
    report['checks']['declared_source_file_count'] = len(sources)

    def records(prefix, suffix):
        return {PurePosixPath(n).name.removesuffix(suffix):v for n,v in objects.items()
                if n.startswith(prefix) and n.endswith(suffix) and isinstance(v,dict)}
    starts=records('attempts/','_start.json');results=records('attempts/','_result.json')
    calls={n:v for n,v in objects.items() if n.startswith('calls/') and isinstance(v,dict)}
    pending = sorted(set(starts)-set(results))
    for ident in sorted(set(results)-set(starts)):
        issue(report,'RESULT_WITHOUT_START','attempts/'+ident+'_result.json','error')
    endpoint=contract.get('request_endpoint_for_hash_check')
    endpoint_ok=isinstance(endpoint,str) and digest(endpoint)==cfg.get('base_url_sha256')
    report['checks']['request_endpoint_binding_verified']=endpoint_ok
    if not endpoint_ok: issue(report,'REQUEST_HASH_CHECK_UNAVAILABLE','manifest.json')
    for ident,s in starts.items():
        if not isinstance(s.get('payload'),dict):
            issue(report,'REQUEST_PAYLOAD_INVALID','attempts/'+ident+'_start.json','error')
        elif endpoint_ok and digest({'endpoint':endpoint,'payload':s['payload']})!=s.get('request_sha256'):
            issue(report,'REQUEST_HASH_MISMATCH','attempts/'+ident+'_start.json','error')
        r=results.get(ident)
        if r is not None:
            for k in ('attempt','logical_id','request_sha256','payload','metadata'):
                if s.get(k)!=r.get(k):
                    issue(report,'START_RESULT_MISMATCH','attempts/'+ident+'_result.json','error');break
    successes=[r for r in results.values() if r.get('status')=='ok']
    for name, call in calls.items():
        matches=[r for r in successes if r.get('attempt')==call.get('attempt') and r.get('logical_id')==call.get('logical_id')]
        if len(matches)!=1 or matches[0]!=call:
            issue(report,'CALL_RESULT_MISMATCH',name,'error')
    for r in successes:
        if not any(v==r for v in calls.values()):
            issue(report,'SUCCESS_RESULT_WITHOUT_CALL','attempts/'+str(r.get('attempt')),'error')
    ids = [v.get('logical_id') for v in calls.values()]
    if len(set(map(str,ids)))!=len(ids):issue(report,'DUPLICATE_LOGICAL_CALL','calls','error')
    n_length=0;pt=ct=0;missing_usage=0;returned=set()
    for r in results.values():
        response=r.get('response')
        if not isinstance(response,dict): response={}
        if response.get('model') is not None: returned.add(str(response['model']))
        choices=response.get('choices',[])
        if isinstance(choices,list):
            n_length += int(any(isinstance(x,dict) and x.get('finish_reason')=='length' for x in choices))
        usage=response.get('usage')
        if not isinstance(usage,dict):missing_usage+=1;continue
        if all(isinstance(usage.get(k),int) and not isinstance(usage[k],bool) and usage[k]>=0 for k in ('prompt_tokens','completion_tokens')):
            pt+=usage['prompt_tokens'];ct+=usage['completion_tokens']
        else:missing_usage+=1
    report['ledger']={'started_attempts':len(starts),'finished_attempts':len(results),
                      'pending_attempts':pending,'successful_results':len(successes),
                      'completed_call_files':len(calls),'truncated_responses':n_length,
                      'error_results':len(results)-len(successes),'missing_usage_results':missing_usage,
                      'known_prompt_tokens_finished_attempts':pt,'known_completion_tokens_finished_attempts':ct,
                      'task_record_files':sum(n.startswith('records/') for n in blobs),
                      'prefix_files':sum(n.startswith('prefixes/') for n in blobs),
                      'returned_model_ids':sorted(returned),
                      'cost_estimate_recomputed':False,'provider_bill_reconciled':False}
    report['run_description']={'study':m.get('study'),'model':cfg.get('model'),
                               'max_output_tokens':cfg.get('max_output_tokens'),
                               'run_fingerprint':m.get('fingerprint'),'evidence_label':m.get('evidence_label')}
    for folder in ('calls','attempts','prefixes','private'):
        if not any(n.startswith(folder+'/') for n in blobs):
            issue(report,'RAW_DIRECTORY_HAS_NO_FILES',folder)
    if pending: issue(report,'INTERRUPTED_ATTEMPTS_PRESERVED','attempts')
    if n_length: issue(report,'TRUNCATED_RESPONSES_PRESERVED','calls')


def write_bundle(out: Path, entries: dict[str,bytes]) -> None:
    index={'tool_version':VERSION,'sha256':{n:sha(b) for n,b in sorted(entries.items())},
           'meaning':'Byte integrity only; not proof of authentic provider execution or scientific validity.'}
    entries={**entries,'BUNDLE_MANIFEST.json':encoded(index)}
    out.parent.mkdir(parents=True,exist_ok=True)
    # Exclusive creation. Never replace a prior return bundle.
    with zipfile.ZipFile(out,'x',zipfile.ZIP_DEFLATED) as z:
        for n,b in sorted(entries.items()):z.writestr(n,b)


def collect_bundle(run_dir: Path, out: Path, contract: dict,
                   statement_path: Path | None = None, billing_path: Path | None = None) -> dict:
    run_dir=Path(run_dir);out=Path(out).absolute()
    root=run_dir.resolve()
    if root == out.resolve() or root in out.resolve().parents:
        raise ValueError('Output must be outside the source run directory')
    if out.exists():raise FileExistsError('Output already exists; choose a new file')
    report={'task_id':contract.get('task_id'),'collector_version':VERSION,
            'collected_utc':datetime.now(timezone.utc).isoformat(),'status':'REVIEW_REQUIRED',
            'run_label':run_dir.name,'new_model_calls':0,'new_network_requests':0,
            'original_runs_modified_by_tool':False,'selected_source_bytes_unchanged':None,
            'evidence_file_count':0,'issues':[],'checks':{},'ledger':{},
            'operator_statement':{'interrupted_run_status':'unknown','reason':'unknown',
                                  'billing_status':'not_provided','other_calls_in_billing_window':'unknown'},
            'billing_note_attached':False,'research_validity':'NOT_ASSESSED',
            'next_paid_experiment_authorized':False}
    blobs:dict[str,bytes]={};optional:dict[str,bytes]={}
    if run_dir.is_symlink():
        issue(report,'RUN_SYMLINK_REJECTED','source','error');report['status']='SOURCE_PATH_REJECTED'
    elif not root.exists():
        issue(report,'RUN_NOT_FOUND','source','error');report['status']='MISSING_SOURCE'
    elif not root.is_dir():
        issue(report,'RUN_IS_NOT_DIRECTORY','source','error');report['status']='SOURCE_PATH_REJECTED'
    else:
        if (root/'.run.lock').exists():issue(report,'LOCK_PRESENT_NOT_REMOVED','.run.lock')
        try:
            blobs=gather(root,report)
            inspect_evidence(blobs,contract,report)
        except (ValueError,OSError,TypeError,RecursionError,AttributeError):
            issue(report,'COLLECTION_OR_SCHEMA_ERROR','source','error')
            blobs={};report['status']='COLLECTION_BLOCKED'
    if statement_path is not None:
        try:
            raw=read_regular(Path(statement_path),1024*1024)
            st=strict_json(raw)
            allowed={'interrupted_run_status','reason','billing_status','other_calls_in_billing_window','currency','billing_time_window','redactions','notes'}
            if not isinstance(st,dict) or any(k not in allowed or not isinstance(v,str) or len(v)>4000 for k,v in st.items()):
                raise ValueError('Invalid operator statement')
            optional['operator/statement.json']=raw
            if not sensitive(raw):report['operator_statement'].update(st)
        except (OSError,ValueError,UnicodeError,RecursionError):
            issue(report,'OPERATOR_STATEMENT_INVALID','operator/statement.json','error')
    if billing_path is not None:
        bp=Path(billing_path)
        if bp.suffix.lower() not in {'.txt','.md','.json','.csv'}:
            issue(report,'BILLING_NOTE_FORMAT_REJECTED','operator/billing_note','error')
        else:
            try:optional['operator/billing_note'+bp.suffix.lower()]=read_regular(bp,1024*1024)
            except (OSError,ValueError):issue(report,'BILLING_NOTE_UNREADABLE','operator/billing_note','error')
    found=[]
    for n,b in {**blobs,**optional}.items():
        if sensitive(b):found.append(n)
    if found:
        for n in found:issue(report,'COMMON_CREDENTIAL_PATTERN',n,'error')
        blobs={};optional={};report['status']='BLOCKED_SENSITIVE_CONTENT'
        report['operator_statement']={'status':'withheld_due_to_sensitive_content'}
        # Source-derived metadata can also carry a credential; withhold it too.
        report['ledger']={}
        report['run_description']={'status':'withheld_due_to_sensitive_content'}
        report['checks']={}
        if sensitive(report['run_label'].encode()): report['run_label']='withheld'
        for item in report['issues']:
            if sensitive(item['path'].encode()): item['path']='withheld'
    elif blobs:
        unchanged=True
        for n,b in blobs.items():
            try:
                if read_regular(root/n)!=b:unchanged=False
            except (OSError,ValueError):unchanged=False
        report['selected_source_bytes_unchanged']=unchanged
        if not unchanged:
            issue(report,'SOURCE_CHANGED_DURING_COLLECTION','source','error');blobs={};report['status']='SOURCE_UNSTABLE'
    if report['status']=='REVIEW_REQUIRED':
        if any(i['severity']=='error' for i in report['issues']):report['status']='EVIDENCE_WITH_ISSUES'
        elif report['ledger'].get('pending_attempts') or report['ledger'].get('truncated_responses'):
            report['status']='READY_FOR_REVIEW_WITH_INTERRUPTION'
        else:report['status']='READY_FOR_REVIEW'
    report['evidence_file_count']=len(blobs)
    report['billing_note_attached']=any(n.startswith('operator/billing_note') for n in optional)
    report['limits']=['No new experiment was run. No retry, resume, inference, or billing API was invoked.',
                      'Interrupted or malformed responses are preserved, not repaired or replaced.',
                      'Missing records and invoices remain unknown. Do not fabricate replacements.',
                      'No claim of independent audit, complete private-data detection, or provider attestation.',
                      'Successful packaging does not authorize further paid experiments or establish paper readiness.']
    entries={'LOCAL_CHECKS.json':encoded(report),'TASK_CONTRACT.json':encoded(contract),
             'README_RETURN.md':('# R1 evidence return\n\nThis is offline packaging, not a new model experiment.\n'
                                  'Inspect LOCAL_CHECKS.json before drawing conclusions.\n'
                                  'Original copied evidence is under evidence/run/.\n'
                                  'Billing and operator notes are self-reported and optional.\n').encode()}
    entries.update({'evidence/run/'+n:b for n,b in blobs.items()})
    entries.update(optional)
    write_bundle(out,entries)
    verified=verify_bundle(out)
    if not verified['ok']:raise ValueError('Written bundle failed integrity verification')
    return report


def verify_bundle(path: Path) -> dict:
    try:
        with zipfile.ZipFile(path) as z:
            info=z.infolist();names=[x.filename for x in info]
            if len(names)!=len(set(names)) or len(names)>MAX_FILES+20 or any(not safe_relative(n) for n in names):
                return {'ok':False,'reason':'unsafe_or_duplicate_paths'}
            if sum(x.file_size for x in info)>MAX_TOTAL+4*1024*1024 or any(x.file_size>MAX_FILE for x in info):
                return {'ok':False,'reason':'size_limit'}
            m=strict_json(z.read('BUNDLE_MANIFEST.json'))
            expected=m['sha256']
            if set(expected)!=(set(names)-{'BUNDLE_MANIFEST.json'}):
                return {'ok':False,'reason':'file_set_mismatch'}
            bad=[n for n,h in expected.items() if sha(z.read(n))!=h]
            return {'ok':not bad,'checked_files':len(expected),'mismatches':bad}
    except (OSError,ValueError,KeyError,TypeError,zipfile.BadZipFile,RecursionError):
        return {'ok':False,'reason':'unreadable_bundle'}


def main() -> int:
    parser=argparse.ArgumentParser(description='Offline collection only; zero LLM calls. Source runs are never modified.')
    parser.add_argument('--project',type=Path,help='Existing LLM_Pilot_Kit project directory')
    parser.add_argument('--run',help='Run path relative to project; defaults to the named interrupted run')
    parser.add_argument('--out',type=Path,help='New ZIP path outside the original run')
    parser.add_argument('--stopped',action='store_true',help='Confirm no process is writing the original experiment directory')
    parser.add_argument('--statement',type=Path,help='Optional operator statement JSON; unknown is accepted')
    parser.add_argument('--billing-note',type=Path,help='Optional already-sanitized text/csv/json billing note; never fetched online')
    parser.add_argument('--verify',type=Path,help='Verify an already collected ZIP; no other action')
    args=parser.parse_args()
    if args.verify:
        v=verify_bundle(args.verify);print(json.dumps(v,ensure_ascii=False,indent=2));return 0 if v['ok'] else 2
    if not args.stopped:
        parser.error('Confirm experiment writer is stopped, then add --stopped. Do not remove old locks or resume requests.')
    contract_path=Path(__file__).resolve().with_name('TASK_CONTRACT.json')
    contract=strict_json(read_regular(contract_path))
    project=args.project
    if project is None:
        if not sys.stdin.isatty():parser.error('--project is required in noninteractive execution')
        project=Path(input('Original LLM_Pilot_Kit directory (no key/password): ').strip().strip('"').strip("'"))
    project=project.expanduser().absolute()
    if not project.is_dir():parser.error('Project directory does not exist; correct --project. Do not recreate an empty project.')
    rel=args.run or contract['default_run']
    if not safe_relative(rel):parser.error('--run must be a safe path relative to the selected project')
    run=project.joinpath(*PurePosixPath(rel).parts)
    for p in [run,*list(run.parents)[:len(PurePosixPath(rel).parts)-1]]:
        if p.is_symlink():parser.error('Symlinked run paths are not followed; use the actual project directory')
    if project.resolve() not in run.resolve().parents:parser.error('Run must remain inside project')
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S_%fZ')
    out=args.out or Path(__file__).resolve().parent/'uploads'/('R1_evidence_'+stamp+'.zip')
    try:
        r=collect_bundle(run,out,contract,args.statement,args.billing_note)
    except (OSError,ValueError,RecursionError):
        print('Collection blocked. Check paths, file stability, limits and output existence; do not alter original records.',file=sys.stderr)
        return 2
    print(json.dumps({'status':r['status'],'new_model_calls':0,'evidence_files':r['evidence_file_count'],
                      'issues':r['issues'],'return_zip':str(out.absolute()),
                      'next_paid_experiment_authorized':False},ensure_ascii=False,indent=2))
    # A diagnostic bundle is still a valid return; do not rerun research to "fix" it.
    return 0

if __name__=='__main__':
    raise SystemExit(main())
