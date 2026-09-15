# R10 manuscript insert: equal task outcomes under shared conditional-update capabilities

**Status:** audited development diagnostic, not a new method-success claim. These
results do not replace the earlier ToolSandbox data. No model was queried during
this review.

## Protocol and recorded results

R10 evaluated one endpoint configuration on 12 constructed file-backed SQLite
cases spanning service-to-configuration routing and ranked eligible-batch
selection. Four guidance conditions (generic, minimal-update, intent-based
verification, and both) shared the same documented read/update tools, optional row
version preconditions, optional selection preconditions, and eight-request cap.
There were 48 primary episodes and no extra repeats. State updates were injected
once after the first eligible read; all 40 scheduled updates were exposed, and the
eight stable episodes had no update.

Every condition achieved 12/12 final-goal, final-business-state, and trace-safe
success. All episodes terminated with a recorded completion assessment. The 237
model requests contained 262 native calls: 144 reads, 70 update attempts, and 48
terminal reporting calls. Only 48 update attempts committed; 22 were rejected
without changing state (14 row-version conflicts and eight selection conflicts).
The terminal reporting tool records the agent's assessment and does not consult
the private evaluator.

| Guidance | Safe episodes | Model requests | Database calls | Conflicts | Input tokens | Output tokens |
|---|---:|---:|---:|---:|---:|---:|
| Generic | 12/12 | 58 | 52 | 5 | 109,786 | 13,598 |
| Minimal | 12/12 | 60 | 52 | 6 | 116,264 | 11,177 |
| Intent | 12/12 | 58 | 54 | 5 | 112,662 | 12,280 |
| Both | 12/12 | 61 | 56 | 6 | 124,960 | 12,624 |

## Behavior and guard scope

All 70 update attempts submitted only the requested business field, and all used
at least one optional precondition. The generic agent was not forced to copy old
fields and already adopted minimal updates. All current-selection episodes used
selection checks; literal-ID episodes retained the specified ID and used row
checks instead. Thus the factorial prompt assignments did not induce exclusive
behavioral categories, and their equal task outcomes provide no evidence of an
incremental correctness benefit from the added guidance. They do not establish
statistical equivalence either.

In eight observed proposals, the route or ranking changed without changing the
old selected row's version. The agent attempted the old target with a stale
selection token; the database rejected the attempt, after which the agent
re-queried and completed the task. Consequently, zero committed wrong writes does
not mean zero wrong-target proposals. The success belongs to the combined agent
and documented conditional-update environment, rather than an unaided ability to
avoid every stale proposal.

## Separate retrospective checks

For each rejected attempt, we replayed its recorded prefix offline and omitted
only the failed precondition. All 14 row-conflict branches still made a permitted
minimal business update in their actual prestates; all eight selection-conflict
branches updated the wrong current target. These are local transition checks,
not live-agent continuations or a no-guard policy evaluation. They show why a
rejection count alone is not a count of prevented business errors. No general
recommendation to remove row checks follows.

The frozen false-completion endpoint was zero because all declared completions
were trace-safe. It does not score every narrative detail. Two targeted checks
found a wrong stated pre-update value (2 rather than 3) and an incorrect claim
that the ranked winner was the only eligible row. The successful database
outcomes remain unchanged; these posthoc observations are not a newly selected
primary endpoint or an estimated narrative-error rate.

## Limits and research decision

This is a one-endpoint, two-template constructed diagnostic, not a public
benchmark or an independent sample of production incidents. The shared prompt
and tool documentation explicitly explain staleness, omitted-field preservation,
and the limits of row-only validation. Conditional selection checks are available
to every arm; their mechanism is not claimed novel. Different capabilities and
tasks prevent a single-factor causal comparison with R9NT1. No final-state versus
trace-safe disagreement was observed here, and no added guidance demonstrated a
correctness gain. The evidence supports retaining the strong simple control and
ending same-template expansion, not claiming a new ReCheck method or transferring
these data to RepairLens.
