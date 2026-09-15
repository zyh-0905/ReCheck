# Sources and attribution

Data: SAP/agent-quality-inspect, Hugging Face dataset revision
`593e686f4d0c2e9fcae5ae664c16a7687907cf97`.
All requested raw JSON bytes and dataset card are preserved inside inputs/R14_public_data_original.zip. Licence: Apache-2.0 per dataset card. The collector manifest preserves exact URLs, response revision, ETag and local SHA-256.

Paper: Penny Chong et al., Talk, Evaluate, Diagnose: User-aware Agent Evaluation with Automated Error Analysis.
https://arxiv.org/html/2603.15483v1
The source uses adapted tasks, natural-language subgoals and LLM judges. Its progress implementation removes completed goals from subsequent evaluation. This is not ToolSandbox original milestone similarity.

Source code read through the GitHub connector (not executed; exact files of the original data-producing service have not been authenticated):
- https://github.com/SAP/agent-quality-inspect/blob/23c256af44af28f8f7b1b94be8acdb24c8ec80ea/src/agent_inspect/metrics/scorer/progress.py
  blob 501424d516e5215bde46471f48a1c294097f2eab. Lines260 onward show completed-goal retention and extension of last progress value.
- https://github.com/SAP/agent-quality-inspect/blob/23c256af44af28f8f7b1b94be8acdb24c8ec80ea/paper_experiments/datasets/toolsandbox_dataset.json
  blob c6daf02adc51973fa193b307449b6869cf0d1bf2. The in-scope task effects also occur verbatim in the supplied subgoal specifications (judge explanations not used).
- https://github.com/SAP/agent-quality-inspect/blob/23c256af44af28f8f7b1b94be8acdb24c8ec80ea/paper_experiments/toolsandbox_session.py
  blob 0483bd42fade7575f09fdbc77638c8c967b298d6. Session transport; not the full snapshot-emitting server.
- https://github.com/apple-aiml-research/ToolSandbox/blob/c8571d7854316d2e1c5f288e59fe1e34e53f6dd1/tool_sandbox/common/message_conversion.py
  Stored unchanged from the already supplied R13 vendor source. get_snapshot_indices_to_databases/serialize_to_conversation attach full namespace tables to messages. This supports the snapshot interpretation; it does not establish exact SAP runner equivalence.
- https://github.com/apple-aiml-research/ToolSandbox/blob/c8571d7854316d2e1c5f288e59fe1e34e53f6dd1/tool_sandbox/tools/setting.py
  blob d823d92f7ebaf2d907a07b8f9905d1c082362104. set_low_battery_mode_status(True) disables cellular, wifi and location_service; original file and licence retained.

No model/provider invoices or actual historical weights authenticated. No source numerical claims imported as our results. No native benchmark re-execution, LLM judge, or external issue/push in this analysis.
