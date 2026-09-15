# R5 Offline Study Implementation Plan
> Execution: inline, test-first; no external repository writes.
Goal: calibrated task-loss study, source-locked offline reproduction, audited feedback ZIP.
Architecture: original R4 API under vendor/; disjoint calibration and test generation; pure-state belief DP; actual rule execution; independent evaluator; immutable CLI artifact system.
Tech stack: Python 3.11+, NumPy 2.3.5, standard-library filesystem/ZIP/CSV/hash/SQLite-free JSON reference tools.
Spec: docs/DESIGN.md and configs/protocol.json.
Global constraints: 0 LLM/network calls; no keys; never mutate R1-R4 data; no outcome-based seed selection.
Tasks:
1. Tests for calibration table diagonal, directional page loss, train/validation/test ID disjointness.
2. Tests for joint posterior action kernel, exhaustive small-horizon DP, no-probe/free-probe limits, budget rejection.
3. Implement pure calibration/model modules; verify red then green.
4. Test deterministic workflows and independent evaluator agree on all 64 semantic configurations; preserve stale-but-correct cases.
5. Implement source lock, immutable output, no-network guard, run/verify/audit/export workflow.
6. Execute frozen full study, preserving all outcomes; separate cold planning cost from cache lookup and task execution.
7. Independently replay outputs; validate scoring and hard quotas; produce paired descriptive statistics.
8. Fresh extraction test and reproduction; create verified package and Chinese execution prompt.
No automatic scientific pass, billing assertion, background execution promise, or paper submission.

## Execution status
- [x] Modules 1-6 implemented and tested.
- [x] 8192 task records executed; independent replay passed.
- [x] Fixed-policy redundant expansion diagnosed by a failing regression and removed without any changed scientific trajectory.
- [x] Export whitelist, license preservation and finite cost regressions passed.
- [ ] Final fresh extraction and feedback export verification (performed in delivery stage).
