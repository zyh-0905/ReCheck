# Sources and scope
- ToolSandbox pinned source: https://github.com/apple-aiml-research/ToolSandbox/tree/c8571d7854316d2e1c5f288e59fe1e34e53f6dd1
  Included source bytes match UPSTREAM_MANIFEST.json, tree 64ccd1694a91f2029844434d5995a2c0945cd6b2.
  Full upstream license/acknowledgements retained. No endorsement is implied.
- ToolSandbox paper: https://arxiv.org/abs/2408.04682
  This run uses original native local tools/state/execution, but author-constructed scenarios and a new grader.
  It does not run the official autonomous user simulator or claim official benchmark scores.
- DeepSeek Chat Completions: https://api-docs.deepseek.com/api/create-chat-completion/
- DeepSeek thinking mode: https://api-docs.deepseek.com/guides/thinking_mode/
  Official indexed documentation checked on 2026-09-13 lists deepseek-v4-flash and high/enabled.
  Direct fetch timed out in this session; no current model endpoint was called by the researcher.
  Configuration intentionally differs from old deepseek-flash logs; do not combine as same-backend replication.
  No tools parameter is sent; text-JSON actions are executed by a safe local adapter.
  reasoning_content is retained in raw responses, not reused as an action or interpreted as a causal proof.
- Existing R7B report: material installation and native source observations were previously verified.
  This stage provides new native solvability and software checks, not a paid-model performance result.
