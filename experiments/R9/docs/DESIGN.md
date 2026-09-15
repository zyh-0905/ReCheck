# R9 live continuation and evaluation-gap diagnosis

Approval basis: user asked to execute the previously proposed diagnostic-paper plan, with researcher offline work and only paid LLM calls handed off.
No claim of a new TOCTOU defense or final-state-vs-trace concept.

## Frozen design before paid data
Four declared task families: person message, explicit-number message, reminder-description rescheduling, and Wi-Fi/low-power dependencies. The first three retain the scope of ToolSandbox-derived mechanisms; settings add a distinct state-dependency family, not a new external benchmark.
Four paired schedules: none, relevant update before episode, relevant update just after first qualifying read, unrelated update just after that read. One update at most. No change is selected based on answer success. Absent reads leave the post-read intervention untriggered; report this, do not reassign/drop cases.
Actor arms: ordinary inherited context; same data plus read-before-write and outcome-confirmation instruction. Same native APIs, no atomic guards, no private state or oracle supplied. Changes never erase existing agent effects. The actor continues after actual results for at most 10 requests including done.
16 constructed cases, 32 primary episodes, 4 diagnostic repeats (post-read person/reminder, both arms), 360 main request attempts plus one smoke.

## Scoring axes
A: successful state-changing tool return; B: task goal in final business state; C: final goal and permitted final business state; D: final goal with no unauthorized write at any earlier agent step. Termination, event-trigger rate, explicit error recovery and budget exhaustion separate. These are our diagnostic projections, not claims about official ToolSandbox scoring. Business state excludes native reminder creation timestamps, with scope explicit.
Reference scoring never enters actor payload. Intervention logs separate external from agent state changes. Query-observation can be stale at receipt by design; it is not rewritten.
Primary comparison evaluates grading disagreements on the SAME live trace, not algorithms with different atomic privileges. 32 episodes are not 32 independent task families. No confirmatory significance claims. No new RepairLens results.

## Costs and safety
All model attempts, tool calls, setup calls, durations, raw responses and endpoint metadata retained. Tokens not currency. No LLM judge/user simulator. No real SMS, files or personal accounts. HTTP errors/invalid JSON/truncation/identity changes pause; semantic tool errors return to actor within fixed cap. No auto-retry or post-stop calls.
