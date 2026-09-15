# User-run LLM pilot implementation plan

Goal: attach real Chat Completions inference to the existing ReCheck finite-model controller and collect a separate RepairLens replay-readiness diagnostic. No external calls are made during development.
Architecture: immutable run manifest; append-only attempt journal; completion cache keyed by logical call identity + exact request hash; trusted local tool environment; offline evaluator; allowlisted result export.
Spec: the two research plans already approved in this conversation; this delivery is a pilot extension, not fulfillment of all paper experiments.

## Scope and evidence boundaries
- ReCheck: original DP imported unchanged; explicit finite-model assumptions retained. Frozen task streams; four policies; one shared initial memory-writing call per stream; two LLM calls per task (plan, answer). New prompts are the same across policies. Exact calibration remains a controlled assumption.
- RepairLens: original shared LLM-produced prefix, full artifact regeneration versus an LLM-selected patch set. This is replay_readiness, NOT RepairLens algorithm performance. No claim of natural failures or arbitrary graph recovery.
- No hidden evaluator outputs are sent to the model, used to retry, or used to stop a run. Output errors remain failures. No arbitrary code from a model is executed.
- No API secret, authorization header, environment dump or local file other than the allowlisted run artifact is exported.
- Hard request-count limit, optional metered spend stop (not a provider-enforced dollar cap), no implicit model substitution, no automatic retries of model answers.

## Tasks and gates
1. Core client and persistence: write tests for strict config, payload parsing, request identity, budget stop, key redaction, and resumability; run failing tests before implementation; implement; rerun.
2. ReCheck adapter: test endpoint semantics, hidden-state separation, identical initial evidence, original DP identity; implement environment and runner; run through a test-only HTTP fixture.
3. Replay readiness: test shared prefix identity, retained artifacts, selective set validation, and offline evaluation; implement and run through fixture.
4. Reporting and packaging: freeze source + config fingerprints; emit per-task and per-attempt records; derive summaries offline; export a complete run including failures but excluding secrets.
5. Delivery: fresh unit/integration suite, CLI help/preflight, offline smoke and pilot execution, source hash audit; clearly label fixture outputs as software tests rather than LLM research.

Execution: inline in the current conversation; separate isolated directory. The user runs the real endpoint calls and returns the generated result ZIP.
