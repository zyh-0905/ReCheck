# R8A: evidence consolidation and check/use boundary (development)
Frozen design: 2026-09-13. Prior R7C1 outcomes already inspected; this is a NEW
researcher-constructed execution-contract study, not preregistration or a new LLM test.
No remote model calls. Historical raw responses and their scores stay unchanged.

Question: does correctly refreshing an object binding imply validity at use time?
Prior art explicitly includes TOCTOU, HTTP conditional requests, and tool fusion.
We test established execution contracts, not a proposed novel agent algorithm.

Native backend: ToolSandbox c8571d7854316d2e1c5f288e59fe1e34e53f6dd1 with R7C1 bridge.
Three intent templates: current-person phone, literal phone, current-description reminder.
Four perturbation kinds: none; unrelated contact update; relevant binding replacement;
non-binding target-field update (relationship or reminder location).
None has one timing; all other events have before_resolve / after_resolve / after_use.
This is 30 constructed intent/event/timing cells. Four execution contracts per cell:
1 query_use: query then execute; 2 global_guard: atomically compare whole world snapshot
then execute or reject; 3 scoped_guard: atomically recheck just intent binding then execute
or reject; 4 scoped_retry1: same scoped contract with at most one re-resolve after rejection.
Total 120 native scripted trajectories. No independent-sampling claims or p-values.

We schedule changes deterministically between operations; there are no uncontrolled
concurrent threads. Atomic means the stipulated check/write segment cannot interleave
with the cooperating event scheduler; this is NOT a guarantee of remote API atomicity.
Guard options are extra environment capabilities. Their results must not be presented
as an equal-tool-budget superiority test against unguarded agents.
Current-at-commit is the success convention; changes after a correct committed write
must not retroactively make it wrong. All writes are scored, not only final state.
Rejecting everything gives zero wrong writes but zero completion, not full success.

Full snapshots, native calls, admin interventions, event order, rejection and completion
are retained. Main totals are separate from counterexamples / software tests. Arbitrary
LLM-generated code, real SMS, production accounts and external requests are not used.
Times are descriptive only. Query counts include guarded rechecks and retry resolution;
whole-state token issuance/validation and preparation/admin work are separate counters.

Analysis: report all event cells, success/wrong-write/reject counts and actual tool calls;
compare global-versus-scoped rejection under irrelevant changes. Any zero-error result
is limited to coverage of the declared synthetic interleavings and binding predicates.
Do not call it a fresh paid-model trajectory, post-change model recovery, a new theory,
public benchmark score, general safety guarantee or publication readiness.
