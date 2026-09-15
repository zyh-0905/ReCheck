#!/usr/bin/env python3
"""Offline reproduction of R14 public-corpus analysis. Never calls a model.
Usage: python reproduce.py --out /absolute/new/directory
The source collector and any downloaded code are NOT executed.
"""
from pathlib import Path,PurePosixPath
import argparse,hashlib,json,zipfile,stat,subprocess,sys,shutil

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True);a=p.parse_args();base=Path(__file__).resolve().parent;out=a.out.resolve()
 if out.exists():raise SystemExit('Output must be a NEW directory; refusing overwrite.')
 for name,expected in json.loads((base/'ANALYSIS_LOCK.json').read_text())['source_freeze'].items():
  if hashlib.sha256((base/name).read_bytes()).hexdigest()!=expected:raise SystemExit('Frozen source differs: '+name)
 zpath=base/'inputs/R14_public_data_original.zip';out.mkdir(parents=True);dest=out/'inputs/download';dest.mkdir(parents=True)
 with zipfile.ZipFile(zpath) as z:
  infos=z.infolist()
  if sum(x.file_size for x in infos)>512*1024*1024:raise SystemExit('Archive too large')
  seen=set()
  for i in infos:
   path=PurePosixPath(i.filename)
   if i.filename in seen or path.is_absolute() or '..' in path.parts or stat.S_ISLNK(i.external_attr>>16):raise SystemExit('Unsafe archive path')
   seen.add(i.filename)
   if i.is_dir():continue
   q=dest/path;q.parent.mkdir(parents=True,exist_ok=True);q.write_bytes(z.read(i))
 m=json.loads((dest/'MANIFEST.json').read_text())
 for v in m['files']:
  b=(dest/'raw'/v['path']).read_bytes()
  if len(b)!=v['bytes'] or hashlib.sha256(b).hexdigest()!=v['sha256']:raise SystemExit('Corrupt raw data: '+v['path'])
 (out/'results').mkdir();(out/'logs').mkdir()
 cmds=[
  [sys.executable,str(base/'src/corpus_audit.py'),'--raw',str(dest/'raw'),'--out',str(out/'results/dev_v2'),'--split','dev'],
  [sys.executable,str(base/'src/corpus_audit.py'),'--raw',str(dest/'raw'),'--out',str(out/'results/heldout_v1'),'--split','heldout'],
  [sys.executable,str(base/'src/finalize_results.py'),'--root',str(out)],
  [sys.executable,str(base/'src/sensitivity_review.py'),'--raw',str(dest/'raw'),'--out',str(out/'results')],
  [sys.executable,str(base/'src/independent_check.py'),'--root',str(out)],
 ]
 for n,cmd in enumerate(cmds):
  with (out/'logs'/f'command_{n}.log').open('w') as f:subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT,check=True)
 names=['all_episodes.csv','by_model_persona.csv','combined_summary.json','sequential_scopes.csv','receipt_name_anomalies.json','posthoc_semantic_sensitivity.csv','posthoc_phase_sensitivity.csv','posthoc_sensitivity_summary.json','independent_final_check.json','raw_file_checks.json']
 comparisons={n:(base/'results'/n).read_bytes()==(out/'results'/n).read_bytes() for n in names}
 if not all(comparisons.values()):raise SystemExit('Scientific output mismatch: '+str(comparisons))
 (out/'verification.json').write_text(json.dumps({'raw_files':len(m['files']),'scientific_outputs_equal':comparisons,'new_model_calls':0},indent=2)+'\n');print(json.dumps(comparisons,indent=2))
if __name__=='__main__':main()
