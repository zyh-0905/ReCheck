# R1 Evidence Handoff Implementation Plan

**Goal:** Collect the previously missing interrupted run without invoking models or changing original evidence.
**Architecture:** A standalone, standard-library collector copies allowlisted bytes, checks the frozen manifest and request ledger, and writes a new checksummed ZIP. Missing or suspicious evidence produces an explicit diagnostic rather than a fabricated replacement. Experiment code is read as bytes, never imported or executed.
**Tech Stack:** Python 3.10+, pathlib, json, hashlib, zipfile, unittest. No network or subprocess calls.
**Spec:** ../TASK_CONTRACT.json; user-approved research/execution/audit division.

## Global constraints
- New model calls: 0. Paid experiment execution is not authorized in R1.
- Never edit, rename, unlock, delete, summarize-in-place, or resume existing runs.
- Default target: runs/recheck_deepseek_v41_flash; verify cap=4096 and the previously supplied fingerprint.
- Missing source and unavailable billing are reportable states, not grounds to regenerate data.
- Do not export .env, config.local.json, credentials or unrelated directories. Common secret patterns block raw export; not a universal privacy guarantee.
- Files must be stable during collection. User explicitly confirms the experiment writer is stopped.
- Checksums establish byte integrity, not authenticity, completeness of history, or research validity.

## Task 1: Collector and evidence checks
Files: collect_feedback.py, tests/test_collect.py.
Interface: collect_bundle(run_dir, out, contract, statement_path=None, billing_path=None) -> dict.
1. Write and run `test_entrypoint_exists`; verify failure before implementation.
2. Implement allowlist and raw-byte copying; audit schema without changing evidence.
3. Run `python -m unittest discover -s tests -v`.
4. Test missing source, interrupted requests, mismatched identity, malformed JSON, source mutation, secrets, symlinks and overwrite refusal.

## Task 2: CLI and return bundle
Interface: python collect_feedback.py --project PATH --stopped; python collect_feedback.py --verify ZIP.
1. Require a stopped-writer confirmation before reading source evidence.
2. Load frozen task contract; resolve only the named project/run.
3. Emit LOCAL_CHECKS.json and original evidence within a new ZIP; no live API invocations.
4. Verify extraction-independent ZIP hashes and expose incompleteness rather than automatically rerunning.

## Task 3: User handoff and packaging
Files: README_ZH.md, EXECUTION_PROMPT_ZH.md, WORKFLOW_ZH.md, operator_statement.example.json.
1. Give exact macOS/Linux and Windows commands and a bounded local-assistant prompt.
2. Use the same collector on real previously returned records only for offline validation; never manufacture the missing batch.
3. Package source/tests/docs/checksums and verify in a fresh directory.
