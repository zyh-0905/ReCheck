# Technical notes: executed scope, proofs, and information boundaries

These notes accompany two controlled-model papers, not a validation of unrestricted LLM agents. All observations below are either explicitly modeled or produced by the supplied executable workers. Runtime traces are not fabricated model transcripts.

## 1. ReCheck model and proof details

Let evidence channel j be a binary state with independent symmetric flip probability h_j in [0,1/2]. An exact observation resets age to zero. If p(a) is the probability that the cached bit differs from the current state after a transitions, the recursion p(a+1)=h+(1-2h)p(a), p(0)=0, gives p(a)=[1-(1-2h)^a]/2. This is a parity probability; 1-(1-h)^a would instead count at least one change and is not the exact mismatch probability when changes can reverse.

Task k follows a known exogenous Markov matrix P. Loss is sum_j w[k,j] I[cache_j != state_j]. There is no coupling in probe cost and no shared hard resource cap. For r remaining tasks, keeping costs w[k,j]p_j(a)+E_l V[r-1,a+1,l,j], while refreshing costs c_j+E_l V[r-1,1,l,j]. The joint value separates because the action set is a Cartesian product, costs add and future task transitions are unaffected by the actions. Common task randomness does not invalidate additivity of conditional expected value.

Monotonicity follows by induction: p(a) is nondecreasing, the keep value is nondecreasing in a if the previous value is, and the refresh value is constant in a. The minimum remains nondecreasing. With strict-improvement tie handling, the refresh action is an upper age interval. This does not imply a universal scalar threshold across different tasks, finite horizons or channels.

The age array includes a capped final entry for allocation convenience. Exactness claims concern states reachable from the shared startup prefix over the declared horizon; they do not concern arbitrary unreachable age/remaining combinations beyond that horizon. Unit tests compare small reachable problems to brute force and verify monotone actions.

### What the proof does not cover

No unknown hazards, learned transition parameters, adversarial changes, source uncertainty, noise-aware main policy, coupled probes, shared setup costs, coupled task losses, irreversible task effects, or semantic reasoning errors are covered. The XOR example is an out-of-model failure diagnostic. A binary Bayesian noise update function is tested, but this does not mean a noisy-observation main study was performed.

### Estimation and evaluation separation

Controllers receive ages, task identifiers, public loss weights, hazard/transition models and previous paid observations. Hidden true modes generate environment observations and final loss only. Future task realizations are not provided to the planner. Known transition probabilities are a favorable model assumption and are disclosed.

All main policies share the exact initial calibration and pay four startup probes. Main objective J includes these probes; first-run CPU loop time and offline policy-table construction are reported separately. J is not dollars or end-to-end latency. Exact task success requires every positive-weight bit to match; zero-weight task rows are negative controls that naturally pass.

### Executed data inventory

Main: 64 seeds, 3 base hazards, 2 task persistence values, 3 prices, 8 methods, 80 steps = 9,216 runs / 737,280 task-method evaluations. Development: 16 disjoint base seeds, with TTL/mismatch/random parameter grids. Boundary: 32 new seeds, 3 conditions, 4 methods, 80 steps = 384 runs. SQLite: 32 new seeds, 4 methods, 40 steps = 128 runs / 5,120 actual task-method evaluations.

SQLite conventions are amount scale and interval endpoint inclusion. Schema stays unchanged. Public calibration records and boundary records are an intentionally informative observation interface. Data are generated and queries actually executed. The executor is deterministic, not an LLM. This is one additional executable environment, not two independent public benchmarks.

## 2. RepairLens state and exact reference

A candidate hypothesis h includes a required-artifact mask, a prior mass and deterministic outcome predictions for each public probe. It is more than an unlabeled graph. The controller never receives the sampled true index. Although the experiment driver retains truth to instantiate the worker, the policy interface receives only the candidate problem and observed outcome.

State is (B,C,U): retained hypotheses, valid reusable artifacts, and already-used probes. Terminal support-valid repair refreshes union_h D(h) minus C. Common source correction and publication validation do not influence policy choice and are added to every realized cost ledger. Terminal repair is the declared candidate contract, not optimization over arbitrary programs.

For each unused probe u, pay its cost, branch using the prior conditioned on retained support, restrict B to the observed branch and augment C with any validated produced artifacts. Bellman recursion takes the minimum of terminal cost and these branch values. Induction on unused probes proves the exact reference optimal only within this finite model. Positive cost and one-use probes ensure termination. Two-step rollout has no claimed approximation ratio.

A probe that neither refines support nor produces a new artifact is dominated. Conversely, a probe that produces an artifact can be useful even if its information gain is small. Two equal-prior hypotheses requiring A or B, both with repair cost 10, illustrate this: diagnostic-only identification at cost 6 leads to total16; productive refresh of A at cost10 leads to expectation15. Discarding diagnostic products changes the optimum back to diagnostic-first. This is a test fixture, not a general novelty proof.

### Why nuisance hypotheses are retained

Different provenance routes can require the same repair. Full identification of n individually observable route bits needs n observations in the worst case; repair can stop immediately if the damage set is already common. This is a constructed separation. It is not a log(number of repair classes) theorem. In the coupled family, inspection bits are XOR-coded with a route bit, so discarding route distinctions before interpreting observations would be wrong.

### Execution and storage

There are three synthetic 64-point signals. Workers actually calculate means, RMS values and rFFT DC magnitude and write JSON. Changing source0 to source1 changes only selected worker inputs. Route variations are constructed nuisance provenance or inspection encodings; they are not discovered real application paths.

Identical prefixes are reconstructed and their byte digests compared. Each artifact has a payload checksum and an input-scope digest; snapshots and restoration are unit tested. Publication under a new scope is allowed only when refreshed or declared independent by retained hypotheses. Checksums detect accidental corruption, not malicious hosts or authenticated origin. No external side effects or process-wide checkpoint claims are made.

Nonproductive inspections may execute internal worker comparisons. They do not enter the reusable artifact count, but have declared costs and their CPU time is included. The materialized-block count is therefore not a count of every NumPy computation.

### Main, stress and validation

Primary: 20 independently generated cases in each of six fixed families, 11 methods, 1,320 actual workflow runs. The true behavior is sampled from the supplied prior and belongs to the family by construction. The study evaluates decision algorithms with known behavior families; it does not train a provenance extractor. Priors are not learned from data.

Stress: 60 new general-family cases, paired complete-support and all-true-mask-hypotheses-removed configurations, 120 runs. Omission is deliberately100%, not a natural prevalence estimate. An empty posterior triggers full fallback, but compatible incorrect support can still cause failure.

After policy stopping, evaluation checks block0 for current output, all three blocks for persistent state, and two aggregate contracts. The source code comment refers generically to fixed downstream contracts; there are precisely two aggregate follow-up checks (sum of means and weighted RMS), in addition to current/state checks. They are mathematically derived from the same data, not independent unseen tasks. They are not exposed as adaptive search feedback.

## 3. Statistical protocol

Main hypotheses and data generators were locally frozen before main execution; source hashes in configs/frozen_protocol.json check that policies were not tuned after test outcomes. This is not external preregistration and does not establish statistical power.

ReCheck uses common base random seeds across rates, task regimes, prices and methods. Accordingly, the independent unit for pooled comparisons is the base seed, giving 64 clusters. The original written within-regime bootstrap choice was corrected before computing intervals; see ANALYSIS_AMENDMENT.md. This avoids counting coupled regimes as independent.

RepairLens uses the workflow instance within each fixed family. Resampling is paired across methods and stratified within family, with equal family weights. 3,000 percentile bootstrap replicates give descriptive95% intervals conditional on these generators. Numerous reported contrasts are not familywise-confirmed hypothesis tests. SQL uses32 independent seed clusters.

A full deterministic rerun checks scientific CSV columns to tight numerical tolerances and compares event ledgers. Measured timing is excluded from equality because repeated wall times are inherently variable. Reproduction does not increase sample size and does not substitute for independent replication.

## 4. Cost interpretation

ReCheck J prices semantic mismatches and probes in assigned units. Its paper separately reports first-run loop time and table construction. Those compute costs are not silently converted into a claimed real deployment cost.

RepairLens assigned cost includes each probe, noncached final repair, common source correction, and publication validation exactly once. Assigned prices can differ from measured local worker latency. Repair-phase timing excludes the identical common prefix and final hidden evaluation; planning and execution are measured separately. Directly comparing their sum shows both planning methods slower locally than restart.

The sensitivity plot T_m(tau)=mean_planning_ms + tau*mean_assigned_cost_m describes a hypothetical latency conversion. Its crossing points are algebraic scenario analysis, not measurements on expensive services. An application needs independently measured operation latencies to validate this model.

## 5. Next experiment gate

ReCheck needs independently estimated drift/task models, real natural-language task interpretation and an external tool benchmark; RepairLens needs expensive independently specified workers, credible candidate coverage and natural failures. Both require strong nearest-method reproduction and independent human checks. Merely adding more synthetic seeds cannot discharge these obligations.
