# Primary sources and overlap boundary
Checked 2026-09-13. This is not an exhaustive novelty review and no new novelty claim is made.

- ToolSandbox: Lu et al. arXiv:2408.04682; fixed source c8571d7854316d2e1c5f288e59fe1e34e53f6dd1, source tree 64ccd1694a91f2029844434d5995a2c0945cd6b2. https://github.com/apple-aiml-research/ToolSandbox . Native snapshots, tools and trajectory/milestone evaluation are already part of the project; R9's projections are not claims that official scoring only checks a final bit.
- Lilienthal & Hong, Mind the Gap, arXiv:2508.17155, https://arxiv.org/abs/2508.17155 . TOCTOU and tool-based mitigations already studied. No claim that after-read updates or double queries are new defenses.
- Li et al., ATBench, arXiv:2604.02022, https://arxiv.org/abs/2604.02022 . Trajectory-level safety evaluation already studied. R9 does not claim to invent whole-path evaluation. The abstract was checked; not reproduced.
- Podivilov et al., AgentLens, arXiv:2607.06624, https://arxiv.org/abs/2607.06624 . Whole-trajectory review rather than task-pass alone is existing work. Abstract checked; not reproduced.
- DeepSeek API: https://api-docs.deepseek.com/api/create-chat-completion/ and https://api-docs.deepseek.com/guides/thinking_mode/ . Request label and high thinking parameter confirmed on public documentation. This does not authenticate provider weights, alias equivalence or future endpoint availability. Request/return labels and system_fingerprint are recorded separately. No native tools parameter is sent, so reasoning_content is saved as evidence but not fed into next request.

R9 uses author-constructed event schedules on the same public ToolSandbox backend. It is a prospective fixed development diagnostic for later paid responses, not an external preregistration or a new independent benchmark. All original licenses and source remain intact.
