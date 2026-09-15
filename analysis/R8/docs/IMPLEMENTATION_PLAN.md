# Executed research plan
1. Read fixed R7C1 audit and raw kit; validate input SHA-256 and material manifest.
2. Restore the supplied Python 3.11 runtime and byte-validated native dependencies.
3. Write failing tests for dynamic versus literal targets, interleavings, rejection,
   current-at-commit scoring, retry limits and the no-network boundary.
4. Implement native experiment and independent pure-Python state scorer; save all cases.
5. Run tests, 120 native trajectories and offline score validation twice. Preserve failures.
6. Recompute paid R7C1 summary from raw episode/call data WITHOUT model invocations.
7. Create a claim/evidence matrix and an ICASSP-style descriptive paper with independent
   sections for original paid observations and new scripted execution-contract boundaries.
8. Compile, render all PDF pages, check references/layout, then zip verifiable sources.
No user rerun. No new paid runner. RepairLens is explicitly not validated by these results.
