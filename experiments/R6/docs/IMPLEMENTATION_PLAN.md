# R6 Implementation Plan

> Execute tests and implementation in this isolated new package. No old directories or model calls.

**Goal:** Measure whether buying interaction labels is justified by subsequent task-loss improvement.
**Architecture:** Immutable paid-calibration ledger, table estimators and acquisition selectors, unchanged finite planner, isolated private task execution, independent audit, portable immutable export.
**Tech Stack:** Python 3.11+, numpy 2.3.5, stdlib.
**Spec:** docs/DESIGN.md.

## Tasks and verification commands
- [x] 1. Test canonical cells, irrelevant invariance, duplicate charging and single-only access. Create tests/test_acquisition.py, implement r6lib/data.py and acquisition.py. Run `python -m unittest tests.test_acquisition -v`.
- [x] 2. Test selection does not see unbought labels, equal cost, immutable prefixes, deterministic rankings and zero sensitivity. Create tests/test_selection.py and implement selection.py. Run `python -m unittest tests.test_selection -v`.
- [x] 3. Test exact discrete comparison, bounded numeric tolerance only at declared paths, metadata corruption, missing records, NaN and infinity rejection. Create tests/test_equivalence.py, implement equivalence.py. Run `python -m unittest tests.test_equivalence -v`.
- [x] 4. Test immutable artifact identity, no-network entrypoint, private data separation, budget, trace recovery and completed-run no-resample. Implement runtime.py, storage.py, study.py, review.py and r6.py. Run `python -m unittest discover -s tests -v`.
- [x] 5. Freeze code/protocol before research execution, run all fixed panels and streams; save raw metrics and all negative conditions. Independently audit and recalculate ledgers.
- [x] 6. Save discrete references separately from predictive float references; repeat full run from new unpacked distribution; compare exact decisions and bounded predictions. Do not match timing.
- [x] 7. Write findings, literature boundary, theory and user runbook/Prompt. Freeze final source manifest, re-test clean distribution and verify output ZIP.

Final checklist assertions must be read together with verification/DELIVERY_VERIFICATION.json and fresh execution logs.
