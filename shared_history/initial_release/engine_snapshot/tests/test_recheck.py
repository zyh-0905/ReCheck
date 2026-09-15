import itertools
import numpy as np
import pytest


def test_binary_parity_probability_matches_enumeration():
    from src.recheck.core import mismatch_probability
    for a in range(7):
        for h in [0, .03, .2, .5]:
            exact = sum(h**sum(bits)*(1-h)**(a-sum(bits))
                        for bits in itertools.product([0,1], repeat=a) if sum(bits)%2)
            assert mismatch_probability(a,h) == pytest.approx(exact)


def test_invalid_hazard_rejected():
    from src.recheck.core import mismatch_probability
    with pytest.raises(ValueError): mismatch_probability(3,.8)


def test_one_step_has_correct_price_boundary():
    from src.recheck.core import solve_refresh_dp
    sol = solve_refresh_dp(np.array([[1.]]), np.ones((1,1)), np.array([.1]),np.array([.15]),3)
    assert not sol.probe[1,1,0,0]
    assert sol.probe[1,2,0,0]


def test_finite_horizon_dp_matches_recursive_enumeration():
    from src.recheck.core import solve_refresh_dp, mismatch_probability
    W=np.array([[1.],[.1]])
    P=np.array([[.8,.2],[.4,.6]])
    sol=solve_refresh_dp(W,P,np.array([.13]),np.array([.2]),4)
    def brute(r,a,k):
        if not r: return 0.
        keep=W[k,0]*mismatch_probability(a,.13)+sum(P[k,j]*brute(r-1,a+1,j) for j in range(2))
        refresh=.2+sum(P[k,j]*brute(r-1,1,j) for j in range(2))
        return min(keep,refresh)
    assert sol.value[4,1,0,0] == pytest.approx(brute(4,1,0))


def test_irrelevant_channel_is_never_probed():
    from src.recheck.core import solve_refresh_dp
    sol=solve_refresh_dp(np.zeros((2,1)),np.ones((2,2))/2,np.array([.1]),np.array([.01]),5)
    assert not sol.probe.any()


def test_zero_drift_never_probed_after_exact_prefix():
    from src.recheck.core import solve_refresh_dp
    sol=solve_refresh_dp(np.ones((2,1)),np.ones((2,2))/2,np.zeros(1),np.array([.01]),5)
    assert not sol.probe.any()


def test_bad_transition_rejected():
    from src.recheck.core import solve_refresh_dp
    with pytest.raises(ValueError):
        solve_refresh_dp(np.ones((1,1)),np.array([[.9]]),np.array([.1]),np.array([.1]),3)


def test_sql_probe_and_decoding_all_modes():
    from src.recheck.sql_environment import SQLToolWorld
    with SQLToolWorld(17) as env:
        for unit,end in itertools.product([0,1],repeat=2):
            env.set_modes(unit,end)
            assert env.probe(0)==unit
            assert env.probe(1)==end
            result=env.execute(2,[unit,end])
            assert env.evaluate(2,result)
            assert env.schema_fingerprint()==env.initial_schema_fingerprint


def test_sql_wrong_modes_can_change_result():
    from src.recheck.sql_environment import SQLToolWorld
    with SQLToolWorld(17) as env:
        env.set_modes(1,1)
        assert not env.evaluate(2,env.execute(2,[0,0]))


def test_stream_is_reproducible():
    from src.recheck.experiment import make_stream, model
    w,p,h=model(.04,.8)
    a=make_stream(14,p,h,20); b=make_stream(14,p,h,20)
    assert np.array_equal(a[0],b[0]) and np.array_equal(a[1],b[1])


def test_fresh_relevant_has_no_controlled_errors():
    from src.recheck.experiment import make_stream, model, run_stream
    w,p,h=model(.1,.8); tasks,modes=make_stream(14,p,h,20)
    result,_=run_stream(tasks,modes,w,h,.12,'fresh',None,None)
    assert result['success']==1.
    assert result['task_loss']==0.


def test_policy_does_not_receive_true_modes():
    from src.recheck.core import solve_refresh_dp
    w=np.array([[1.,.2]])
    s=solve_refresh_dp(w,np.ones((1,1)),np.array([.1,.2]),np.array([.1,.1]),4)
    # The only arguments are current task, evidence ages and remaining horizon.
    a=s.action(4,np.array([1,1]),0)
    assert np.array_equal(a,s.action(4,np.array([1,1]),0))


def test_age_threshold_is_monotone_in_finite_model():
    from src.recheck.core import solve_refresh_dp
    rng=np.random.default_rng(727)
    for _ in range(20):
        p=rng.dirichlet(np.ones(3),size=3)
        w=rng.uniform(0,1,(3,2))
        sol=solve_refresh_dp(w,p,rng.uniform(0,.5,2),rng.uniform(.03,.6,2),7)
        assert np.all(np.diff(sol.value,axis=1)>=-1e-12)
        assert np.all(np.diff(sol.probe.astype(int),axis=1)>=0)


def test_future_reuse_can_justify_nonmyopic_refresh():
    from src.recheck.core import solve_refresh_dp,mismatch_probability
    w=np.array([[.35],[.65]]);p=np.array([[0.,1.],[0.,1.]])
    sol=solve_refresh_dp(w,p,np.array([.05]),np.array([.12]),7)
    assert .35*mismatch_probability(5,.05)<.12
    assert sol.probe[2,5,0,0]
    assert sol.value[2,5,0,0]==pytest.approx(.12+.65*.05)
