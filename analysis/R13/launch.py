"""Offline only. Reuse a separately installed Python 3.11 ToolSandbox environment.
No credentials are read. Socket-level denial is not an OS-level sandbox.
"""
import os,sys,socket
from pathlib import Path
ROOT=Path(__file__).resolve().parent
sys.dont_write_bytecode=True
sys.path.insert(0,str(ROOT/'vendor/bridge'))
sys.path.insert(0,str(ROOT/'vendor/ToolSandbox'))
for key in ('R13_SITE','R13_ROUGE_SOURCE','R13_TOOL_SOURCE','R13_LEGACY_BRIDGE'):
 if key in os.environ:sys.path.insert(0,os.environ[key])
sys.path.insert(0,str(ROOT/'src'))
def deny(*args,**kwargs):raise RuntimeError('R13 offline networking denied')
socket.socket.connect=deny;socket.socket.connect_ex=deny;socket.create_connection=deny;socket.getaddrinfo=deny
os.environ.setdefault('POLARS_MAX_THREADS','1');os.environ.setdefault('OPENBLAS_NUM_THREADS','1')
if len(sys.argv)<2:raise SystemExit('usage: launch.py census OUT | native OUT | check OUT | regrade OUT | tests')
if sys.argv[1]=='tests':
 import unittest
 r=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.discover(str(ROOT/'tests')))
 raise SystemExit(not r.wasSuccessful())
elif sys.argv[1]=='census':
 import native_census
 native_census.run(sys.argv[2])
elif sys.argv[1]=='native':
 import native_scope_cases
 native_scope_cases.run(sys.argv[2])
elif sys.argv[1] in ('check','regrade'):
 import review_saved
 review_saved.run(ROOT/'results/revision_run1/trajectories',sys.argv[2],native=sys.argv[1]=='regrade')
else:raise SystemExit('Unknown command')
