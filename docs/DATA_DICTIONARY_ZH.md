# 数据目录和口径

## 第三方公开数据（不是本项目重新调用模型生成）

固定源：SAP/agent-quality-inspect，提交`593e686f4d0c2e9fcae5ae664c16a7687907cf97`。

可直接浏览的目录：
`data/public/SAP_agent-quality-inspect/593e686f4d0c2e9fcae5ae664c16a7687907cf97/`

其中`raw/toolsandbox/<model>/<expert|nonexpert>/trial_<n>_results.json`保留96份试验JSON；各设置的aggregate共12份，另有数据卡README。根`MANIFEST.json`与`collector_used.py`是采集证据，不是额外数据样本。原始压缩包还保存在`analysis/R14/inputs/R14_public_data_original.zip`，无需联网即可使用。

数据共3551条、37个不同任务ID；`gpt_4_1/nonexpert/trial_0_results.json`源文件仅36条，缺`convert_currency`。这不是漏下载。六个来源模型目录×两个人设×八个trial是重复记录结构。

| 字段/对象 | 用途 | 注意 |
|---|---|---|
| 模型目录、persona、trial、sample_id | 复合记录身份 | 不只用run_id去重；不同目录可能重复run_id |
| status | 来源运行状态 | success不是任务效果全部正确 |
| trajectory | 已保存对话、调用和工具回执 | 文本中的工具式JSON不等于原生调用 |
| tool call ID | 连接提案与实际回执 | 无匹配回执则不能补造执行 |
| database_update | namespace表快照 | 不按逐行补丁合并；不推断未知的同批中间状态 |
| progress_rates | 来源TED的进展序列 | 尾部可补齐；不是额外回合，不是ToolSandbox similarity |
| 本地local/terminal谓词 | 本研究声明的有限效果检查 | 不是整项任务真值；缺证据保留UNKNOWN |
| conservative_conflict/review_class | R15审阅后保留的冲突类型 | 与自动候选和排除表分开 |

## 本项目真实模型实验

R7C1、R9NT1、R10等的原始回传在`feedback/`，原任务代码在`experiments/`，审核表在`stages/`。同一调用可能因累计上下文在多个文件出现；计数须按实际请求或工具事件身份去重，不按文本字符串出现次数。

## 离线脚本与局部反事实

R11、R12、R13有原生本地执行但没有新模型答案。其快照、时钟、回放和测试数据不能追加到公开语料模型样本分母。`results/dev*`与`results/posthoc*`按原命名保留，不能把事后敏感性分析称为盲测。

## 两套来源清单

`provenance/SOURCE_ARTIFACTS_ALL.json`：历史与本次新增源附件的名称、长度、SHA-256、归档去向。`ARCHIVE_MANIFEST.json`：当前整合目录逐文件摘要。原包自带清单原样保留。相同SHA-256可能代表多个便利副本，不等于多个实验。
