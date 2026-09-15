#!/usr/bin/env python3
"""Re-execute every scientific experiment in a temporary output directory.

Only measured timings may differ. Do not overwrite the first-run result bundle.
This is a deterministic reproduction check, not additional independent evidence.
"""
from pathlib import Path
import sys,json,tempfile,hashlib,time,contextlib,io
import pandas as pd
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from src.recheck import experiment as rc
from src.repairlens import experiment as rl

TIMINGS={'cpu_ms','planning_ms','execution_ms','recheck_compile_ms','no_task_compile_ms'}

def compare_scientific_frames(original,reproduced,keys):
    if original.duplicated(keys).any() or reproduced.duplicated(keys).any():
        raise AssertionError('comparison keys must identify a unique run')
    columns=sorted(set(original.columns)-TIMINGS)
    if set(columns)!=set(reproduced.columns)-TIMINGS:raise AssertionError('column mismatch')
    a=original.sort_values(keys)[columns].reset_index(drop=True)
    b=reproduced.sort_values(keys)[columns].reset_index(drop=True)
    pd.testing.assert_frame_equal(a,b,check_exact=False,check_dtype=False,rtol=1e-10,atol=1e-12)
    return {'rows':len(a),'scientific_columns':columns,'match':True,'excluded_columns':sorted(set(original.columns)&TIMINGS)}

def main():
    start=time.perf_counter();checks={}
    with tempfile.TemporaryDirectory(prefix='research-reproduction-') as tmp:
        out=Path(tmp)
        for d in ['results','configs']:(out/d).mkdir()
        rc.ROOT=out;rl.ROOT=out
        rc.calibrate(80,list(range(100,116)))
        orig=json.loads((ROOT/'configs/recheck_calibration.json').read_text())
        assert orig==json.loads((out/'configs/recheck_calibration.json').read_text())
        rc.run_main();rc.run_boundaries();rc.run_sql();rl.run_main();rl.run_support_stress()
        files={
            'recheck_development.csv':['hazard','rho','price','method','parameter'],
            'recheck_main.csv':['seed','hazard','rho','price','method'],
            'recheck_boundaries.csv':['condition','seed','method'],
            'recheck_sql.csv':['seed','method'],
            'repairlens_main.csv':['seed','method'],
            'repairlens_support_stress.csv':['condition','seed','method']}
        for f,keys in files.items():
            checks[f]=compare_scientific_frames(pd.read_csv(ROOT/'results'/f),pd.read_csv(out/'results'/f),keys)
        assert json.loads((ROOT/'results/repairlens_instances.json').read_text())==json.loads((out/'results/repairlens_instances.json').read_text())
        import gzip
        for f in ['recheck_traces.jsonl.gz','repairlens_traces.jsonl.gz']:
            with gzip.open(ROOT/'results'/f,'rb') as a,gzip.open(out/'results'/f,'rb') as b:
                aa=a.read();bb=b.read();assert aa==bb
                checks[f]={'decompressed_sha256':hashlib.sha256(aa).hexdigest(),'match':True}
    result={'passed':True,'scope':'full same-environment deterministic rerun; not independent replication or new sample',
            'elapsed_seconds':time.perf_counter()-start,'checks':checks,
            'timings':'Original recorded timings retained. Repeated wall times are not expected to be byte-identical.'}
    (ROOT/'results/reproduction_audit.json').write_text(json.dumps(result,indent=2))
    print(json.dumps(result,indent=2))

if __name__=='__main__':main()
