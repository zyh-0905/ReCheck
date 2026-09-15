# R10 implementation review and known limits

This is a same-assistant review, not a separately dispatched agent or human peer review.

Reviewed against the frozen plan:
- The model loop receives task/history/schema and actual receipts only. Hidden cases and full SQLite states occur only in environment/auditor objects.
- Both connections use parameterized queries; identifiers are enumerated in code. Model has no arbitrary SQL/file/shell tool.
- Atomic preconditions are offered to all four arms. There is no transaction spanning model generation and no claimed remote atomicity.
- First relevant read triggers at most one environment event. Any subsequent update attempt closes that opportunity. If the agent skips the read, missing exposure is retained rather than manufactured.
- All returned tool calls are schema/ID validated before execution, then sequentially dispatched. A terminal report must be unique and last. Ordinary prose never becomes a database action.
- Every database event includes before/after states and result. The evaluator carries external deltas forward separately, so an external event cannot legalize an earlier wrong write. Technical row versions remain logged but do not alone count as business corruption.
- The prior qualified native transport is reused. It keeps raw bytes, usage, request/response labels, tool IDs and required reasoning history. Loopback tests are explicitly software, not scientific records.
- Frozen records are never chosen best-of-N. A completed run returns unchanged; paused/orphaned records stop. A catastrophic interruption without a response may require manual reconciliation; automatic audit is not claimed to resolve unknown paid outcomes.
- Raw scalar type errors, nonfinite JSON, unknown tools, source/config changes, cap mismatch and delayed bad batches have negative tests. Standard-library network blocking is not OS-level hostile-code isolation.
- finish_task is an untrusted self-report. No success score is returned to the agent; reports after earlier tools in one response have no intervening model observation. Its local receipt is not falsely asserted to be consumed by a later model request.

Scope limits: two constructed families/one SQLite backend; single preplanned change; fixed small schema; task descriptions clearly state preservation; extra instruction lengths differ; one endpoint; no formal proof/independent human audit. The simple scripted resolvers are deliberately retained as strong mechanisms. Their successes cannot be turned into LLM successes or a novel optimizer result.
