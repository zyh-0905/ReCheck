# Response-label amendment, r7c-1.0.1

The original protocol required the response model string to equal the request string. Its sole observed smoke response returned `deepseek-flash` for a `deepseek-v4-flash` request. It finished normally, produced the requested JSON, and provided coherent usage. The old run remains paused; no research episode was executed.

The new frozen allowlist accepts the requested label or this observed label at the initial smoke. The returned label and system fingerprint then form a pinned within-run metadata cohort. Both labels remain in logs; any subsequent change is a stop condition. This is **not a claim of alias equivalence or authenticated weights**. It is not a fallback: the requested model, endpoint, and payload do not change. No automated model discovery or extra probe is introduced.

The local audit now reports execution_complete separately and checks completed-run identity records against raw responses. A mechanical pass for a smoke-only directory does not establish completed experiments.

The 14 cases, three arms, seed/order, action and system prompts, worker, tool permissions, upstream source, stopping limits and scoring are unchanged. The amendment is made after inspecting a failed smoke, before any primary model task outcomes exist; it is a protocol repair, not outcome-based selection.

Budget: prior recorded generation attempts 1; new smoke at most 1; new primary/repeat run at most 384. Overall recorded-generation lineage upper bound 386. Extra out-of-band requests mentioned only in a README are unverified and not included in that accounting.

Evidence: docs/PAUSED_SMOKE_RESPONSE.json retains the full response record and docs/ORIGINAL_PAUSED_STATUS.json retains the old paused marker. They are archival documents, not current-run responses or imported completed smoke records.

Official documentation checked 2026-09-13: https://api-docs.deepseek.com/api/list-models and https://api-docs.deepseek.com/zh-cn/ . These show the request name, but do not in the retrieved passages establish the observed response-label equivalence. Response id 435179bf-26c6-4edb-95cc-4d9fa72568da is the local evidence for the added metadata label.
