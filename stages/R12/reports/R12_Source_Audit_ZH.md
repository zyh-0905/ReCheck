# R12公开来源与证据等级

核查日期：2026-09-15。网页检索使用Exa；仓库文本通过GitHub连接读取。公开下载在当前容器DNS失败，所以ToolSandbox运行环境复用此前已回传且本轮重新校验的材料。没有重新向用户索取材料。

## 固定源代码

### ToolSandbox：已原生执行

- 当前仓库：`apple-aiml-research/ToolSandbox`（原`apple/ToolSandbox`重定向至此）。
- 提交：`c8571d7854316d2e1c5f288e59fe1e34e53f6dd1`，2026-09-11；tree `64ccd1694a91f2029844434d5995a2c0945cd6b2`。
- 本轮77个上游文件与历史冻结清单一致，原始LICENSE及ACKNOWLEDGEMENTS保留。
- `tool_sandbox/common/evaluation.py`的Git blob为`af9faacc65c0e700a52093fb0c5d77ac6c36c449`，与本轮GitHub读取结果相同。
- 源码定位：`EvaluationResult.__attrs_post_init__`（约955—983行）、`MilestoneMatcher._dfs`和`compute_mapping_and_similarity`（约1070—1211行）。原版枚举历史快照并最大化里程碑匹配，没有对所有目标统一追加结束时保持条件。
- 公共任务位置：single_tool_call_scenarios.py中的cellular_off、wifi_off、update_contact_with_id_and_phone_number；multiple_tool_call_scenarios.py中的三个低电量开启任务、update_contact_relationship_with_relationship、modify_reminder_with_recency_latest。
- 原项目说明的指标本来就是历史里程碑的动态匹配。必须区分“这是一个进展指标的边界”和“作者保证了它能认证所有最终状态”。本轮没有确认后一个广泛主张。

链接：
https://github.com/apple-aiml-research/ToolSandbox/tree/c8571d7854316d2e1c5f288e59fe1e34e53f6dd1
https://github.com/apple-aiml-research/ToolSandbox/blob/c8571d7854316d2e1c5f288e59fe1e34e53f6dd1/tool_sandbox/common/evaluation.py
https://arxiv.org/abs/2408.04682

### tau2-bench：源码与文档核查，没有运行完整框架

- 仓库：`sierra-research/tau2-bench`；截至2026-09-15的选定提交为`2174a603f6d014ef94473ffa95957f6ce27100db`，日期2026-09-10。
- 实际阅读：`src/tau2/evaluator/evaluator.py`（blob `76c95a83e9049d70a5570b93989797c0626974b6`）、`evaluator_env.py`（`a2e0a1a07cffd9394cc462376799289b1e9fbedd`）、`evaluator_action.py`（`861784876aab7f0f2bf16685b8607b50f9873fd5`）。
- `ALL`/默认组合只把任务reward_basis指定的分项乘入总分。ACTION可诊断计算，但没有进入reward_basis时不会降低总reward。
- EnvironmentEvaluator用参考动作生成目标数据库，并比较实际轨迹的结束状态，不要求逐条复制这条参考路径。工具错误不是按字符串出现次数累计扣分。
- 因此，本次没有支持“tau2默认评分会因没有照抄参考动作或出现一次工具错误而自动判失败”的假设。
- 已有公开issue #499及更早#321报告了参考动作失败被吞掉的问题。该问题不同于本轮ToolSandbox终态回退发现；仅核查文献/源码，不宣布我们首次发现，也不声称本轮复现其15/114等数值。
- 没有安装并执行整个tau2 runner、用户模拟器或NL断言模型，没有产生tau2官方成绩。

链接：
https://github.com/sierra-research/tau2-bench/blob/2174a603f6d014ef94473ffa95957f6ce27100db/src/tau2/evaluator/evaluator.py
https://github.com/sierra-research/tau2-bench/blob/2174a603f6d014ef94473ffa95957f6ce27100db/src/tau2/evaluator/evaluator_env.py
https://github.com/sierra-research/tau2-bench/blob/main/docs/evaluation.md
https://github.com/sierra-research/tau2-bench/issues/499
https://github.com/sierra-research/tau2-bench/issues/321

## 检索边界

一次ToolSandbox issues关键词检索未返回相关项，不是未发表、未讨论或全球首创的证明。MM-ToolSandbox等后续项目没有执行，结论不能扩展到它们。现有工作的时间逻辑、终态断言和变形测试均不是本轮新发明。
