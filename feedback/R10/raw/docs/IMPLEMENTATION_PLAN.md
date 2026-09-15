# R10 target re-resolution × minimal writes: implementation plan

Status: execution of user-approved next-stage diagnostics, not a claimed new optimizer.

Goal: separate whether an action updates the currently requested object, whether it overwrites protected state, and whether readback actually verifies user intent. Use a different executable substrate (file-backed SQLite, two real connections) from the preceding ToolSandbox extension. This is a constructed local workflow, not a public benchmark or natural production incident.

Architecture: frozen task definitions → six whitelisted native tools → database transaction → append-only before/after/receipt journal. Environment changes use a separate SQLite connection once after the first qualifying read, including within a returned batch. No direct SQL, file access, model explanation, or hidden oracle may become a tool action. Reuse the previously qualified native API client/parser; no new remote request is sent on the research side.

Scope: two task families (service→profile join, eligibility/priority-based dispatch selection); twelve cells include stable, irrelevant, protected-field-only, selection-only, and literal-ID controls. Four language-instruction arms are a 2×2 diagnostic (generic vs intent-grounded verification, usual vs explicitly minimal writes). Do not force the baseline to submit stale fields. All arms get identical tools including optional version/selection preconditions. Strong scripted precondition/re-resolution baselines precede any paid run.

Global constraints: Python >=3.11; only standard library; 48 primary episodes, no extra repetitions; 8 model requests/episode; 4 native calls/response; 32 tools/episode; maximum384 model attempts and1536 native actions; no smoke, user-simulator or judge; first response binds metadata; amounts UNKNOWN. Frozen source/config/task hashes. Invalid output retained then stop; business conflicts return as tools; no automatic network retries/resumption. A success in software tests is not a model result.

Tasks:
- [x] Test native operations and injected histories, then implement two-connection SQLite engine.
- [x] Test independent state/trajectory evaluation, including no-op errors and misbinding despite correct row version.
- [x] Execute all 12 cells with fixed scripted baselines; retain all negative and literal-ID controls.
- [x] Test single-response multi-tool order, truthful results, bounds, pause/no-resampling and replay.
- [x] Run full-loop local HTTP fixtures and fresh-package replay; no actual paid API.
- [x] Freeze the handoff, paper protocol, literature boundaries and complete deliverable verification.

No change to R1–R9NT1 records, no thesis claim that final-state evaluation missed R9NT1 errors, no promotion of classical patch/CAS/requery into a novel method. R10 is prospective relative to its new model outputs, but designed using earlier results; not external preregistration. Script repetitions are not independent samples.

Execution completion record: core and evaluation tests, both offline runs, and rule/cap/late-bad/prose HTTP fixtures completed. Final deliverable fresh checks and immutable input hashes are recorded outside the source tree in R10_Delivery_Verification.json; any failure is retained, not retroactively hidden.
