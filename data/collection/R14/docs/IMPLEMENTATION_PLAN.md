# R14 public-corpus transfer — bounded implementation plan

Goal: unblock the previously approved R13 external-trajectory analysis by transferring immutable public JSON bytes, without any model, user simulator, judge, or paid endpoint.

Source: SAP/agent-quality-inspect at 593e686f4d0c2e9fcae5ae664c16a7687907cf97.
Selection before downloading outcomes: six listed ToolSandbox model directories; both expert/nonexpert; trials 0–7, plus their aggregate files and dataset README. No pickle, model weights or execution of downloaded content.

- [x] Write focused tests for fixed roster, schema, safety and archive preservation; record failure before implementation.
- [x] Implement standard-library HTTPS GET collector with bounded sizes, no retry and no overwrites.
- [x] Record exact raw-file hashes and missing files; export usable partial evidence on transport failure.
- [x] Test full simulated collection and rejection paths; do not call simulations research samples.
- [x] Deliver only downloader plus prompt. Data collection is not R14 scientific completion.
