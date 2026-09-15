# Candidate text for a development-study appendix (not a final submission)

## Controlled endpoint study

We evaluated a frozen finite-model refresh controller in a hybrid execution pipeline. A language model compiled a bounded, task-specific plan; SQLite executed the plan, and a deterministic renderer produced the numeric result. Initialization used exact calibration receipts. This differs from the earlier pilot, which used language-model memory writing and a second language-model answer stage. We therefore do not interpret cross-pilot accuracy changes as the causal effect of one prompt or architecture component.

The frozen development design contained sixteen synthetic streams, four per condition, with twelve tasks per stream and two controllers. Only the first 384 model calls contribute to primary outcomes. A further 32 same-input calls are separate diagnostics and never replace primary responses; one call is used for connectivity. The recorded model identifier was `deepseek-flash`, with a 16,384-token output cap, thinking enabled and reasoning effort high, and temperature omitted. These are provider-reported identifiers, not independent weight attestations.

| Condition | ReCheck success | Myopic success | ReCheck proxy objective | Myopic proxy objective |
|---|---:|---:|---:|---:|
| Matched, low persistence | 44/48 | 44/48 | 9.28 | 8.96 |
| Matched, high persistence | 41/48 | 38/48 | 13.40 | 16.00 |
| No drift | 48/48 | 48/48 | 5.60 | 3.20 |
| Underestimated drift | 37/48 | 33/48 | 15.80 | 20.20 |

The proxy objective counts task-relevant binary semantic mismatches and adds stipulated probe costs; it is neither currency nor end-to-end latency. ReCheck improved the observed proxy objective in two conditions and worsened it in two. Across primary method pairs, 45 positions differed in refresh decisions, 21 differed in task-relevant evidence, and these sets overlapped at 11 positions. Ten evidence differences persisted when the current refresh actions were identical, illustrating the carry-over effect of earlier refreshes. Among the 21 evidence-different pairs, only ReCheck succeeded on 12, only Myopic on five, and both failed on four.

Every primary plan was consistent with the supplied evidence. All 51 primary failures occurred with task-relevant stale evidence under this constructed task family. This separation is conditional on the narrow plan contract, exact initialization and deterministic execution. Amounts are nonzero and timestamps densely occupy integer boundary positions, so incorrect relevant semantics necessarily change the answer when the plan follows those semantics. It is not a general theorem that stale memory always causes failure.

All 32 same-input diagnostic pairs produced the same parsed plan and rendered result, but six differed in visible formatting and all differed in completion-token count. Thus no task-level repeat disagreement was observed in this small diagnostic; output variability was not eliminated. The study incurred 97,684 reported input tokens and 78,042 output tokens including diagnostics and connectivity. Monetary cost was not verified.

The experiment is developmental, with four independent streams per condition, known controller dynamics and no external-benchmark claim. We report no confirmatory significance or general superiority claim. The factored dynamic program is a conditional classical reference, not itself a new general algorithmic contribution.
