# Frozen pilot protocol v0.1

## Status
Exploratory development pilot, not external preregistration, not a completed main-paper experiment. No claimed power, significance, generalization, or independent human audit. All model calls must be performed by the user on their own authorized endpoint.

## ReCheck
- 4 independent stream seeds, 8 tasks each, fixed generator. Alternating no-drift and hidden-drift conditions. Bernoulli flips have probability 0 or .12. The controller is always given the nominal finite model, not the current truth.
- Unit and endpoint are initially calibrated using exact, scoped SQLite probes; one actual LLM writer produces a shared memory per stream. A malformed initial writer output remains unknown, not silently repaired with hidden labels. All methods receive the same initial prefix.
- Methods: unchanged original finite DP; myopic; fixed TTL=3; refresh-all. All work under the same probe-price surrogate, not a common hard tool budget. Original DP is optimal only for its declared surrogate model, not for empirical LLM loss or invoice costs.
- Two calls per task/method: bounded plan and answer after executing local tools. Prompt contains neither method identity nor hidden true modes, future queries, SQL comparison operators, gold labels or task scores. Tool handlers—not arbitrary generated code—perform SQLite queries. No model-driven automatic repair.
- Method order is rotated within each stream/step. Request IDs remain distinct across methods even when inputs coincide. Shared initial prefix is the only cross-method model response reuse. Resume restores an already completed logical call and does not constitute another experimental replicate.
- Report all intended task/method pairs, invalid plans, malformed outputs, truncations, provider errors and pending calls. Missing usage is explicitly marked. Offline correctness uses canonical stored amounts, integer time conditions and actual output, never the policy's suggested mode.
- Experimental unit: stream, not each of its model calls. Four streams are a pipeline/behavior pilot, not evidence of population-level superiority. Additional repeats or modified prompts remain development data.

## RepairLens replay readiness
- Deliberate diagnostic, NOT the RepairLens finite-model planner and NOT a surrogate result under its name.
- Four generated source-revision cases with three separately produced model artifacts. The source revision is publicly supplied, old generated artifacts are frozen once for all methods. No oracle-clean prefix is substituted and no until-success filtering is allowed.
- Full regeneration and LLM-selected patching use the same per-artifact worker and output contract. Keep-stale is a no-repair control. The selection call is charged. Candidate parsing errors remain failures; no hidden test is used to select/retry patches.
- Explicit natural-language arithmetic rules and partial logged provenance; no claim of arbitrary unknown-dependency recovery. These are revisions, not audited natural agent failures. No selected-set claim establishes causal optimality.
- Report all cases and separately the offline subset with correct old artifacts that become invalid under the new source. Do not discard non-eligible rows from the bundle. Current artifact checks are not independent unseen follow-up tasks.

## Client controls
- No streaming, SDK, automatic model/parameter switching, shell execution or silent retries. `max_tokens` versus `max_completion_tokens` is explicit configuration.
- One process per output directory. Immutable code/config/protocol fingerprint. Journaling precedes the request; completed responses are hashed and retained. In-flight interruptions require explicit retry consent. Provider errors also require explicit retry flag.
- Hard HTTP-attempt count; optional token-price-based estimate guard. This does not enforce an invoice hard cap. Prices, currency, usage, cache counts and missing bills are audited separately.
- Request Authorization headers and environment values are never serialized. The known credential is redacted if echoed by a provider. No endpoint credentials in URL or redirects. Export uses a file allowlist.

## Next gate
Review data completeness and model compatibility before deciding main experimental scale. Passing this pilot does not complete the original research plans. Formal holdouts must be drawn from different frozen task templates/mechanisms and never reused for prompt tuning.
