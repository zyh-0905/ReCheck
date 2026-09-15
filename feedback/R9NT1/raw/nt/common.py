
from pathlib import Path
from datetime import datetime,timezone
from contextlib import contextmanager
import os,json,hashlib,socket
from .contract import canonical,strict_json,ContractError
def sha(data):return hashlib.sha256(data).hexdigest()
def digest(obj):return sha(canonical(obj).encode())
def now():return datetime.now(timezone.utc).isoformat()
def read(path):return strict_json(Path(path).read_text(encoding="utf-8"))
def write(path,obj,once=False):
 p=Path(path);p.parent.mkdir(parents=True,exist_ok=True)
 text=json.dumps(obj,ensure_ascii=False,sort_keys=True,indent=2,allow_nan=False)+"\n"
 if once:
  with p.open("x",encoding="utf-8") as f:f.write(text)
 else:
  tmp=p.with_name(p.name+".tmp")
  with tmp.open("w",encoding="utf-8") as f:f.write(text)
  os.replace(tmp,p)
@contextmanager
def no_network():
 def blocked(*a,**k):raise RuntimeError("Network forbidden during native/local evaluation")
 a,b,c=socket.socket.connect,socket.socket.connect_ex,socket.create_connection
 socket.socket.connect=blocked;socket.socket.connect_ex=blocked;socket.create_connection=blocked
 try:yield
 finally:socket.socket.connect=a;socket.socket.connect_ex=b;socket.create_connection=c
def source_paths(root):
 root=Path(root);out=[]
 for p in root.rglob("*"):
  rel=p.relative_to(root)
  if any(x in ("runs","uploads",".venv","__pycache__",".git") for x in rel.parts):continue
  if p.is_symlink():raise ContractError("Symlink in source")
  if p.is_file() and rel.as_posix() not in ("SOURCE_MANIFEST.json","PREPARED.json",".run.lock"):
   out.append(p)
 return sorted(out)
def verify_source(root):
 root=Path(root);m=read(root/"SOURCE_MANIFEST.json")
 actual={p.relative_to(root).as_posix():{"bytes":p.stat().st_size,"sha256":sha(p.read_bytes())} for p in source_paths(root)}
 if actual!=m["files"]:raise ContractError("Source changed; preserve and export, do not edit hashes")
 return digest(m)
@contextmanager
def locked(root):
 p=Path(root)/".run.lock"
 with p.open("x",encoding="utf-8") as f:json.dump({"pid":os.getpid(),"created":now()},f)
 try:yield
 finally:p.unlink(missing_ok=True)
