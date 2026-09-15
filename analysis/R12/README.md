# R12 Public Evaluator Audit — offline, scripted, not LLM scores

Start with `docs/R12_Research_Report_ZH.md` and `docs/CLAIM_EVIDENCE_MATRIX_ZH.md`.
There is no paid experiment, key handling, submit command, or GitHub write.
Original R1–R11 data remain unchanged.

## Recorded result sets

- `results/native_run1`: first five original setting tasks × six variants.
- `results/supplement_run2`: three exploratory original tasks × five variants.
- `results/supplement_run1`: retained incomplete harness attempt, NOT added as independent evidence.
- `results/native_run2`, `results/supplement_run3`: reproduction only.
- `results/regrade_final`: original snapshot evaluator plus independent terminal checks, 45 records.
- `logs/minimal_repro.json`: independent original-class driver on wifi_off.

Every trajectory includes native events, snapshots, original evaluation mapping,
and separately labelled terminal goal. These are simulated ToolSandbox data, not
private user accounts. No public leaderboard has been regraded.

## Optional research-side reproduction

Use Python 3.11 and ToolSandbox's pinned original dependencies. The vendor ZIP
contains original source and licensing, not a runtime, wheel bundle, or fonts.
Install dependencies in a separate environment, or reuse the previously supplied
R7 runtime/modules. No installation or model call is performed by this package.

For an already configured environment:

```bash
export R12_TOOL_SOURCE=/absolute/path/to/extracted/ToolSandbox-c8571d7854316d2e1c5f288e59fe1e34e53f6dd1
python3.11 launch.py tests
python3.11 launch.py minimal
python3.11 launch.py native /tmp/r12-new-setting-results
python3.11 launch.py supplement /tmp/r12-new-extra-results
python3.11 launch.py regrade /tmp/r12-new-regrade-results
```

With a supplied interpreter executed with `-S`, also set `R12_SITE` to the already
unpacked dependency modules and `R12_ROUGE_SOURCE` to rouge_score-0.1.2 source.
Paths are examples; outputs must not already exist. Tests use shipped recorded
fixtures but also execute original native tools. Python sockets are blocked;
this is not an OS sandbox. No API key is read.

Recorded reminder tasks use local calendar semantics (the recorded environment
was UTC). Regrading restores the recorded relative-day evaluation input, whereas
new native runs use the actual clock. Across native runs the tabular outcomes are
identical but entire snapshots are NOT byte-identical; differences are retained.

## Provenance

`vendor/UPSTREAM_MANIFEST.json` records all 77 upstream source hashes.
`verify_archive.py` checks the delivery manifest without importing tools or making
network calls. See `DELIVERY_VERIFICATION.json` for tests actually run.

The maintainer note is a draft only. No issue has been filed and no claim of
novelty, human independent review, or submission readiness is made.
