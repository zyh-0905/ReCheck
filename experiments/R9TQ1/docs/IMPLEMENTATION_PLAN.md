# R9TQ1 Implementation Plan
Goal: prove an auditable native tool exchange before paying for full research calls.
Architecture: canonical contracts + journal + native session + lifecycle + offline replay.
Spec: DESIGN.md. Tech: Python 3.11, fixed native dependencies, urllib, stdlib tests.
- [x] Contract: red tests -> strict envelope, schema, metadata, tool ID and history validation.
- [x] Native integration: old unmodified native bridge, schemas, qualification state scoring.
- [x] Journal: exact request/response bytes, no retries, cap, safe error and credentials handling.
- [x] Lifecycle: prepare, one qualify command, audit/export, partial state retention.
- [x] Replay: rebuild outgoing messages and native events; validate all artifacts incl partial.
- [x] Fresh extraction: source hashes, native tests, loopback qualification and cap fixtures.
- [x] Handoff: prompt / runbook / version boundaries / costs, no new remote calls.
