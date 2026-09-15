# R11近邻工作核查与下一阶段门槛

访问日期：2026-09-14。一级来源为作者论文/标准；检索与全文阅读不等于代码复现。这里只说明与当前具体主张的重叠，不声称穷尽所有工作，不把预印本均当作顶会录用论文。

## 近邻矩阵

| 工作 | 已有覆盖 | 对本稿的约束 |
|---|---|---|
| Reddy等，Reason Less, Verify More，2607.07405v2 | 政策宽松工具中的静默错误、前置守卫及守卫精度审查 | 不能把“有些拒绝有用、有些无用”宣布首创；本地案例不能代替其公开任务证据 |
| Lyu等，From Version Conflicts to Decision Conflicts，2609.08015v1 | 显式可执行决策条件、版本与决策冲突区别、选择性复核和提交绑定 | 本稿行条件/选择条件的机制与之相近；不包装为新算法 |
| Wang等，AgentSpec，2503.18666v3 | 可定制运行时约束、触发器/谓词/执行机制 | 添加动作守卫本身不新颖 |
| Lilienthal与Hong，Mind the Gap，2508.17155v1 | Agent检查—使用竞态及提示、监测、工具融合 | 本稿不再声称发现新的TOCTOU攻击或防护 |
| Lu等，ToolSandbox，2408.04682 | 状态化工具与评测基础 | 本研究扩展不是原官方完整榜单成绩 |
| Fielding等，RFC9110 | 条件请求的规范语义 | 正确的条件拒绝不能仅因没写入就一律计为代理错误 |

本稿候选测量增量是把**完整条件请求是否合法、去除前提后的业务效果、真实提交、反馈后的恢复**分别核算。但目前只在小型自建任务上完成，不能把一种清楚的表述直接当作已证明的新颖性。

## 进入下一份付费包前的明确门槛

1. 先在公开环境或已有评测实现中定位一项真实、可引用的归因问题；给出规则、输入和导致误判的轨迹，不只假设别人用“冲突次数”评模型。
2. 建立任务规范而不是只对照某条金标准操作路径。不同合法解法要被接受；不提供隐藏答案给在线策略。
3. 在该规范下区分正常条件拒绝、业务错误的无条件尝试、过度保守拒绝与工具错误；两名人类审阅者或清晰可执行规范用于独立审查，尚未完成不得声称完成。
4. 静态离线重放只能回答局部转移；涉及恢复成本、替代策略成功率时，另行冻结匹配的真实闭环实验，完整计入重试，不拼接本包分支。
5. 先固定任务ID、版本和纳入规则，再看新方法成绩；公开原版与额外构造干预分别命名。两组能力不同就报告执行契约效应，不作为同能力算法对照。
6. 若公开评测已正确区分这些概念，或者结果仍只有已知机制复现，则停止当前诊断贡献主张，不用换seed或删合法能力制造差异。

当前**没有**已冻结的外部主任务列表、原生基线复现或新付费执行代码；不承诺此路径一定形成论文。上述门槛不要求用户现在运行实验，所有可在研究端完成的工作仍由研究端执行。

## 本次读取的来源

[S1] Vikas Reddy, Sumanth Reddy Challaram, Abhishek Basu. Reason Less, Verify More: Deterministic Gates Recover a Silent Policy-Violation Failure Mode in Tool-Using LLM Agents. arXiv:2607.07405v2 (2026-07-11).
https://arxiv.org/html/2607.07405
https://arxiv.org/abs/2607.07405

[S2] Yongjian Lyu, Yang Ren, Ruofei Lai, Wenting Liu. From Version Conflicts to Decision Conflicts: Selective Revalidation for Long-Running AI Agents. arXiv:2609.08015v1 (2026-09-07).
https://arxiv.org/html/2609.08015
https://arxiv.org/abs/2609.08015

[S3] Haoyu Wang, Christopher M. Poskitt, Jun Sun. AgentSpec: Customizable Runtime Enforcement for Safe and Reliable LLM Agents. arXiv:2503.18666v3 (2025-07-31).
https://arxiv.org/html/2503.18666v3

[S4] Derek Lilienthal, Sanghyun Hong. Mind the Gap: Time-of-Check to Time-of-Use Vulnerabilities in LLM-Enabled Agents. arXiv:2508.17155v1 (2025-08-23).
https://arxiv.org/html/2508.17155

[S5] J. Lu et al. ToolSandbox: A Stateful, Conversational, Interactive Evaluation Benchmark for LLM Tool Use Capabilities. arXiv:2408.04682 (2024).
https://arxiv.org/abs/2408.04682

[S6] Roy Fielding, Mark Nottingham, Julian Reschke. HTTP Semantics. RFC9110 (2022), Section13.
https://www.rfc-editor.org/rfc/rfc9110.html#name-if-match
