# R6 design: paid interaction calibration, not another LLM prompt test
## Scientific questions and authorized scope
R5 used a full label tensor to construct its purported cheap single-effect model. R6 makes label acquisition explicit. Each training panel has independent catalogs; learners query only registered labels. Reference answers and changed-workflow executions are charged separately. No model endpoint exists. User has approved continuing the previous proposed calibration-cost experiment.

## Alternatives and choice
1. Buy every interaction: model-rich reference, cost-heavy.
2. Buy only single-flip effects, extend by noisy OR: economical strong baseline.
3. Buy selected multi-flip cells: random, current-policy occupancy, or immediate-decision stress sensitivity. This is the chosen comparison, not a presumption that method 3 wins.

## Data units
4 training panels of 16 catalogs. Per panel, 4 environment conditions times 8 new independent streams of 8 tasks. Both probe menus use each same private stream. Selectors never receive evaluation data. At public-irrelevant coordinates the tensor uses symmetry implied by the bounded API. Diagonal risk is structurally zero. There are 82 canonical single-flip cells and 100 interaction cells; costs will be checked, not silently assumed.

## Selection
Each atom is one canonical (q, cached, true) cell measured on all 16 training catalogs. All atoms cost 16 executions. Build a fixed grid of hypothetical public beliefs/ages/budgets. Current-policy occupancy ranks how often a cell affects the selected action. Decision sensitivity replaces one unmeasured cell by 0 and by 1 and scores the maximum immediate regret of retaining the current best action, averaged on the grid. These endpoints are stress tests, not Bayesian draws/confidence limits. Recompute after each acquisition; use first 16 and first 32 of the same stream, never later labels in the earlier checkpoint.

## Audit and measurement
Raw artifacts, code, protocol: byte hashes. Discrete science: exact values/types. Only records[*].predicted_task_error_after_receipts: finite [0,1], absolute 1e-14, relative 0. Timing is excluded from scientific equality but retained. Solver tie policy remains R5 round-to-12 digits; do not change after observing outcomes. Independent scoring verifies actual tool outputs; ledger query counts match executed results. Cross-machine reproduction adds no sample.

## Contribution boundary
This studies actual calibration cost and decision-sensitive acquisition under shared refresh constraints. General decision-focused learning, active information acquisition and finite DP are prior art. Fixed scenarios, given drift, controlled tasks and small semantic dimension remain. No monetary savings, no real-agent generalization, no accepted-paper claim.
