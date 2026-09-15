# R5 development-study text (not a replacement for the paper's main experiments)

## Calibrated task-consequence model
We replaced channel-wise semantic mismatch penalties with an empirical task-failure
kernel indexed by public task class, cached interface semantics, and hypothetical
current semantics. The kernel was estimated on 64 independent synthetic catalogs.
A further 32 catalogs were used only for diagnostic evaluation; no validation or test
outcomes entered online action selection. The controller retained known symmetric
semantic-transition rates and idealized calibration probes. Its state included the
last observed semantic values in addition to receipt ages, since the consequences
of a stale pagination convention can be asymmetric.

## Rule-executed paired evaluation
We evaluated four fixed conditions with 16 independently generated base streams per
condition. Each eight-task stream was replayed under both singleton-only and shared
probe menus with identical task, catalog, and semantic-transition tapes. Eight
policies yielded 1,024 policy trajectories and 8,192 rule-executed task outcomes.
These are not LLM experiments. Statistical resampling uses base streams, retaining
the paired menu and policy observations together.

Under the shared menu, the learned full-kernel exact policy achieved 98/128,
128/128, 92/128, and 109/128 successes in the matched, no-drift, faster-drift,
and catalog-shift conditions, respectively. Its measured task-failure-plus-credit
costs were 36.30, 6.15, 41.95, and 24.90. The binary-any-mismatch exact baseline
obtained 96/128, 128/128, 91/128, and 106/128, with costs 38.25, 6.30, 43.40,
and 28.25. Descriptive paired intervals for the main nonzero-drift contrasts
include zero. A single-flip noisy-OR kernel matched or closely approached the
full model and performed better under catalog shift (111/128; cost 23.00).
Thus the study does not establish that fitting all joint consequences is
preferable to a simpler direction-sensitive model.

## Limits
The calibration/validation mean absolute table difference was 0.01738, with maximum
difference 0.203125. Neither quantity certifies population risk, and the catalog-shift
condition violates the calibration distribution. The no-drift controller still
spent credits, whereas never refreshing achieved zero task loss and zero runtime
probe cost. Scheduling and loss learning therefore remain conditional tools rather
than universal improvements. Cold planning measurements cover only three semantic
channels and horizons up to eight; all compilation and calibration costs must be
reported separately from online lookup. Classical Bellman planning and the
bounded-reward perturbation argument are used as reference analyses, not claimed
as novel general theorems.
