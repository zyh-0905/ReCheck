# 反馈 10：R6 选择性交互校准与真实采样成本

| 项 | 内容 |
|---|---|
| 协议 | `R6_SELECTIVE_CALIBRATION_01`（r6-6.0.0） |
| 执行时间（原始 UTC） | **START 2026-09-12T18:34:49Z → END 2026-09-12T18:35:29Z**，完整结束（未中断） |
| **LLM / API 实验调用** | **0**（`new_llm_api_calls: 0`、`network_allowed: false`） |
| 是否使用密钥 | **否**（无密钥、无 .env、无模型配置、无 smoke、无登录/充值） |
| 记录到的环境 | `macOS-26.5.2-arm64-arm-64bit`、`arm64`、Python **3.11.15**、NumPy **2.3.5**（硬件型号未猜测） |
| 规模 | 40384 次物理校准工作流、128 条基础流、2560 轨迹、20480 条规则记录 |
| 单元测试 | **60 tests, OK（退出码 0）** |
| **`execute` 退出码** | **0**（完整结束） |
| **`verify`** | **`{"pass": true, "entries": 2714, "issues": []}`** |

## 1. 实际执行的命令与退出码（可核对）

| 命令 | 退出码 |
|---|---|
| `.venv/bin/python -m unittest discover -s tests -v` | **0**（60 tests OK） |
| `.venv/bin/python r6.py execute` | **0** |
| `.venv/bin/python r6.py verify uploads/R6_feedback_20260912T183528217128Z.zip` | **0** |

依赖安装访问了包索引；实验命令禁用网络。**只运行一次完整批次**，未重跑、未删锁、未改源码/seed/阈值/数据/预算/参考哈希、未创建第二次运行挑选较好耗时。`execute` 实际耗时 14.311 s（脚本自报 `run_seconds`），本回复不编造耗时估计。

## 2. 独立审核结果（`audit/report.json`）

| 项 | 值 |
|---|---|
| `mechanical_pass` | **true** |
| `issues` | **[]（空）** |
| `source.pass` / `files` / manifest SHA | **true** / 39 / `f50e48d8fd36844d58cf18c12b21f7fcbdb6f16ce9faf6827c8bb6d285b7e632` |
| `calibration_workflow_events_checked` / `physical_calibration_workflows` | **40384 / 40384** |
| `runtime_task_records` | **20480** |
| `trajectories` / `base_streams` / `training_panels` | **2560 / 128 / 4** |
| `hard_budget_violations` | **[]（空）** |
| `new_llm_api_calls` | **0** |
| `reference_present` / **`reference_science_match`** | **true / true** |
| `scoped_probability_atol` / `rtol` | 1e-14 / 0 |
| **`max_probability_delta`** | **0.0** |
| `scientific_gate` | `PENDING_RESEARCHER_REVIEW` |

**跨平台验收全部通过，且比我预期的更严格**：`reference/science.json` 与本机 `reference_validation.json` **完全相等（`==` 判定为 True）** —— 2560 条轨迹的 `discrete_sha256`、20480 个预测点、`protocol_sha256` 全部一致；允许的 1e-14 浮点容差**实际未被用到**（`max_probability_delta = 0.0`）。即：动作、预算、答案、绑定严格一致，预测值也没有任何实际偏差。

## 3. 主结果：决策敏感选择**没有**稳定超越随机（阴性结果，按协议保留）

运行期 J = 任务失败 + 0.05 × 核验额度（**不是货币、不是墙钟**）；共同初始化 6 额度单列。下表为 4 条件 × 2 菜单合并（每方法 8 行 × 32 流）：

| 方法 | 成功 | 失败 | 核验额度 | 运行 J 合计 | J/回合 | 独立校准工作流/批 |
|---|---|---|---|---|---|---|
| **random_32** | **1722** | **326** | 1975 | **424.75** | **53.0938** | 1904 |
| **random_16** | **1722** | **326** | 1979 | 424.95 | 53.1188 | 1648 |
| single_only | 1717 | 331 | 1984 | 430.20 | 53.7750 | 1392 |
| full_joint | 1716 | 332 | 1972 | 430.60 | 53.8250 | 2992 |
| occupancy_32 | 1714 | 334 | 1977 | 432.85 | 54.1063 | 1904 |
| decision_32 | 1712 | 336 | 1975 | 434.75 | 54.3438 | 1904 |
| occupancy_16 | 1712 | 336 | 1975 | 434.75 | 54.3438 | 1648 |
| decision_16 | 1709 | 339 | 1974 | 437.70 | 54.7125 | 1648 |
| any_exact | 1693 | 355 | 2028 | 456.40 | 57.0500 | 0 |
| never | 1362 | 686 | 0 | 686.00 | 85.7500 | 0 |

**16/32 嵌套检查点的直接比较**（差值为正表示前者更差）：

| 对比 | 成功数差 | 运行 J 差 |
|---|---|---|
| `decision_16` vs `random_16` | **−13** | **+12.75** |
| `decision_32` vs `random_32` | **−10** | **+10.00** |
| `decision_16` vs `occupancy_16` | −3 | +2.95 |
| `decision_32` vs `occupancy_32` | −2 | +1.90 |
| `random_16` vs `occupancy_16` | **+10** | **−9.80** |
| `random_32` vs `occupancy_32` | **+8** | **−8.10** |

**随机选择在两个检查点上都优于决策敏感规则，也优于访问权重规则。**

### 3.1 配对区间（`paired.csv`，描述性、条件性）

`paired.csv` 112 行中的 `left==right` 行是同一部署内两菜单的对照，**不是方法间对比**（其均值约 −0.25～−0.30，不能读成"某方法胜自己"）。真正的方法间对比：

| 对比 | n | 平均 J 差 | left 胜 / 平 / 负 | CI 含 0 的对比数 |
|---|---|---|---|---|
| `full_joint` vs `single_only` | 8 | +0.00156 | 10 / 244 / 2 | — |
| `decision_32` vs `occupancy_32` | 8 | +0.00742 | 1 / 254 / 1 | — |
| `decision_16` vs `occupancy_16` | 8 | +0.01152 | 0 / 253 / 3 | — |
| `decision_32` vs `full_joint` | 8 | +0.01621 | 0 / 252 / 4 | — |
| `decision_16` vs `single_only` | 8 | +0.02930 | 3 / 251 / 2 | — |
| **`decision_32` vs `random_32`** | 8 | **+0.03906** | 1 / 250 / 5 | **8/8** |
| **`decision_16` vs `random_16`** | 8 | **+0.04980** | 0 / 251 / 5 | **8/8** |

`decision` vs `random` 的**全部 8 个条件×菜单对比的置信区间都包含 0** —— 即在该描述性区间下**无稳定差异可判**。脚本自带 `inference` 标注为 `descriptive_conditional_on_four_fitted_panels_not_confirmatory`。

**这与脚本自带文档一致**：README 与 `docs/REVIEW_LIMITATIONS_ZH.md` 已写明"决策敏感规则并未稳定超过随机选择"，并给出**停止条件**：*若在相同预算下不能稳定超过随机/简单选择，暂停该选择器的优越性主张；不要立即投入新的字段复制 LLM 实验。* 本轮数据支持该停止条件，**我不改变数据、不调 seed 去跑成胜利**。

## 4. 校准成本（每批 standalone；**不可把 16/32 前缀相加**）

`calibration_costs.csv` 表头即带 `do_not_sum_nested16_and32_as_actual_runs` 标注。

| 方法 | 标签执行 | 参考执行 | 总工作流 | 选择器秒(均) | 采集耗时秒(均) | 设计构建秒 |
|---|---|---|---|---|---|---|
| single_only | 1312 | 80 | **1392** | 0.00000 | 0.07304 | 0.0 |
| full_joint | 2912 | 80 | **2992** | 0.00001 | 0.15490 | 0.0 |
| random_16 / random_32 | 1568 / 1824 | 80 | 1648 / 1904 | 0.00007 / 0.00024 | 0.08785 / 0.10135 | 0.0 |
| occupancy_16 / 32 | 1568 / 1824 | 80 | 1648 / 1904 | 0.06491 / 0.12280 | 0.15564 / 0.23164 | 0.08568 |
| **decision_16 / 32** | 1568 / 1824 | 80 | 1648 / 1904 | **0.17528 / 0.32362** | 0.26362 / 0.42670 | 0.08568 |

**少采标签不等于本地更快**：`decision` 与 `random` 购买的工作流**完全相同**（1648 / 1904），但选择器计算时间高约 **2.4–2.7 倍**（0.175 vs 0.00007 s；0.324 vs 0.00024 s），采集总耗时也更高。这正是 `REVIEW_LIMITATIONS_ZH.md` 预警的"决策选择的计算可能比全部标签执行贵"。

## 5. 成本前沿（`cost_frontier.csv`）

含假想代价 `price_per_calibration_workflow` ∈ {0, 0.001, 0.01} × 部署次数 N ∈ {10, 100, 1000}，统一含 **0.3 初始化项**。脚本自带 `scope` 标注：`hypothetical_cost_sensitivity_not_currency_or_measured_deployment`。

示例（data_shift / shared）：`any_exact` 摊销后恒为 1.534375（校准工作流 0）；`decision_16` 在 λ=0 时为 1.6671875，λ=0.01、N=10 时升至 3.3151875。**这是设定敏感性，不是人民币、真实 API 账单或未来部署保证。**

## 6. 计时与规模（只运行一次，未挑最快）

`execution_summary.json` 自报：

| 项 | 值 |
|---|---|
| 起止 | 2026-09-12T18:34:49.381883+00:00 → 18:35:03.693007+00:00 |
| `run_seconds` | 14.311297875130549 |
| `training_and_design_seconds` | 4.397308792220429 |
| 物理训练工作流 | **40384**（含 1600 次正确参考） |
| 基础流 / 轨迹 / 任务记录 | 128 / 2560 / 20480 |
| `new_llm_api_calls` / `network_allowed` | 0 / false |
| 独立训练批次数 | 4 |
| `counts_note` | `budgets16/32 are nested checkpoints, not independent training runs` |

## 7. 输出包路径

```
/Users/user/代码/DeepSeek harness/REcheck/实验反馈/反馈10_R6_选择性交互校准_20260913/原始记录/R6_feedback_20260912T183528217128Z.zip
```

**verify 结果：`{"pass": true, "entries": 2714, "issues": []}`**

包内顶层分布：`kit_source/` 40、`run/` 2674、`BUNDLE_MANIFEST.json` 1。**密钥扫描 0 命中**（真实密钥与任意 `sk-` 模式均为 0），**不含** `config.local.json`、`.env`、`.key`、`.pem`。

## 8. 未解决的错误

**无。** `execute` 退出码 0、完整结束；`issues` 为空；`hard_budget_violations` 为空。未知事项（作者意图、计费、隐藏模型活动等）一律保留 **unknown**，不作猜测。

## 9. 边界声明（不越界）

- J 是"任务失败 + 0.05 × 核验额度"，共同初始化 6 额度单列；`cost_frontier.csv` 的 λ/N 为**假想敏感性**，**不是货币或已测部署节约**。
- 16/32 是**嵌套检查点**，共享过去；两者成本**不能相加**当作实际独立运行。四个训练批次才独立，每批 16 目录；同一流内步骤与多方法高度相关。
- 选择器只使用单项/已购买标签与固定假想公共状态网格；当前目录、真实模式、任务正确答案**均未进入在线调度**。公共相关通道由规范给出，**不是学习发现**。
- 本轮**没有**新增 RepairLens 实验，**没有**新通用 DP 定理，**不是**公开 benchmark 或跨领域迁移。只测 3 个语义通道、已知漂移。
- 同一研究助手自审 + 独立算术实现，**不是独立人类同行评审**；原始文件 SHA 只证明字节完整性。
- 我**未**声明方法成功、统计显著或达到投稿要求；最终判断由研究审核完成。完成后停止，不自动扩大运行。

## 文件

| 文件 | 说明 |
|---|---|
| `原始记录/R6_feedback_20260912T183528217128Z.zip` | **回传用**。2714 条目：校准购买账本、16/32 检查点、2560 条原始轨迹、代码快照、任务数据、统计、计时、清单 |
| `原始记录/execution_summary.json` | 起止 UTC、墙钟、物理工作流数、规模计数 |
| `原始记录/design_metadata.json` / `compilation.json` | 设计元数据与规划缓存计数 |
| `原始记录/manifest.json` / `status.json` | 冻结绑定与状态 |
| **`审核/report.json`** | **独立审核报告（本批次核心结论）** |
| `审核/summary.csv`（80 行） | 方法 × 条件 × 菜单统计 |
| `审核/paired.csv`（112 行） | 配对区间（描述性、条件性） |
| `审核/calibration_costs.csv` | 校准购买账本与分段计时 |
| `审核/cost_frontier.csv` | 假想 λ/N 成本敏感性 |
| `审核/reference_validation.json` | 与 `reference/science.json` **完全相等** |
| `审核/单元测试完整输出.txt` / `execute完整输出.txt` | 完整终端输出与退出码证据 |
