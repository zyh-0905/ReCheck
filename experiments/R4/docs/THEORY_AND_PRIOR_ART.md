# R4 theory, algorithm status, and prior-art boundary

## Exact finite problem
At a decision epoch, state is (h, a, q, b): remaining task rounds, ages of three last-verified binary semantics, current public task type, and remaining integer probe credits. A probe packet e reveals a fixed subset S_e with cost c_e. A batch U is admissible only if sum(c_e) <= min(b, per_round_cap). The covered channels are the union, not a sum with duplicates. Singleton cost is 2; overlapping pair packets cost 3. Observations are exact; channels flip independently and symmetrically with assumed hazard h_j <= 1/2.

The mismatch probability of the last observation at age a is p_j(a)=[1-(1-2h_j)^a]/2. This requires the symmetric Markov and exact observation assumptions. It is not an open-world confidence bound.

With a^U_j=0 if covered and a_j otherwise, the recurrence is:

V_h(a,q,b) = min_U {lambda*cost(U) + sum_j w_qj p_j(a^U_j)
  + sum_q' P(q'|q) V_(h-1)(a^U+1,q',b-cost(U))}; V_0=0.

`recheck_joint` solves this finite recurrence exactly. In this narrow model observations' values do not affect the mismatch loss, and actions do not change task transitions; hence an age-only state is sufficient. Correlated/asymmetric dynamics, uncertain probes, meaningful task-output feedback and unknown model fitting are NOT covered. The integer budget is enforced by the environment; lambda is an extra loss trade-off, not a substitute for the hard constraint.

## Compared policies
- `recheck_joint`: exact finite known-model reference, not a novel general solution or a scalable deployment claim.
- `bundle_rollout`: two-step Bellman lookahead followed by the exact expected cost of `age_paced`; replan after each epoch. This is conventional base-policy rollout, not a new general algorithm. Tail computation is not free; record actual per-method runtime using independent caches. Its tiny-model efficiency must be measured rather than asserted.
- `bundle_myopic`: exact enumeration of all affordable packet subsets for current loss plus lambda cost; it gets the SAME catalogue and hard budget, not singleton-only tools.
- `age_paced`: frozen budget-paced weighted-age heuristic; waits for an age threshold ceil(2h/b), then chooses weighted covered age per packet credit. It is not a reproduction of an optimal AoI or Whittle-index algorithm.
- `separable_projected`: offline-only relaxed individual-channel continuation values projected onto the same feasible bundle catalogue. It ignores future joint budget coupling; not a faithful native R3 comparator since the objective/constraints have changed.
- `never`: offline no-maintenance lower-cost/negative control.

## What is proved, and what is not
The Bellman reference is optimal ONLY for the specified finite model and admissible catalogue. The argument is standard backward induction. Hard-budget feasibility follows by admission-before-query and exact credit subtraction. Neither is claimed as a novel theorem.

For a fixed feasible base policy pi, let W be its exact finite-horizon value. One-step Bellman minimization T W <= W because the base action remains admissible. Monotonicity of T implies T^2 W <= T W. Repeated two-step lookahead with an exact base tail is no worse than the base under this model: at the next state its reoptimized value is no higher than the one-step improvement tail used in the current evaluation. This statement needs exact expectations/feasible candidates and does not carry to fitted models automatically. Small exhaustive tests corroborate the implementation, not a new theorem or a formal proof checker.

A basic coupling witness: three individually preferred singleton probes cost 6, violating a per-round cap of 4. Two singleton probes covering {0,1} cost 4, whereas a {0,1} packet costs 3. Thus factorized decisions must be reconciled with joint feasibility and union coverage. This is a witness to a changed problem, not a new complexity result. Generalized one-step selection includes weighted budgeted maximum coverage; do NOT claim a generic greedy approximation guarantee without matching the published assumptions and algorithm.

## Primary literature checked on 2026-09-12
1. V. Tripathi and E. Modiano, Optimizing Age of Information with Correlated Sources. MobiHoc 2022; extended IEEE/ACM Transactions on Networking article 2024. https://arxiv.org/abs/2208.01738 ; https://doi.org/10.1109/TNET.2024.3427658
   Shared/correlated observations, scheduling, and unknown-correlation adaptation already exist. Simply renaming these as memory probing is not sufficient novelty.
2. S. Khuller, A. Moss, J. Naor, The Budgeted Maximum Coverage Problem. Information Processing Letters 70(1), 39-45, 1999. https://doi.org/10.1016/S0020-0190(99)00031-9
   R4's current-stage coverage objective has this established combinatorial lineage.
3. DeepSeek official thinking-mode documentation: https://api-docs.deepseek.com/guides/thinking_mode/
   Parameter form was checked, but the live model ID is kept from the user's previously successful frozen runs. No remote model/weight identity or current pricing is certified here.

## Publication gate
R4 is a scoped mechanism extension plus a SECOND SELF-CREATED executable environment, not a public external benchmark. It does not close the original paper's unknown-model, generalization, native strong-baseline, human-review, or originality gaps. If a same-input deterministic compiler is equally good and cheaper, keep that result; do not manufacture a need for the LLM. If rollout savings disappear after planning/validation cost, stop enlarging this setup and revise the scientific object before more paid calls.
