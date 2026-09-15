#!/usr/bin/env python3
"""Only run --confirm-calls 360 can issue paid requests. No smoke command."""
from pathlib import Path
import sys,argparse,json
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'vendor/toolsandbox'))
from nt.runtime import prepare,run_study,export
from nt.audit import audit
from nt.common import read

def main():
 p=argparse.ArgumentParser();p.add_argument('command',choices=['prepare','run','audit','export','status']);p.add_argument('--confirm-calls',type=int)
 a=p.parse_args()
 try:
  if a.command=='prepare':r=prepare(ROOT)
  elif a.command=='run':r=run_study(ROOT,a.confirm_calls)
  elif a.command=='audit':r=audit(ROOT)
  elif a.command=='export':print(export(ROOT));return 0
  else:
   f=ROOT/'runs/main/status.json';r=read(f) if f.exists() else {'status':'absent'}
  print(json.dumps(r,ensure_ascii=False,indent=2))
  return 2 if r.get('status')=='paused' or r.get('mechanical_pass') is False else 0
 except Exception as exc:
  print(f'Stopped: {type(exc).__name__}: {exc}',file=sys.stderr);return 2
if __name__=='__main__':raise SystemExit(main())
