# Sources and scope

1. Raw public dataset: SAP/agent-quality-inspect, revision 593e686f4d0c2e9fcae5ae664c16a7687907cf97. Source card included as SOURCE_DATA_CARD.md; declared Apache-2.0. Raw bytes came from the user-supplied, previously verified R14 download, not a new scrape.
   https://huggingface.co/datasets/SAP/agent-quality-inspect/tree/593e686f4d0c2e9fcae5ae664c16a7687907cf97/toolsandbox
2. TED author paper, read 2026-09-15: Talk, Evaluate, Diagnose: User-aware Agent Evaluation with Automated Error Analysis.
   https://arxiv.org/html/2603.15483v1
   This is the source methodology, not an original ToolSandbox leaderboard regrading. No new judge calls were made.
3. Prior temporal reasoning work, used only to bound novelty (no code reproduction): Chu et al., TimeBench, ACL 2024.
   https://aclanthology.org/2024.acl-long.66/
4. Prior calendar reasoning work, used only to bound novelty (no code reproduction): Miao, Fu, Wei, SPAN.
   https://arxiv.org/abs/2511.09993

Simple calendar arithmetic and known difficulties of temporal reasoning are not claimed novel. Repository versions, provider weights and upstream operation are not authenticated beyond the saved files and receipt consistency checked here.
