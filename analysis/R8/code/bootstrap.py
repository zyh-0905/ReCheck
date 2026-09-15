"""Load the unchanged native tool subset; disable all runtime network connects."""
import os, sys, socket
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
os.environ['POLARS_MAX_THREADS']='1'
os.environ['OPENBLAS_NUM_THREADS']='1'
os.environ['OMP_NUM_THREADS']='1'
def deny(*args,**kwargs):
    raise RuntimeError('R8_OFFLINE_NO_NETWORK')
socket.socket.connect=deny
socket.socket.connect_ex=deny
socket.create_connection=deny
# External validated dependencies are an installation artifact, not research data.
if os.environ.get('R8_DEPS'):
    sys.path.insert(0,os.environ['R8_DEPS'])
if os.environ.get('R8_ROUGE'):
    sys.path.insert(0,os.environ['R8_ROUGE'])
sys.path[:0]=[str(ROOT/'native'),str(ROOT/'native/vendor/toolsandbox'),str(ROOT/'code')]
