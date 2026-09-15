# ReCheck / RepairLens Implementation Plan

> Execution: inline, in the isolated research/controlled-study branch. User has authorized implementation.

**Goal:** Execute the locally feasible, controlled-model portion of the supplied plans and generate two truthful ICASSP-format research drafts with actual measurements.
**Architecture:** Two independent Python packages, shared statistical reporting, immutable protocol, raw trial records, source-derived LaTeX tables. Policies never receive hidden evaluator state.
**Tech Stack:** Python, NumPy, SciPy, SQLite, pytest, matplotlib, pdfLaTeX; ICASSP 2027 spconf executable definitions and an in-document numbered bibliography (no IEEEbib download).
**Specs:** original_plans/01_ReCheck_research_plan.md and original_plans/02_RepairLens_research_plan.md.

## Global constraints
- No invented LLM runs, no invented human audits, no claimed SOTA or completed external-benchmark validation.
- Generated instances are controlled synthetic experiments; executable SQL/files do not turn them into natural agent failures.
- No external submission, registration, paid API calls or repository writes.
- Main numerical tables must be generated from experiment output; complete traces and seeds retained.
- Author identities/affiliations are not supplied. Drafts will explicitly require this before submission (ICASSP is not blind).
- Official author guidelines require disclosure of generated text, code and figures; place disclosure within the technical-page budget.

## Task 1: ReCheck mathematical core
Files: src/recheck/core.py, tests/test_recheck.py.
Interfaces: mismatch_probability(age,hazard), solve_refresh_dp(weights,transition,hazards,prices,horizon).
- [x] Write tests for parity probability, brute-force equivalence, irrelevant-task behavior, probability validation.
- [x] Run `pytest tests/test_recheck.py -q` and retain red log.
- [x] Implement exact factorized finite-horizon controller for explicitly independent binary modes, exact observations and additive task loss.
- [x] Run tests; record all scope restrictions.

## Task 2: ReCheck experiment and SQL adapter
Files: src/recheck/experiment.py, src/recheck/sql_environment.py.
- [x] Write tests for actual SQL receipt interpretation and hidden-state-independent policy selection.
- [x] Implement fixed-seed task streams; fit TTL/entropy thresholds on disjoint development streams; freeze main protocol.
- [x] Run main and boundary conditions, report loss-plus-probe cost AND measured CPU/SQL timings. Do not claim real-world dollar savings.

## Task 3: RepairLens core and exact reference
Files: src/repairlens/core.py, tests/test_repairlens.py.
Interfaces: RepairProblem, Probe, terminal_cost(problem,support,cached), RepairSolver.choose(support,cached,used).
- [x] Write tests for robust terminal repair, productive cache reuse, cost conservation, nonempty support, a hand-computed optimal policy.
- [x] Implement finite-hypothesis dynamic programming, depth-limited policies and information-based baselines.
- [x] Prove the exact recurrence only for its declared deterministic finite family; no universal recovery claim.

## Task 4: RepairLens actual artifact replay
Files: src/repairlens/experiment.py, src/repairlens/artifacts.py.
- [x] Test snapshot restoration and content/version-bound cache reuse.
- [x] Execute all methods from byte-identical input snapshots; keep downstream evaluation outside the controller.
- [x] Run complete-state and two same-workflow derived follow-up checks after stopping; include missing-true-hypothesis stress test. Independent unseen follow-up tasks remain unexecuted.

## Task 5: Reporting and manuscripts
Files: scripts/make_report.py, scripts/audit.py, papers/*/main.tex, docs/STATUS_AND_REVIEW_ZH.md.
- [x] Use paired independent-base-seed/instance resampling (see separate analysis amendment). Label bootstrap uncertainty conditional on the generator.
- [x] Generate one chart per figure, vector PDF and PNG; matplotlib default colors and distinct markers.
- [ ] Download a byte-identical official 2027 template archive. Direct download failed; executable style definitions were transcribed from official web text, with local SHA and disclosure. No upstream byte hash is claimed.
- [x] Write two bounded-scope papers and extended proof/protocol notes.
- [x] Compile, inspect every page, audit fonts/page geometry/citations/numerical agreement; label scientific gaps separately from formatting.

## Completion boundary

Checkboxes above refer to the scoped controlled implementation, not every requirement of the original research plans. Full same-environment replication passed; the checkpoint is not independent peer review. Real LLM inference, natural failures, public benchmarks, three-model evaluation, author identity and official submission are NOT completed. See STATUS_AND_REVIEW_ZH.md for requirement-by-requirement gaps.
