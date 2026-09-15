import pytest


def toy_problem():
    from src.repairlens.core import Probe, RepairProblem
    return RepairProblem(required_masks=(1,2),prior=(.5,.5),artifact_costs=(5.,5.),probes=(
        Probe('diagnose',1.,(0,1),0),
        Probe('refresh-a',5.,(0,1),1),
        Probe('refresh-b',5.,(0,1),2)))


def test_terminal_union_and_cache_subtraction():
    from src.repairlens.core import terminal_cost
    p=toy_problem()
    assert terminal_cost(p,(0,1),0)==10
    assert terminal_cost(p,(0,1),1)==5
    assert terminal_cost(p,(0,),0)==5


def test_exact_policy_hand_computed():
    from src.repairlens.core import RepairSolver
    s=RepairSolver(toy_problem())
    value,action=s.choose((0,1),0,0)
    assert value==pytest.approx(6.)
    assert action==0


def test_productive_probe_is_better_than_discarding_result():
    from src.repairlens.core import Probe, RepairProblem, RepairSolver
    p=RepairProblem((1,2),(.9,.1),(5.,5.),(
        Probe('refresh-a',5.,(0,1),1),Probe('inspect',3.,(0,1),0)))
    good=RepairSolver(p,reuse=True).choose((0,1),0,0)
    bad=RepairSolver(p,reuse=False).choose((0,1),0,0)
    assert good[0]==pytest.approx(5.5)
    assert bad[0]==pytest.approx(8.)


def test_irrelevant_nuisance_probe_not_chosen():
    from src.repairlens.core import Probe, RepairProblem, RepairSolver
    p=RepairProblem((1,1),(.5,.5),(3.,),(Probe('route',.1,(0,1),0),))
    value,action=RepairSolver(p).choose((0,1),0,0)
    assert action==-1
    assert value==3


def test_empty_support_is_not_safe():
    from src.repairlens.core import terminal_cost
    with pytest.raises(ValueError): terminal_cost(toy_problem(),(),0)


def test_negative_cost_rejected():
    from src.repairlens.core import Probe, RepairProblem
    with pytest.raises(ValueError): RepairProblem((1,), (1.,),(3.,),(Probe('bad',-1.,(0,),0),))


def test_cache_requires_matching_input_digest(tmp_path):
    from src.repairlens.artifacts import ArtifactStore
    s=ArtifactStore(tmp_path)
    s.put('x',{'answer':3},'source-v1')
    assert s.get('x','source-v1')=={'answer':3}
    with pytest.raises(ValueError): s.get('x','source-v2')


def test_artifact_snapshot_restoration(tmp_path):
    from src.repairlens.artifacts import ArtifactStore
    s=ArtifactStore(tmp_path/'active')
    s.put('x',{'answer':3},'v1')
    snap=s.snapshot(tmp_path/'snap')
    s.put('x',{'answer':4},'v2')
    s.restore(snap)
    assert s.get('x','v1')=={'answer':3}


def test_cache_detects_content_tamper(tmp_path):
    from src.repairlens.artifacts import ArtifactStore
    s=ArtifactStore(tmp_path)
    s.put('x',{'answer':3},'v1')
    (tmp_path/'x.json').write_text('{}')
    with pytest.raises(ValueError): s.get('x','v1')


def test_actual_replay_completes_and_preserves_prefix(tmp_path):
    from src.repairlens.experiment import make_problem,run_case
    p,truth,meta=make_problem(9,'overlap')
    a,_=run_case(p,truth,meta,'exact',tmp_path/'a')
    b,_=run_case(p,truth,meta,'restart',tmp_path/'b')
    assert a['complete'] and b['complete']
    assert a['initial_digest']==b['initial_digest']


def test_cost_ledger_adds_up(tmp_path):
    from src.repairlens.experiment import make_problem,run_case
    p,truth,meta=make_problem(3,'general')
    a,trace=run_case(p,truth,meta,'exact',tmp_path/'a')
    assert a['cost']==pytest.approx(sum(x['charged'] for x in trace))


def test_productive_artifact_can_change_optimal_first_action():
    from src.repairlens.core import Probe,RepairProblem,RepairSolver
    p=RepairProblem((1,2),(.5,.5),(10.,10.),(
        Probe('inspect',6.,(0,1),0),Probe('refresh-a',10.,(0,1),1)))
    assert RepairSolver(p,True).choose((0,1))==pytest.approx((15.,1))
    assert RepairSolver(p,False).choose((0,1))==pytest.approx((16.,0))


def test_more_valid_cached_artifacts_cannot_increase_optimal_cost():
    from src.repairlens.core import RepairSolver
    p=toy_problem();s=RepairSolver(p)
    assert s.choose((0,1),0)[0]>=s.choose((0,1),1)[0]>=s.choose((0,1),3)[0]
