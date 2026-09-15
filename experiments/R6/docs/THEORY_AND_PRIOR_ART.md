# R6 theory and prior-art boundary

## Object and costs
The known-transition controlled process has cached mode m, age vector a, public task class q and hard refresh quota b. The offline empirical loss L(q,m,z) is estimated only from paid, catalog-level supervised executions. L is a binary *task failure probability*, not the count of stale channels. Data from deployment/evaluation are not fed into L or calibration selection.

Buying only canonical single-flip cells requires 82 labels per catalog; all non-diagonal canonical cells require 182. Five independently executed correct task references per catalog are included in both. Thus for n catalogs, C_single=87n, C_full=187n and C_k=(87+k)n. This accounting uses exact public irrelevant-coordinate equivalences, not a claim about unknown real-world dependencies. Each atom costs n executions. Per-method choices never read unpurchased outcomes.

## Acquisition heuristic
For a fixed grid state s, a feasible refresh action u induces a linear stage-cost vector Q_u(s;L)=c(u)+sum_c X(s,u,c)L_c. Let u0 minimize the current stage cost. For an unmeasured cell c, independently set L_c to v=0 and v=1 and compute
S_c = mean_s max_{v in {0,1}} [Q_{u0}(s;L[c<-v])-min_u Q_u(s;L[c<-v])].
Acquire the largest S_c (ties: rounded 12 decimal places, canonical cell order), pay for actual training executions, update that cell and repeat. This is an immediate-decision stress heuristic. It is NOT the expected value of sample information, not a calibrated posterior and not a guarantee about the full-horizon planner. A fixed 16/32 budget also does not establish optimal stopping.

## Standard loss-approximation bound (not claimed new)
For a fixed policy pi with identical transition/observation dynamics under L and Lhat, let d_pi(c) be its expected number of visits to cell c over H tasks, after the action's actual observation. Probe costs cancel. By linearity and the triangle inequality:
|J_L(pi)-J_Lhat(pi)| <= sum_c d_pi(c)|L_c-Lhat_c|.
For exact optimizers pi* of L and pihat of Lhat, add/subtract J_Lhat(pihat), use optimality, and apply the fixed-policy bound twice:
J_L(pihat)-J_L(pi*) <= B(pihat)+B(pi*) <= 2H ||L-Lhat||_infinity.
These are elementary bounded-loss perturbation consequences, not a new contribution. A nonzero optimization error adds to the right side. The implementation's 12-decimal tie rule is a numerical convention, not an exact-arithmetic theorem. R6 does NOT obtain a uniform bound from its small training sample, and unknown transition/data shift can invalidate the premise.

This explains why reducing prediction error on a rarely used cell may be irrelevant to decisions, while proving neither our selection heuristic optimal nor any benefit in a new environment.

## Amortized break-even, not a measured deployment benefit
For method A vs cheaper-calibrated B, suppose the observed runtime loss reduction is delta=J_B-J_A, additional paid calibration is DeltaC, one calibration workflow has stipulated task-loss equivalent lambda, and N future task streams amortize the model. A improves the stipulated objective only if N*delta>lambda*DeltaC. If delta<=0 and DeltaC>0, no positive N pays it back under those point estimates. This is an accounting identity; estimated delta is uncertain. Cold training, selection and planning times remain separate actual measurements, not hidden inside lambda. The exported sensitivity grid uses fixed N and lambda values, not cherry-picked best ones.

## Prior art explicitly retained
- Javdani et al., Near Optimal Bayesian Active Learning for Decision Making, AISTATS 2014: decision regions and costly information acquisition. https://proceedings.mlr.press/v33/javdani14.html
- Mandi et al., Decision-Focused Learning: Through the Lens of Learning to Rank, ICML 2022: decision quality differs from generic prediction accuracy. https://proceedings.mlr.press/v162/mandi22a.html
- Filstroff et al., Targeted Active Learning for Bayesian Decision-Making, arXiv:2106.04193v2: targeted acquisition about optimal decisions. https://arxiv.org/abs/2106.04193
- Benslimane et al., Decision-Focused On-Policy Learning for Contextual Linear Optimization with Partial Feedback, arXiv:2606.01081 (2026 preprint): adjacent partial-feedback decision learning, not the setting evaluated here. https://arxiv.org/abs/2606.01081

The source check used primary landing pages/abstracts, not an exhaustive full-text novelty review. R6 tests a concrete cost/interaction question; it does not establish that decision-centric acquisition, finite DP or selective calibration is unprecedented.
