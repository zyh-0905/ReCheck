# R2 implementation and verification plan
Goal: deliver a self-contained capped user-run ReCheck live-model development pilot and offline audits.
Spec: configs/r2_protocol.json; prior R1 report, source archive hashes recorded in docs/PROVENANCE.json.
Architecture: preserve original SQL worker and finite DP; new protocol, journal wrapper, evaluator,
accounting and gated CLI. User executes remote calls; current validation uses only local fixtures.
Tech stack: Python 3.11+, numpy 2.3.5 (original pin); standard library HTTP and SQLite.
Constraints: preserve prior artifacts; no new remote LLM call in development; no silent retry or
method/model substitution; hidden truth only in world/evaluator; raw journal immutable; fee unknown
without scoped schedule; no accuracy-based seed selection; no blanket scientific certification.

- [x] Task 1. tests/test_r2_audit.py before r2lib/audit.py:
  assert legal stale100 vs true1 is stale_related, irrelevant amount for count_all is not relevant;
  validate null, integer count, plan contract, truncation axes independently.
- [x] Task 2. tests/test_r2_protocol.py before r2lib/protocol.py:
  assert484 calls; fixed new seeds; public-task-only preflight distinguishes 0.22 and preserves0.18.
- [x] Task 3. tests/test_r2_accounting.py before r2lib/accounting.py:
  test Saturday offpeak, invalid usage, cache discrepancy, missing prices unknown, boundary crossing.
- [x] Task 4. tests/test_r2_live.py before r2lib/session.py and experiment.py:
  local HTTP fixture only; completed answers retained; invalid response stops; resume no resample;
  different model blocked; open attempts blocked; immutable request hash; source/code freeze.
- [x] Task 5. r2.py gated prepare/smoke/run/audit/export; tests for no overwritten export,
  no live calls before preflight/smoke/explicit cap consent, no private evaluation in model input.
- [x] Task 6. run all tests; reproduce previous TTL and Always fixtures; full484-request local
  fixture run (not LLM research), offline response replay, export/fresh-unzip integrity checks.
- [x] Task 7. Chinese operator prompt/runbook, negative findings and resource limitations;
  final source hashes and validation logs; provide the zip without test run outputs or credentials.
