# R14：公开原始数据接收与首轮真实轨迹分析

这是**已执行的离线分析成果包**，不是用户执行任务，不授权任何新模型请求。
研究数据来自用户回传的固定版本 SAP/agent-quality-inspect 公开 JSON。请先读 `REPORT_ZH.md` 和 `CASE_REVIEW_ZH.md`。

## 内容
- `inputs/R14_public_data_original.zip`：用户回传的公开数据原包，内含109份原始文件及采集清单；不改字节。
- `ANALYSIS_LOCK.json`：进入trial2–7谓词筛查前保存的代码摘要和范围；不是外部预注册。
- `src/`：标准库离线分析、独立终态核对、事后语义敏感性；无模型请求。
- `results/dev_v2/`、`results/heldout_v1/`：冻结主筛查结果；保留 `dev_v1` 的大小写开发反例，避免掩盖开发修改。
- `results/all_episodes.csv`：3,551条记录的身份、调用结构、原分数和限定目标筛查。
- `results/receipt_batches.csv`未单列；各划分目录中保留 `receipt_batches.csv`。
- `results/sequential_scopes.csv`：96条顺序任务的**初步**边界筛查，不是人工金标准。
- `results/posthoc_*`：明确标注事后敏感性结果，不冒充独立确认集。
- `results/regression_candidate_raw_sample.json`：唯一静态目标回退候选的原始sample副本；其中用户要求恢复低电量模式，不能直接判作未授权回退。
- `sources/`：对应ToolSandbox序列化/设置代码与原许可证、外部来源索引。

## 复现（供研究端/审阅者，不需要用户重跑）
Python 3.11及以上，仅标准库：

```bash
python -m unittest discover -s tests -v
python reproduce.py --out /absolute/path/to/a/new/output_directory
```

复现只读取本地JSON，校验109文件并重新生成表格；不会执行采集脚本、下载对象、pickle或模型代码，不安装依赖。要求新输出目录，拒绝覆盖。

## 解释限制
本包不是完整ToolSandbox重评分，不运行TED裁判。960条静态请求只检查十种任务的选定效果，不能替代所有业务约束。缺失状态保留UNKNOWN。顺序任务独立处理；恢复旧关系可能是用户授权，而不是Agent犯错。没有新模型训练、调用、公开榜单修改或GitHub推送。

原数据许可见其数据卡（Apache-2.0）；源码文件沿用各自原许可。作者、单位、论文录用及独立人类审核均未由本包认证。
