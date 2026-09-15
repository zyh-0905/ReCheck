"""Offline reproduction from the included raw public archive. Does not call models."""
from __future__ import annotations
import argparse,hashlib,json,socket,stat,sys,tempfile,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'src'))
from analyze import run
from finalize import finalize
from independent_numeric import run as independently_check

def blocked(*args,**kwargs):raise RuntimeError('Network disabled for offline reproduction')

def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args()
 if a.out.exists():raise SystemExit('Refuse to overwrite an existing output directory')
 socket.create_connection=blocked;socket.getaddrinfo=blocked;socket.socket.connect=blocked
 source=ROOT/'inputs/public_source.zip'
 expected=json.loads((ROOT/'PROTOCOL.json').read_text())['input_sha256']
 assert hashlib.sha256(source.read_bytes()).hexdigest()==expected
 lock=json.loads((ROOT/'ANALYSIS_LOCK.json').read_text())
 for path,dig in lock['files'].items():assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==dig,path
 assert hashlib.sha256((ROOT/'PROTOCOL.json').read_bytes()).hexdigest()==lock['protocol_sha256']
 a.out.mkdir(parents=True)
 with tempfile.TemporaryDirectory(prefix='r15-offline-') as d:
  tmp=Path(d)
  with zipfile.ZipFile(source) as z:
   assert sum(i.file_size for i in z.infolist())<300_000_000
   for i in z.infolist():
    path=Path(i.filename)
    assert not path.is_absolute() and '..' not in path.parts and not stat.S_ISLNK(i.external_attr>>16)
    # Only original raw data files; never execute the archived downloader.
    if i.filename.startswith('raw/'):z.extract(i,tmp)
  run(tmp/'raw',a.out/'dev','dev');run(tmp/'raw',a.out/'later','later')
 summary=finalize(ROOT,a.out)
 independent=independently_check(source,ROOT/'results/REVIEW_ANNOTATIONS.json',a.out/'independent_check.json')
 print(json.dumps({'records':summary['total']['records'],'conservative_review':summary['review_counts'],'independent_checks':independent['passes'],'new_model_calls':0},ensure_ascii=False,indent=2))

if __name__=='__main__':main()
