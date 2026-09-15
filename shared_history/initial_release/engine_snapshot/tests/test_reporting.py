import importlib.util
from pathlib import Path
import pandas as pd
import numpy as np

def report_module():
    path=Path(__file__).parents[1]/'scripts'/'make_report.py'
    assert path.exists(), 'report generator must exist'
    spec=importlib.util.spec_from_file_location('make_report',path)
    mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
    return mod

def test_recheck_bootstrap_clusters_base_seeds_not_regime_labels():
    m=report_module()
    df=pd.DataFrame([{'seed':s,'method':a,'objective':s+(a=='B')+regime} for s in [1,2] for a in ['A','B'] for regime in [0,10]])
    out=m.recheck_seed_table(df,'objective')
    assert out.shape==(2,2)
    assert np.allclose(out['B']-out['A'],1)

def test_stratified_paired_interval_retains_pairing():
    m=report_module()
    out=m.stratified_difference([1,2,4,7],[2,3,5,8],['a','a','b','b'],repeats=100)
    assert out['mean_difference']==-1
    assert out['low']==out['high']==-1
