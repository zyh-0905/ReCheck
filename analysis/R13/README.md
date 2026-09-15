# R13 — Temporal Scope Audit (offline research artifact)

**Not a user execution handoff. No model-call budget is authorized.**

This artifact continues the R12 public-evaluator diagnostic. It contains a full
registration census of a pinned ToolSandbox source, candidate semantic labels,
and five scripted executions of one original multi-turn user-revision task.
Neither the labels nor the scripted trajectories are independent human annotations
or new autonomous-model results. All original evaluator scores remain unchanged.

Start with `docs/RESEARCH_REPORT_ZH.md`, then `docs/SEMANTIC_REVIEW_GUIDE_ZH.md` and
`docs/SOURCES_AND_REAL_TRACE_FEASIBILITY_ZH.md`.

## Contents
- `results/census`: 129 base / 1032 expanded native registrations, public prompts,
  private user-simulator task specifications for **offline review only**, constraint metadata.
- `results/revision_run1`: five scripted trajectories, native snapshots and original scores.
- `results/revision_run2`: independent process rerun, not additional samples.
- `results/regrade_run1`: original evaluator regrading plus separate saved-state checks.
- `src/scope_logic.py`: conventional three-valued finite-interval reductions.
- `src/saved_check.py`: independent standard-library snapshot/effect checks; not a new grader.
- `vendor/ToolSandbox`: original 77 files, upstream Apple license preserved.
- `vendor/bridge`: unchanged previously delivered trusted NativeSession bridge.
- `logs`: development failures and successful verification; test trajectories are not research samples.
- `sources`: retrieval scope and limitations, not an imported third-party trajectory corpus.

## Reproduction by a researcher
The native path needs a compatible Python 3.11 ToolSandbox scientific environment
(the used version is CPython 3.11.14, NumPy 1.26.4, Polars 0.20.31, SciPy 1.13.1).
Previously supplied R7 dependencies were reused. No cloud provider stack or API key
is needed. Wheels, Python runtimes, and font files are not redistributed here.

For the previously unpacked dependency layout, set `R13_SITE` and `R13_ROUGE_SOURCE`
to those directories. With an already installed compatible environment they may
be omitted. The launcher defaults to the **included** upstream and bridge source.

```bash
python3.11 launch.py tests
python3.11 launch.py census /tmp/r13-new-census
python3.11 launch.py native /tmp/r13-new-native
python3.11 launch.py regrade /tmp/r13-new-regrade
python3 verify_archive.py
```

Output directories must not exist. `check` validates saved snapshots with a
standard-library checker; `regrade` also executes the original native evaluator.
The launcher blocks Python socket connect and DNS; this is not an OS sandbox.
No `run`, `smoke`, API probe, model-list call, or automatic publishing exists.

Full serialized snapshots have native time-dependent fields. Rerun equality is
claimed only for the explicitly compared scientific outputs; differences are
listed, not globally erased. Source integrity checks are not external attestation.
There is no independent human review, official benchmark submission or maintainer
endorsement. Manuscripts and old archives have not been overwritten.
