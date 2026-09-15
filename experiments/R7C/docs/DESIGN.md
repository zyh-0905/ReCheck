# R7C live-agent problem diagnosis (development protocol)

Approved scope: continue R7 external execution diagnosis; assistant does offline work,
user only performs genuine charged model requests. No R1-R6 resampling.

Question: Does historical evidence induce stale-entity/state errors in a bounded,
natural-language, native ToolSandbox tool loop, and how much can a simple
verify-before-write instruction recover relative to neutral memory and no-memory?
No newly named optimal method. No official ToolSandbox leaderboard claim.

24 constructed extensions = 4 goal families x 6 paired state/observation conditions.
Families: named-recipient message, literal-phone message, named reminder retime,
Wi-Fi state dependency. Conditions: stable, irrelevant change, relevant change,
post-change observation, pre-change observation, explicit error. Changes are made
before the actor starts; no unannounced mid-action race. All arms share the exact
frozen post-change snapshot, task text and ordinary observation; no-memory omits
only the old persistent-memory block. Safe goal completion includes final state and
all intermediate writes; reporting/termination and budget exhaustion are separate.

3 arms: no_memory, memory_standard, memory_verify. Max 6 model decisions per episode,
24*3*6=432 main attempts + one smoke = 433. Actual early completion reduces calls;
never pad, best-of-N or retry. Fixed per-case cyclic arm ordering from seed 701301.
No LLM user simulator or judge. Non-streaming stateless decision-per-step JSON API;
previous actions/observations included in each fresh user payload. System prompt,
tool docs, prompt variants and task generation frozen and hashed before requests.

Native upstream functions/decorators/Polars context unchanged, pinned to commit
c8571d7854316d2e1c5f288e59fe1e34e53f6dd1. Our allowlisted direct dispatcher replaces
InteractiveConsole/Scenario.play. No exec/eval or native external search tools.
Only synthetic contacts/reminders/messages. Do not connect real user services.
Native results UUID/time preserved; audit replay controls only these nondeterministic
outputs using the actual recorded values. No goal labels or current private state
enters actor payloads. The fixture generator and final checker can see private state.

Before paid run: offline scripted policies, no-write/wrong-write and malicious
argument tests, frozen snapshots, full network-fixture loop, offline reconstruction,
source/budget/identity checks, fresh extracted package tests. Raw failures retained.
All non-provider code tested here; no human peer-review claim, no paid responses yet.
