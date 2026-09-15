"""Small explicit statistical utilities; resampling unit chosen by the caller."""
import numpy as np


def paired_interval(a,b,seed=8675309,repeats=3000):
    a=np.asarray(a,float);b=np.asarray(b,float)
    if a.ndim!=1 or a.shape!=b.shape or len(a)<2 or not np.isfinite(a).all() or not np.isfinite(b).all():
        raise ValueError('paired finite vectors with at least two clusters required')
    d=a-b;r=np.random.default_rng(seed)
    samples=d[r.integers(0,len(d),size=(repeats,len(d)))].mean(1)
    lo,hi=np.quantile(samples,[.025,.975])
    return {'n_clusters':len(d),'mean_difference':float(d.mean()),'low':float(lo),'high':float(hi),
            'bootstrap_repeats':repeats,'bootstrap_seed':seed,'interval':'paired percentile bootstrap, descriptive'}


def zero_failure_upper(n,alpha=.05):
    if n<=0 or not 0<alpha<1:raise ValueError('invalid binomial specification')
    return float(1-alpha**(1/n))
