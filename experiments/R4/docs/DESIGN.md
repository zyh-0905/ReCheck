# R4 design and accepted execution scope

R4_BUNDLE_BUDGET_01 is a new development protocol, not a confirmatory test or a new published benchmark.
The user approved continuing research and receiving a runnable bounded model-call package.

Scientific question: do overlapping exact calibration packets and an episode-wide hard credit budget make independent refresh decisions inadequate, and can two-step rollout approximate joint planning in a composed catalogue/inventory API?

Fixed design before world sampling: 4 conditions (overlap matched; disjoint matched; overlap/no drift; overlap/underestimated drift), 3 independent streams each, 8 tasks per stream. Four LLM policies: recheck_joint (finite-model exact reference), bundle_rollout (two-step rollout with paced-age base tail), bundle_myopic (exact feasible one-step subset), age_paced. Additional separable_projected and never are offline controls only. Joint enumeration and rollout are established tools; no claim of novel general optimality. Shared observations and maximum coverage have strong prior art.

Three hidden binary semantic channels: pagination origin, active status encoding, net/gross inventory. Independent symmetric flips; accurate initial calibration; known task transition and assumed hazards. Every policy receives the same probe catalogue. Probes cover singleton channels or overlapping pairs. Packet costs are integer credits, not currency; step cap and episode budget are enforced by the environment. No benchmark truth enters the policy or LLM. Task loss surrogate is weighted semantic disagreement, separately report executable task success.

New environment is our own executable in-process JSON API, NOT public AppWorld/MemoryArena results or a production API. It performs pagination, status filtering, stock joins and aggregation on deterministic generated records. Public structured requests are shown to both LLM and deterministic compiler. No arbitrary LLM code is executed. Canonical evaluator only scores after the run. Probe calibration uses explicit test fixtures; finite known semantics are a limitation.

384 primary calls + 24 independent midpoint repeats (joint/myopic only) + 1 smoke = 409 attempts. Initial receipts are common deterministic calibration. Repeat responses never replace primary or update policy state. Source/protocol/config frozen, strict ledger and fail-pause gates inherited from R3. No remote model calls by the research assistant; only user executes paid commands. No price guesses; fees unknown. No retries, unlock, resampling or forced success. Old experiments unchanged.
