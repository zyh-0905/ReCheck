# R3 Implementation Plan

**Goal:** Deliver tested offline diagnosis and 417-attempt bounded live handoff, not paper acceptance.
**Architecture:** Reuse frozen R2 journal/accounting and SQL environment; new protocol, exact evaluator, hybrid worker, trace audit and CLI in isolated R3 directory.
**Spec:** docs/DESIGN.md

## Tasks
- [x] T1 Tests first: `python -m unittest discover -s tests -v`; empty modules must fail expected behavior checks. Implement exact policy evaluation vs brute-force H<=3, full grid and outcome-blind opportunity calculation.
- [x] T2 Tests first: required-only JSON plan schemas, irrelevant field rejection, timestamp removal, deterministic count render, stale/fresh audit separation. Implement worker and read-only hidden evaluator.
- [x] T3 Tests first: replicate IDs share payload but not response cache; deterministic frozen streams and no policy access to modes. Implement trace run with 384+32 independent calls.
- [x] T4 Tests first: config416 and cap417, source freeze, smoke prerequisite, paused no rerun, LICENSE export, journal partial integrity. Adapt reused support.
- [x] T5 Run full local loopback fixture and offline replay with all 416 primary/replicate calls plus smoke. Negative fixtures exercise pause; completed runs do not resample. Write evidence logs, not pretend these are real LLM results.
- [x] T6 Independent audit and fresh ZIP extraction tests. Deliver prompt, runbook, protocol, exact offline tables, tests and verification. No changes to original paper PDFs.

Final fresh-distribution verification is recorded separately in verification/DELIVERY_VERIFICATION.json.
