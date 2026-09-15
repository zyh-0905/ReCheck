#!/usr/bin/env python3
"""R6 offline-only entrypoint. No network/credentials/model runner exists."""
from pathlib import Path
import argparse,sys,traceback,datetime,json
from r6lib import storage,study,review
ROOT=Path(__file__).resolve().parent

def main():
    parser=argparse.ArgumentParser(description='R6 paid calibration offline study')
    parser.add_argument('command',choices=['execute','prepare','run','audit','export','verify'])
    parser.add_argument('archive',nargs='?');args=parser.parse_args();success=True
    with storage.no_network():
        if args.command=='verify':
            if not args.archive:parser.error('verify requires feedback ZIP path')
            obj=storage.verify_bundle(args.archive);print(json.dumps(obj,indent=2));return 0 if obj['pass'] else 2
        if args.command in ('prepare','execute'):print(json.dumps(study.prepare(ROOT),indent=2))
        if args.command in ('run','execute'):print(json.dumps(study.run(ROOT),indent=2))
        if args.command in ('audit','execute'):
            result=review.audit(ROOT);print(json.dumps(result,indent=2));success=bool(result['mechanical_pass'])
        if args.command in ('export','execute'):
            stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
            dest=ROOT/'uploads'/f'R6_feedback_{stamp}.zip';out=storage.bundle(ROOT,dest)
            print(json.dumps({'export':str(dest),'verification':out},indent=2))
    return 0 if success else 2
if __name__=='__main__':
    try:raise SystemExit(main())
    except Exception:
        traceback.print_exc()
        print('Preserve evidence. Do not modify code, references, seeds or locks. Run export for review.',file=sys.stderr)
        raise SystemExit(1)
