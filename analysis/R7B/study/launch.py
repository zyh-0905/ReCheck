"""Network-disabled launcher for local upstream integration and research fixtures."""
import sys,os,socket,json,runpy
from pathlib import Path
ROOT=Path(__file__).resolve().parent
source=Path(os.environ.get('R7_SOURCE',str(ROOT.parent/'native/source/ToolSandbox-c8571d7854316d2e1c5f288e59fe1e34e53f6dd1'))).resolve()
sys.path[:0]=[str(ROOT),str(source)]
blocked=[]
def deny(*a,**kw):
 blocked.append('socket operation denied');raise RuntimeError('R7B network disabled')
socket.create_connection=deny;socket.getaddrinfo=deny;socket.socket.connect=deny;socket.socket.connect_ex=deny
if __name__=='__main__':
 if len(sys.argv)<2:raise SystemExit('usage: launch.py test|study [out]')
 if sys.argv[1]=='test':
  import unittest
  suite=unittest.defaultTestLoader.discover(str(ROOT/'tests'))
  result=unittest.TextTestRunner(verbosity=2).run(suite)
  raise SystemExit(0 if result.wasSuccessful() else 1)
 elif sys.argv[1]=='study':
  import native_study
  out=Path(sys.argv[2]);out.mkdir(parents=True,exist_ok=False)
  native_study.run_all(out)
  (out/'NETWORK_GUARD.json').write_text(json.dumps({'blocked_operations':blocked,'new_llm_api_calls':0}))
 else:raise SystemExit('unknown command')
