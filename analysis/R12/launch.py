"""Run an offline audit with already-installed native ToolSandbox dependencies.
For supplied Python -S set R12_SITE and R12_ROUGE_SOURCE explicitly.
No credentials are read and network calls are rejected before native imports.
"""
import os,sys,socket,runpy,json
from pathlib import Path
ROOT=Path(__file__).resolve().parent
for name in ('R12_SITE','R12_ROUGE_SOURCE','R12_TOOL_SOURCE'):
    if name in os.environ:sys.path.insert(0,os.environ[name])
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'vendor'/'legacy_bridge')]
def deny(*a,**k):raise RuntimeError('R12 offline network denied')
socket.socket.connect=deny;socket.socket.connect_ex=deny;socket.create_connection=deny;socket.getaddrinfo=deny
os.environ.setdefault('POLARS_MAX_THREADS','1');os.environ.setdefault('OPENBLAS_NUM_THREADS','1')
if len(sys.argv)<2:raise SystemExit('usage: launch.py tests | native OUT | supplement OUT | regrade OUT | minimal')
if sys.argv[1]=='tests':
    import unittest
    r=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.discover(str(ROOT/'tests')))
    raise SystemExit(not r.wasSuccessful())
elif sys.argv[1]=='native':
    import native_audit
    native_audit.run(sys.argv[2])
elif sys.argv[1]=='supplement':
    import supplement
    supplement.run(sys.argv[2])
elif sys.argv[1]=='regrade':
    import regrade
    regrade.run(ROOT,sys.argv[2])
elif sys.argv[1]=='minimal':
    import minimal_repro
    minimal_repro.run()
else:raise SystemExit('Unknown command')
