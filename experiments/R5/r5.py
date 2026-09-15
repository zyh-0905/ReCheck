#!/usr/bin/env python3
"""R5 local-only calibration, scheduling, rule-execution and audit."""
import argparse,sys,traceback,datetime
from pathlib import Path
from r5lib import storage,data,study,review

ROOT=Path(__file__).resolve().parent

def main():
    parser=argparse.ArgumentParser(description='R5 offline-only study; zero LLM/API calls, no credentials.')
    parser.add_argument('command',choices=['prepare','run','audit','export','verify','execute'])
    parser.add_argument('archive',nargs='?')
    args=parser.parse_args()
    exit_status=0
    with storage.no_network():
        if args.command=='verify':
            if not args.archive:parser.error('verify requires ZIP path')
            print(storage.verify_bundle(args.archive));return 0
        if args.command in ('prepare','execute'):
            study.prepare(ROOT);print('Prepared independent calibration. No LLM calls.')
        if args.command in ('run','execute'):study.run(ROOT)
        if args.command in ('audit','execute'):
            r=review.audit(ROOT)
            print({k:r[k] for k in ('mechanical_pass','complete','rows','replayed_task_records','reference_science_match','scientific_gate')})
            if r['issues']:
                print('ISSUES:',r['issues']);exit_status=2
        if args.command in ('export','execute'):
            stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
            dest=ROOT/'uploads'/f'R5_feedback_{stamp}.zip'
            print(storage.bundle(ROOT,dest));print('UPLOAD:',dest)
    return exit_status

if __name__=='__main__':
    try:raise SystemExit(main())
    except KeyboardInterrupt:
        print('Interrupted. Preserve all output; run audit/export. No model request was made.',file=sys.stderr)
        raise SystemExit(130)
    except Exception:
        traceback.print_exc()
        print('Do not alter protocol or old files. Export available evidence for review.',file=sys.stderr)
        raise SystemExit(1)
