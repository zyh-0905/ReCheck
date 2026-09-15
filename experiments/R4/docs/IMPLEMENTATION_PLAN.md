# R4 Implementation Plan

> Execute inline in a new isolated artifact workspace. Do not modify any earlier archive.

**Goal:** a runnable, bounded R4 handoff with raw evidence and reproducible offline checks.
**Architecture:** exact finite joint refresh model, executable composite JSON API, frozen experiment, inherited network journal, independent audit and result exporter.
**Tech Stack:** Python 3.11+, numpy 2.3.5, standard library.
**Spec:** docs/DESIGN.md

## Global constraints
No researcher-side remote LLM calls. User maximum 409 total attempts. Old results immutable. No hidden labels in payloads. No expected result filtering of seeds. No fabricated public benchmark, billing or algorithm originality claims.

## Tasks and verification
- [x] T1 core: `r4lib/model.py`; tests `tests/test_model.py`. Verify loss, overlap union, hard budget, brute-force small optimality and rollout/base comparisons. Run `python -m unittest discover -s tests -v`; first observe red then implement.
- [x] T2 environment: `r4lib/environment.py`, `worker.py`, `protocol.py`; test all eight modes, public request compilation, multi-page/stock joins, calibration and budget rejection. Same red-green cycle.
- [x] T3 runtime: adapt R3 journal/common/storage with frozen R4 identities; implement `r4.py`, `experiment.py`, `audit.py`. Test no calls before gates, refusal after pause, credential exclusion, export LICENSE, replay using saved outputs only.
- [x] T4 offline: exact policy values, retained factorial conditions and counterexample, parameter support not winner filtering; compare rule executor and LLM channels in audit.
- [x] T5 handoff: prompt/runbook, source hashes, fresh unpack tests, full local loopback fixture labelled SOFTWARE_TEST_NOT_RESEARCH, request/record reconstruction and zero remote-call declaration.

Key acceptance commands are full unit tests, `python r4.py prepare`, local fixture smoke/run/audit/export/verify, and a second read-only replay. The final status must distinguish local software checks from real model results still pending.
