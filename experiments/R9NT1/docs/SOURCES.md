# Sources and frozen implementation provenance

Protocol label: 2026-09-14; actual local execution timestamps are stored in logs and may differ from the date label.

- Supplied `Research_Handoff_R9J1.zip`, SHA256 `0ed0d58c4a6824322ec10b61e70dd7af2740e8778363ff8ed122bdfdfd03fdeb`: tasks, scenario snapshots, legacy native/timeline/scoring/replay/rules and fixed schedule.
- Supplied `Research_Handoff_R9TQ1.zip`, SHA256 `5c6a38967bab56a3f12efff9801fd4ecb36a067e57e73c5165857ff9fab62185`: qualified native API contract, journal, schemas and pinned requirements.
- Supplied `R9TQ1_Review_Report_ZH.md`: accepted three native qualification cases, ten responses. Not new study data.
- Official DeepSeek Tool Calls: https://api-docs.deepseek.com/guides/tool_calls/ (checked 2026-09-14 date label). Structured calls and matching actual tool-role replies; no client-inserted fabricated calls.
- Official DeepSeek Thinking Mode: https://api-docs.deepseek.com/guides/thinking_mode/ (same check). Carry prior reasoning_content when tools are used.
- Official Chat Completions: https://api-docs.deepseek.com/api/create-chat-completion/ (same check). Native auto tool choice and request model. No beta strict/forced tool/parallel option or JSON response format added.
- Original ToolSandbox commit `c8571d7854316d2e1c5f288e59fe1e34e53f6dd1`, 77 unmodified vendor files and original licenses. No affiliation or endorsement claimed.

Documentation establishes the intended contract, not that a provider always meets it. Local helper code is a new research integration. Runtime tests are software evidence only. The previous R8 literature boundary still applies; this turn makes no novelty claim and does not needlessly republish full articles or proprietary credentials.
