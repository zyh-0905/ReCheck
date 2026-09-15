# R4 controlled-study manuscript material — audited, not submission-ready

## Shared calibration packets under a finite quota

We conducted a controlled development study using a local catalogue–inventory API, not a public agent benchmark or a production service. Three binary interface conventions govern page indexing, active-item status and gross versus net inventory. Singleton calibration packets consume two credits and selected two-channel packets consume three. All methods face an eight-credit episode budget and a four-credit per-round limit. A common exact initialization costs six equivalent credits outside the runtime budget. Calibration observations are idealized simulator fixtures; task-tool feedback does not update the scheduler's beliefs in this experiment.

Twelve fixed streams, with three streams in each of four conditions, contain eight tasks each. Four schedulers receive identical resources: an exact joint finite-model reference, a two-step rollout policy with an age-paced tail, a bundle-aware myopic policy and an age-paced baseline. An LLM compiles a public request and cached evidence into a bounded plan; a deterministic executor performs pagination, joins and aggregation. There are 384 primary calls, 24 separate same-input repeat diagnostics and one connectivity check. Repeats do not replace primary outputs, consume additional probe credits or alter subsequent state.

| Condition | Joint | Rollout | Myopic | Age-paced |
|---|---:|---:|---:|---:|
| Overlapping packets, matched drift | 20/24 | 22/24 | 18/24 | 18/24 |
| Singleton packets, matched drift | 13/24 | 13/24 | 12/24 | 12/24 |
| Overlapping packets, no actual drift | 24/24 | 24/24 | 24/24 | 24/24 |
| Overlapping packets, underestimated drift | 15/24 | 17/24 | 14/24 | 16/24 |

Aggregated for description only, success was 72/96, 76/96, 68/96 and 70/96 respectively. The proxy objective, defined as the number of relevant semantic mismatches plus 0.05 times probe credits, was 31.65, 27.70, 38.75 and 36.65. This objective is neither monetary cost nor task-error count. The exact method minimizes an expectation under the supplied model; its finite-sample task performance need not dominate rollout. Rollout's four net additional successes over the joint reference were concentrated in two streams. We do not report confirmatory significance from the three streams per condition.

All 384 parsed primary plans equaled those from a deterministic compiler given the same public input. The rule compiler consequently reproduced every functional result, establishing no incremental LLM benefit in this narrow interface. Of 101 stale-evidence records, 98 failed and three succeeded; 283 fresh-evidence records succeeded. The three stale successes skipped the first page but omitted only items excluded by the final category or availability filter. They did not retrieve the same catalogue rows. Thus semantic mismatch is not equivalent to task loss.

The 24 repeated requests produced identical visible text, parsed plans and task outputs, while their returned reasoning strings and completion-token counts differed in every pair. This is limited functional repeat consistency, not proof of zero stochasticity. Measured selector time totalled 0.966 s for the joint reference and 0.242 s for rollout, versus 0.00341 s for myopic; these timers exclude some construction and orchestration overhead. Credits, token counts and latency are reported separately, with no currency-savings claim.

## Post-hoc mechanism diagnostic — separate from the LLM table

Because the original overlapping and singleton groups use different streams, their score difference does not isolate packet sharing. After inspecting R4, we reran all twelve streams using the rule compiler, holding canonical data, task sequence, hidden changes and budgets fixed and changing only packet availability. With shared versus singleton packets, joint scheduling achieved 73 versus 71 correct tasks out of 96, rollout 79 versus 73, myopic 68 versus 68 and age-paced 75 versus 74. These are post-hoc rule-counterfactual results, not additional model responses, an independent test set or replacements for the primary scores. Some individual trajectories still favored singleton policies.

The evidence supports a conditional mechanism study and motivates task-loss-aware, scalable scheduling evaluation. It does not establish a novel general scheduling theorem, unknown-drift learning, public-benchmark generalization, LLM necessity or publication readiness.
