from pathlib import Path
import importlib.util
import pandas as pd
import pytest

def load(name):
    path=Path(__file__).parents[1]/'scripts'/f'{name}.py'
    assert path.exists(), f'{name} implementation required'
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

def test_reproduction_compares_results_but_not_variable_timings():
    m=load('verify_reproduction')
    a=pd.DataFrame({'seed':[1,2],'method':['x','x'],'objective':[.2,.3],'cpu_ms':[1,2]})
    b=a.copy();b['cpu_ms']=[5,6]
    assert m.compare_scientific_frames(a,b,['seed','method'])['rows']==2

def test_reproduction_fails_on_changed_scientific_result():
    m=load('verify_reproduction')
    a=pd.DataFrame({'seed':[1],'method':['x'],'objective':[.2]});b=a.copy();b['objective']=.21
    with pytest.raises(AssertionError):m.compare_scientific_frames(a,b,['seed','method'])

def test_final_pdf_audit_detects_placeholder_authorship():
    m=load('audit')
    p=Path(__file__).parents[1]/'papers/recheck/main.pdf'
    out=m.audit_pdf(p)
    assert out['pages']<=5
    assert out['authorship_complete'] is False
    assert out['unresolved_references'] is False
