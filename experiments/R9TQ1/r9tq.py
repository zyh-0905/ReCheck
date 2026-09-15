#!/usr/bin/env python3
"""R9TQ1 CLI. Only `qualify --confirm-calls 12` can send model requests."""
from pathlib import Path
import sys,argparse,json
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/"vendor/toolsandbox"))
from tq.runtime import prepare,qualify,audit,export
def main():
 p=argparse.ArgumentParser()
 p.add_argument("command",choices=["prepare","qualify","audit","export","status"])
 p.add_argument("--confirm-calls",type=int)
 a=p.parse_args()
 try:
  if a.command=="prepare":r=prepare(ROOT)
  elif a.command=="qualify":r=qualify(ROOT,a.confirm_calls)
  elif a.command=="audit":r=audit(ROOT)
  elif a.command=="export":
   print(export(ROOT));return 0
  else:
   f=ROOT/"runs/qualification/status.json"
   r=json.loads(f.read_text()) if f.exists() else {"status":"absent"}
  print(json.dumps(r,ensure_ascii=False,indent=2))
  if r.get("status") in ("paused","completed_not_qualified") or r.get("mechanical_pass") is False:return 2
  return 0
 except Exception as e:
  # Errors from local controlled checks only; no secret/client exceptions are printed verbatim.
  print(f"Stopped: {type(e).__name__}: {e}",file=sys.stderr);return 2
if __name__=="__main__":raise SystemExit(main())
