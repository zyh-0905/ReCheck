# Integration review and remaining limits

This review is by the same assistant, not an independent human or separately dispatched reviewer. New development is isolated in a new directory; all predecessor archives are untouched.

## Code/data separation
- Unmodified legacy/native.py, timeline.py, scoring.py and replay.py execute original tools and event/scoring rules. Schemas and frozen case bytes match the accepted inputs.
- Only nt/prompts.py constructs actor inputs; cases' private state, contracts and event labels are not included. Tests check identical public messages across event variants.
- Native contract/journal use qualified structure, full-batch schema/ID validation, raw response bodies and exact tool receipts. No text extraction, fake result, hidden repair model, or retry.

## New failure modes checked
- Read + write in one response sees an event between the two, with old read receipt preserved.
- Second read in later response observes updated state; skipping the anchor remains unexposed.
- Explicit native exceptions are returned, not mistaken for wrong writes; earlier wrong writes remain violations after apparent repair.
- Four tools/response × ten responses is bounded at forty/episode; completion at the last mutation can remain unterminated without an extra response.
- Native schema/batch failure executes zero tools from that response.
- Transport/identity/format failures preserve raw evidence and pause globally; local interrupted batches retain a per-tool checkpoint and may require manual partial-prefix review.
- Raw integrity and response reconstruction are separate from task correctness. No zero-success table for unstarted tasks, no best-of-two repeats.

## Limits
- Scripted HTTP fixture responses and unit tests are not new LLM samples. The actual endpoint has not run the R9NT1 dynamic batch.
- Process/network guard is not a hardened operating-system sandbox; no real personal accounts are connected.
- Frozen endpoint/schema metadata do not authenticate model weights or billing.
- Tool failures and batch scheduling can affect exposure; comparative causal claims require care.
- Timeouts in the assistant's long combined verification commands are preserved. Tests are run to completion in separate active verification processes, without altering protocol or responses.
- This adds execution infrastructure, not a publishable algorithm contribution or new RepairLens evidence.

## Pre-release integration correction
A local later-response failure fixture exposed an accounting omission: the audit originally counted tools only from completed episodes, dropping an already-replayed partial prefix. A failing test (expected one native read and two environment operations, received zero) was saved before correction. The auditor now reports completed and partial native counts separately, and verifies the final per-tool progress sidecar. This changed audit accounting, not the task, inference, timeline or outcomes. No real model data were generated during the correction.

Final loopback integration skips the transport's 0.4-second inter-request sleep in the test harness only. This does not alter production config or request bytes; elapsed times of such fixtures are not performance evidence. Prior pacing-enabled runs are retained as pre-correction software evidence.
