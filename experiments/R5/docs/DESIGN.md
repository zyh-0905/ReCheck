# R5 task-consequence research design
Approved scope: next round following R4 audit, offline only.
Question: can a calibration-estimated, direction-sensitive joint task-failure model improve quota-constrained refreshing against binary-mismatch and count-mismatch controls?
State: remaining horizon, ages of last exact receipts, cached semantic bit vector, public task class, remaining probe credits.
The scheduler has no access to live rows, realized current modes, final scores, or future task tape.
Calibration uses 64 independent catalogs, each evaluated across every task class and all cached/true semantic combinations. It produces a 5 x 8 x 8 task-failure table.
A disjoint 32-catalog panel measures prediction mismatch; not used to pick methods or thresholds.
Evaluation: four fixed conditions x 16 independent base streams; both packet menus on the identical tape; eight methods; 8 tasks. 8192 rule-executed task-method-menu results, zero LLM.
The primary measured objective is actual binary task failure plus 0.05 times runtime credits. Semantic mismatch count is secondary, never silently substituted.
Model-based forecasts integrate exact observed probe outcomes; they cannot assume that refreshing removes an error while leaving the cached semantic value unchanged.
Tests must catch direction asymmetry, non-additive multi-channel failure, and a fresh channel's observation changing future belief.
Sources and data frozen before computing results. Negative findings retained.

Tie breaking rounds action scores to 12 decimals, then uses fixed action order. Raw probabilities stay recorded. Guarantees are up to floating precision.
single_effect_exact is built from the same complete calibration table to isolate objective structure; no separate cheaper calibration procedure or cost savings are claimed.
