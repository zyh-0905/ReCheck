
#!/usr/bin/env python3
"""R9 user runner. Never invokes a model unless smoke/run was explicitly requested."""
import os,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent
sys.path[:0]=[str(ROOT),str(ROOT/'vendor/toolsandbox')]
os.environ['POLARS_MAX_THREADS']='1'
os.environ['OPENBLAS_NUM_THREADS']='1'
def main():
 import argparse,json,socket
 p=argparse.ArgumentParser()
 p.add_argument('command',choices=['prepare','smoke','run','audit','export','verify'])
 p.add_argument('archive',nargs='?');p.add_argument('--confirm-calls',type=int,default=0)
 a=p.parse_args()
 if a.command not in ('smoke','run'):
  def deny(*x,**k):raise RuntimeError('Offline command: network disabled')
  socket.create_connection=deny;socket.socket.connect=deny;socket.socket.connect_ex=deny
 from r9lib.artifacts import export_bundle,verify_bundle
 from r9lib.runtime import prepare,smoke,run
 from r9lib.audit import audit
 try:
  if a.command=='prepare':
   r=prepare(ROOT);print(json.dumps({'prepared':True,'fingerprint':r['fingerprint'],'cap':361}));return 0
  if a.command=='verify':
   if not a.archive:raise ValueError('Provide feedback ZIP path')
   print(json.dumps(verify_bundle(a.archive)));return 0
  if a.command=='export':
   print(export_bundle(ROOT));return 0
  if a.command=='audit':
   r=audit(ROOT);print(json.dumps(r,ensure_ascii=False,indent=2));return 0 if r['mechanical_pass'] else 2
  r=smoke(ROOT,a.confirm_calls) if a.command=='smoke' else run(ROOT,a.confirm_calls)
  print(json.dumps(r,ensure_ascii=False,indent=2))
  # Snapshot evidence even after a normal pause. No other model request is made here.
  try:print('Feedback:',export_bundle(ROOT))
  except Exception as e:print('Export issue:',type(e).__name__,str(e))
  return 0 if r['status']=='completed' else 2
 except Exception as e:
  print('STOP:',type(e).__name__,str(e))
  return 2
if __name__=='__main__':raise SystemExit(main())
