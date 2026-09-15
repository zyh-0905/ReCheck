"""Finite-model evidence refresh. No hidden state or task labels enter a policy.

Exactness is conditional on independent binary symmetric drift, exact refreshes,
additive Hamming decision loss, exogenous Markov tasks, and separable probe costs.
This is not a calibrated safety guarantee for an arbitrary language model.
"""
from dataclasses import dataclass
import numpy as np


def mismatch_probability(age: int, hazard: float) -> float:
    """Probability of an odd number of flips since an exact observation."""
    if not isinstance(age, (int, np.integer)) or age < 0:
        raise ValueError('age must be a nonnegative integer')
    if not np.isfinite(hazard) or not 0 <= hazard <= .5:
        raise ValueError('hazard must lie in [0, 0.5]')
    return float((1. - (1. - 2.*hazard)**age)/2.)


@dataclass(frozen=True)
class RefreshSolution:
    value: np.ndarray
    probe: np.ndarray
    horizon: int

    def action(self, remaining: int, ages: np.ndarray, task: int) -> np.ndarray:
        if not 1 <= remaining <= self.horizon:
            raise ValueError('remaining steps outside planned horizon')
        ages=np.asarray(ages,dtype=int)
        if ages.shape != (self.probe.shape[-1],) or (ages<0).any() or (ages>=self.probe.shape[1]).any():
            raise ValueError('ages outside state space')
        if not 0<=task<self.probe.shape[2]: raise ValueError('invalid task')
        return self.probe[remaining,ages,task,np.arange(len(ages))].copy()


def solve_refresh_dp(weights: np.ndarray, transition: np.ndarray,
                     hazards: np.ndarray, prices: np.ndarray,
                     horizon: int) -> RefreshSolution:
    """Backward induction; arrays indexed [remaining, age, task, channel].

    Channel age is incremented *before* each new task; a current exact refresh
    resets it to zero for the current action and to one for the next task.
    The finite age grid is exact for states reachable from the initial prefix.
    There is no shared hard probe budget or batch setup cost in this model.
    """
    w=np.asarray(weights,dtype=float); p=np.asarray(transition,dtype=float)
    h=np.asarray(hazards,dtype=float); c=np.asarray(prices,dtype=float)
    if w.ndim!=2 or not np.isfinite(w).all() or (w<0).any(): raise ValueError('invalid weights')
    k,d=w.shape
    if p.shape!=(k,k) or not np.isfinite(p).all() or (p<0).any() or not np.allclose(p.sum(1),1):
        raise ValueError('transition must be row stochastic')
    if h.shape!=(d,) or not np.isfinite(h).all() or ((h<0)|(h>.5)).any(): raise ValueError('invalid hazards')
    if c.shape!=(d,) or not np.isfinite(c).all() or (c<=0).any(): raise ValueError('positive prices required')
    if not isinstance(horizon,int) or horizon<1: raise ValueError('positive horizon required')
    amax=horizon+1
    ages=np.arange(amax+1)
    mismatch=(1-(1-2*h[None,:])**ages[:,None])/2
    v=np.zeros((horizon+1,amax+1,k,d))
    probe=np.zeros_like(v,dtype=bool)
    next_age=np.minimum(ages+1,amax)
    for r in range(1,horizon+1):
        future=np.einsum('kl,alj->akj',p,v[r-1],optimize=False)
        keep=w[None,:,:]*mismatch[:,None,:]+future[next_age]
        refresh=c[None,None,:]+future[1][None,:,:]
        take=refresh < keep-1e-12
        v[r]=np.minimum(keep,refresh)
        probe[r]=take
    return RefreshSolution(v,probe,horizon)


def noisy_bayes_update(prior_one: float, observed_bit: int, error: float) -> float:
    """General posterior update used by observation-noise unit diagnostics."""
    if not 0<=prior_one<=1 or not 0<=error<=.5 or observed_bit not in (0,1):
        raise ValueError('invalid binary observation model')
    l1=1-error if observed_bit else error
    l0=error if observed_bit else 1-error
    den=prior_one*l1+(1-prior_one)*l0
    if den==0: raise ValueError('observation outside model support')
    return prior_one*l1/den
