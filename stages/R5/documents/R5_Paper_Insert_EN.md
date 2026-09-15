# R5 appendix material — verified offline reproduction

Status: Development evidence only; not a new independent test sample, an LLM experiment, or a claim of methodological novelty.

## Reproducibility and numerical auditing

We reproduced a frozen, rule-executed experiment spanning 64 base streams, two paired probe menus, eight policies, and eight tasks per trajectory (1,024 policy trajectories; 8,192 task-policy evaluations). An independent implementation recomputed all tool results and scores. It also reconstructed the 20,480 calibration and 10,240 validation workflow labels. Source files, protocol, input cases, discrete actions, budget transitions, evidence, and final outputs agreed with the reference.

A strict JSON-hash gate nevertheless rejected 905 trajectories. Direct comparison against the full reference trajectories localized every non-timing discrepancy to the derived post-observation failure-probability field: 2,152 values differed, with maximum absolute error 1.67e-16. Operational projections matched exactly for all 1,024 trajectories. We retained the original failed gate and introduced a separately reported, post hoc numerical-equivalence audit: only the identified probability field admits an absolute tolerance of 1e-14, with finite [0,1] values required; all discrete scientific fields remain exact. This is a reproducibility correction, not rescoring or outcome selection. The reproduction does not increase the number of independent streams.

## Methodological result and limitations

Under the shared menu, the full task-loss kernel and single-effect kernel both solved 98/128 tasks in the matched condition, with task cost 36.30. Under data shift, the full kernel solved 109/128 tasks at cost 24.90, compared with 111/128 and 23.00 for the single-effect model. Cost is the observed binary task-failure count plus 0.05 times runtime probe credits, not monetary or wall-clock cost. Descriptive stream-paired intervals for the full-kernel versus any-mismatch contrast crossed zero in all three nonzero-drift conditions. These results do not establish a consistent benefit from modeling all higher-order interactions. Furthermore, the single-effect kernel was constructed from the full calibration table, so calibration savings have not yet been demonstrated.

The recorded macOS run used Python 3.11.15 and NumPy 2.3.5. For a three-channel horizon-eight cold initial-policy benchmark, two-repeat means were 0.1236 s for exact planning, 0.01061 s for rollout, and 0.000218 s for myopic selection. Corresponding peak traced allocations were approximately 20.23 MB, 1.09 MB, and 0.0335 MB. Memory tracing was conducted separately from timing. These are local initial-policy measurements, not process RSS, complete per-task latency, or high-dimensional scalability evidence.

Known transition hazards, a finite semantic family, ideal calibration receipts, and rule-based execution remain assumptions. The evaluation is not public-benchmark transfer or evidence of LLM necessity. The next study should measure whether selectively estimating interactions can improve held-out task utility after charging actual calibration and planning costs against a genuinely low-cost single-effect baseline.
