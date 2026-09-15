import numpy as np
import pytest


def test_paired_bootstrap_constant_difference():
    from src.common.stats import paired_interval
    out=paired_interval(np.arange(8.),np.arange(8.)+2,seed=4,repeats=500)
    assert out['mean_difference']==pytest.approx(-2)
    assert out['low']==pytest.approx(-2)
    assert out['high']==pytest.approx(-2)


def test_binomial_zero_failure_bound():
    from src.common.stats import zero_failure_upper
    assert zero_failure_upper(120)==pytest.approx(1-.05**(1/120))


def test_nonfinite_metric_rejected():
    from src.common.stats import paired_interval
    with pytest.raises(ValueError):paired_interval([1,float('nan')],[0,0])
