#!/usr/bin/env python3
"""R10 fixed-run entry point. No implicit experiment or credential access."""
from pathlib import Path
import argparse,json
from core.runtime import prepare,run_study,export
from core.audit import audit
from core.common import read
from core.contract import ContractError

def main():
 p=argparse.ArgumentParser();p.add_argument('command',choices=['prepare','status','run','audit','export']);p.add_argument('--confirm-calls',type=int)
 a=p.parse_args();root=Path(__file__).resolve().parent
 try:
  if a.command=='prepare':r=prepare(root)
  elif a.command=='run':r=run_study(root,a.confirm_calls)
  elif a.command=='audit':r=audit(root)
  elif a.command=='export':r={'feedback_zip':export(root)}
  else:
   s=root/'runs/main/status.json';r=read(s) if s.exists() else {'status':'not_started','has_lock':(root/'.run.lock').exists()}
  print(json.dumps(r,ensure_ascii=False,indent=2))
  return 2 if isinstance(r,dict) and r.get('status')=='paused' else 0
 except Exception as e:
  # Errors from allowed contracts are scrubbed by their source; do not expose arbitrary network traces.
  print(json.dumps({'error':str(e) if isinstance(e,ContractError) else type(e).__name__,'preserve_records':True,'automatic_retry':False},ensure_ascii=False));return 2
if __name__=='__main__':raise SystemExit(main())
