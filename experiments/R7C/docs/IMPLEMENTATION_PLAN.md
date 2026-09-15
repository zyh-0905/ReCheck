# R7C Implementation Plan

Goal: deliver a capped, audited native-tool model diagnosis, not another rule-copy test.
Architecture: immutable preparation -> bounded JSON decisions -> native tools ->
independent state/side-effect scoring -> raw journals and replay audit.

1. Test/implement strict JSON, source integrity, safe ZIP and terminal/action schema.
   Required rejects: duplicate key, NaN, arbitrary tool names, executable objects,
   credential in payload, unexpected fields, path traversal and tampered files.
2. Test/implement native scenarios and public projection. Shared inputs across arms;
   no private snapshot, goal IDs/answers or variant labels passed to the actor.
3. Test/implement independent state scorer and scripted controls. Include literal
   number vs person, reassigned number, changed/deleted reminder ID, redundant
   setting and low-battery error; all pre-existing unrelated rows must survive.
4. Test/implement HTTP journal and bounded episode loop: no retry/fallback, global
   attempt cap, identity/usage/finish checks, pause/export, completed-run no resample.
5. Reconstruct all recorded payloads and tool results without network, validate
   internal journals and input hashes; preserve partial runs and classify missing.
6. Test through a localhost software fixture, package with upstream licenses,
   prompt/runbook/protocol and actual offline results; re-extract and verify.

No GitHub writes, account access, model calls or changes to old archives in this work.
