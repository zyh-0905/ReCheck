
#!/usr/bin/env python3
"""R4 user-side runner. prepare/audit/export never call the model."""
from pathlib import Path
import argparse,copy,getpass,json,os,sys,time
from pilot.common import read_json,write_json,digest,utcnow,strict_json_object,run_lock
from pilot.client import RunStopped
from r4lib import protocol,review,storage,experiment,offline,repair_guard
from r4lib.session import Client,validate_r4_config
from r4lib.accounting import validate_schedule
ROOT=Path(__file__).resolve().parent

def require_call_consent(value,expected):
    if value!=expected:raise ValueError(f"Explicit cap consent required: --confirm-calls {expected}. No request sent.")

def config_and_billing(root=ROOT):
    cfg=validate_r4_config(read_json(root/"config.local.json"))
    bill=validate_schedule(read_json(root/"billing.local.json"))
    return cfg,bill

def prepare(root=ROOT):
    integrity=storage.verify_distribution(root)
    existing=list((root/"runs").glob("*/attempts/*_start.json"))
    if existing:raise ValueError("prepare is frozen after any attempt. Use audit/export; do not rewrite experiment preparation.")
    if not (root/"config.local.json").exists():write_json(root/"config.local.json",read_json(root/"config.example.json"))
    if not (root/"billing.local.json").exists():write_json(root/"billing.local.json",read_json(root/"billing.example.json"))
    cfg,bill=config_and_billing(root);s=protocol.load_protocol()
    flight=offline.preflight(s);reg=review.regression_checks();grid=offline.factorial_report();cost=repair_guard.prior_diagnostic()
    report=root/"offline_reports";report.mkdir(exist_ok=True)
    write_json(report/"EXACT_GRID.json",grid);write_json(report/"PREFLIGHT.json",flight);write_json(report/"REGRESSION.json",reg);write_json(report/"REPAIR_COST_DIAGNOSTIC.json",cost)
    prepared={"task_id":s["protocol_id"],"prepared_utc":utcnow(),"integrity":integrity,
      "config_sha256":digest(cfg),"billing_sha256":digest(bill),"protocol_sha256":digest(s),
      "source_sha256":digest(storage.source_hashes(root)),"preflight_pass":flight["pass"],"regression_pass":reg["pass"],
      "network_calls":0,"planned_main_calls":408,"planned_smoke_calls":1,
      "model_profile":storage.profile(cfg),"price_status":"unknown" if not bill.get("enabled") else "user_sourced_list_prices_not_invoice"}
    write_json(report/"PREPARED.json",prepared)
    if not flight["pass"] or not reg["pass"]:raise ValueError("Offline gate failed; export diagnostic package, do not change seeds/parameters.")
    print(json.dumps({"offline_gate":"PASS","remote_model_calls":0,"planned_main_calls":408,
      "model":cfg["model"],"main_output_cap":16384,"prices":prepared["price_status"],
      "trajectory_probe_disagreements":[r["action_differences"] for r in flight["streams"]]},ensure_ascii=False,indent=2))
    return prepared

def require_prepared(root,cfg,bill):
    storage.verify_distribution(root)
    f=root/"offline_reports/PREPARED.json"
    if not f.exists():raise ValueError("Run prepare first; no request sent.")
    d=read_json(f);s=protocol.load_protocol()
    if not d.get("preflight_pass") or not d.get("regression_pass"):raise ValueError("Offline gate not passed")
    expected={"config_sha256":digest(cfg),"billing_sha256":digest(bill),"protocol_sha256":digest(s),
              "source_sha256":digest(storage.source_hashes(root))}
    if any(d.get(k)!=v for k,v in expected.items()):raise ValueError("Prepared config/code/protocol differs. Do not edit a frozen run.")

def require_smoke(root,cfg):
    sr=root/"runs/R4_smoke"
    try:d=read_json(sr/"smoke_result.json");status=read_json(sr/"status.json")
    except FileNotFoundError:raise ValueError("No completed R4 smoke. Run the one-call smoke first.") from None
    if not d.get("json_ok") or status.get("state")!="completed" or d.get("profile_sha256")!=digest(storage.profile(cfg)):
        raise ValueError("Smoke missing, failed, or used different request settings. No main requests sent.")
    files=list((sr/"calls").glob("*.json"))
    if len(files)!=1:raise ValueError("Smoke must contain exactly one recorded response.")
    raw=read_json(files[0])
    if raw.get("status")!="ok" or raw.get("response",{}).get("choices",[{}])[0].get("finish_reason")!="stop":
        raise ValueError("Smoke response failed.")
    if strict_json_object(raw.get("text"))!={"ok":True}:raise ValueError("Smoke raw response disagrees with summary.")
    return d

def _secret(cfg):
    key=os.environ.get(cfg["key_env"],"")
    if not key and not cfg["local_no_auth"]:
        key=getpass.getpass("API key (hidden, process only; never saved): ").strip()
        if not key:raise ValueError("No credential entered")
    return key

def _audit_existing(root):
    out={}
    for name in ("R4_smoke","R4_recheck"):
        run=root/"runs"/name
        if (run/"manifest.json").exists():
            out[name]=review.summarize(run)
            if name=="R4_recheck":out[name]["replay_audit"]=review.replay_check(run)
    return out

def run_paid(command,confirmed,root=ROOT):
    cap=1 if command=="smoke" else 408;require_call_consent(confirmed,cap)
    cfg,bill=config_and_billing(root);require_prepared(root,cfg,bill)
    if command=="run":require_smoke(root,cfg)
    study="r4_smoke" if command=="smoke" else "r4_recheck"
    spec={"phase":"connectivity_only","logical_calls":1} if command=="smoke" else protocol.load_protocol()
    run=root/"runs"/("R4_smoke" if command=="smoke" else "R4_recheck")
    with run_lock(run):
        storage.freeze(run,cfg,study,spec,bill,root=root)
        if (run/"status.json").exists() and read_json(run/"status.json").get("state")=="completed":
            print("This frozen run already completed. No requests will be resampled.")
            review.summarize(run);return 0
        if (run/"status.json").exists() and read_json(run/"status.json").get("state") in ("paused","running"):
            raise RunStopped("This run is paused or unclosed. Export evidence; automatic continuation is not authorised.")
        if command=="run" and not (run/"endpoint_identity.json").exists():
            write_json(run/"endpoint_identity.json",read_json(root/"runs/R4_smoke/endpoint_identity.json"))
        # Billable actions cannot occur before all offline and smoke gates.
        key=_secret(cfg);client=Client(cfg,run,key,cap=cap)
        start=time.perf_counter();invocation=utcnow()
        storage.append_event(run,"run_events.jsonl",{"event":"invocation_started","utc":invocation,"prior_budget":client.budget()})
        write_json(run/"status.json",{"state":"running","updated_utc":utcnow(),"budget":client.budget()})
        rc=0
        try:
            if command=="smoke":
                rec=client.complete("r4/smoke/one",[{"role":"user","content":'Return exactly {"ok":true} as JSON.'}],
                                    {"phase":"connectivity"})
                ok=strict_json_object(rec["text"])=={"ok":True}
                write_json(run/"smoke_result.json",{"json_ok":ok,"profile_sha256":digest(storage.profile(cfg)),
                   "requested_model":cfg["model"],"returned_model":rec["response"].get("model"),
                   "system_fingerprint":rec["response"].get("system_fingerprint"),
                   "claim":"Metadata recorded, not an independent weight-identity attestation."})
                if not ok:raise RunStopped("Smoke JSON not the requested object. No resampling.")
            else:experiment.run(client,cfg,run,spec)
            write_json(run/"status.json",{"state":"completed","updated_utc":utcnow(),"budget":client.budget()})
        except (RunStopped,KeyboardInterrupt) as exc:
            why="KeyboardInterrupt; remote receipt of any open attempt remains unknown" if isinstance(exc,KeyboardInterrupt) else str(exc)
            write_json(run/"status.json",{"state":"paused","updated_utc":utcnow(),"reason":why,"budget":client.budget()})
            print("PAUSED:",why);rc=2
        except Exception as exc:
            write_json(run/"status.json",{"state":"paused","updated_utc":utcnow(),"reason":"local_exception:"+type(exc).__name__,
                       "budget":client.budget()})
            print("PAUSED on local error:",type(exc).__name__,str(exc));rc=2
        finally:
            storage.append_event(run,"run_events.jsonl",{"event":"invocation_ended","started_utc":invocation,"utc":utcnow(),
                 "wall_seconds":time.perf_counter()-start,"budget":client.budget()})
            review.summarize(run)
    out=storage.export_bundle(root)
    print("Feedback ZIP:",out)
    if rc:print("Upload the partial evidence. Do not edit, unlock, retry, change caps, or launch another batch.")
    return rc

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    sub=p.add_subparsers(dest="command",required=True)
    sub.add_parser("prepare")
    for name in ("smoke","run"):
        q=sub.add_parser(name);q.add_argument("--confirm-calls",type=int)
    sub.add_parser("audit");sub.add_parser("export")
    q=sub.add_parser("verify");q.add_argument("zipfile",type=Path)
    a=p.parse_args(argv)
    if a.command=="prepare":prepare();return 0
    if a.command in ("smoke","run"):return run_paid(a.command,a.confirm_calls)
    if a.command=="audit":
        out=_audit_existing(ROOT)
        print(json.dumps({k:{"ledger":v["ledger"],"records":v["completed_records"],"scientific_gate":v["scientific_gate"]} for k,v in out.items()},ensure_ascii=False,indent=2))
        return 0
    if a.command=="export":
        _audit_existing(ROOT);print("Feedback ZIP:",storage.export_bundle(ROOT));return 0
    print(json.dumps(storage.verify_bundle(a.zipfile),indent=2));return 0

if __name__=="__main__":
    try:sys.exit(main())
    except (ValueError,FileNotFoundError,RunStopped) as exc:
        print("STOP:",str(exc),file=sys.stderr)
        print("No automatic retry. Fixes or new experiments require review; use export for available evidence.",file=sys.stderr)
        sys.exit(2)
