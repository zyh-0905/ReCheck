# 反馈 06：R2 ReCheck 机制预实验

| 项 | 内容 |
|---|---|
| 任务 | `R2_RECHECK_MECHANISM_01`（r2-2.0.0） |
| 执行时间 | 2026-09-12 UTC 11:44–12:20（CST 19:44–20:20，约 36 分钟） |
| 模型 | `deepseek-flash`（= DeepSeek-V4.1-Flash） |
| 端点 | `https://api.deepseek.com/v1`（沿用，未改动） |
| 输出上限 | 16384，**显式发送** `{"thinking":{"type":"enabled"},"reasoning_effort":"high"}`，不发送 temperature |
| smoke | **1 次**，`json_ok=true`，finish=stop |
| 主实验 | **484 / 484** 次请求尝试，**240 / 240** 条记录 |
| HTTP 错误 / 截断 / JSON 失败 | **0 / 0 / 0** |
| 不确定中断 | 0（无 start 缺 result） |
| 本地检查 | `pass: true`（audit ledger + **replay_audit**） |
| 科学门 | `PENDING_RESEARCHER_REVIEW_NOT_AUTOMATIC_PASS` |
| 价格状态 | **UNKNOWN**（按 prompt 未填估算、未换汇、未沿用旧价目） |
| **本轮新增模型调用** | **485 次**（1 smoke + 484 主实验） |

## 1. 执行合规性

按 prompt 逐步执行，**未改进算法、未优化提示、未选参数**：

1. 确认 `r2.py`、`configs/r2_protocol.json`、`SOURCE_MANIFEST.json` 均在位；独立目录执行，未覆盖旧工程。
2. Python 3.11.15 + `numpy==2.3.5`；**91 个单元测试全通过**（仅本地 fixture，不访问模型）。
3. `prepare` → **offline_gate PASS**，`remote_model_calls: 0`，`trajectory_probe_disagreements: [0,0,4,4]`（与 README 预定值一致）。
4. 配置按 prompt 保留：端点、模型 ID、`max_tokens=16384`、`thinking=enabled`、`reasoning_effort=high`、temperature 不发送；费用保持 unknown。
5. 密钥仅从进程环境 `LLM_API_KEY` 读取，未写入任何配置/命令/日志，未读取 `.env`。
6. `smoke --confirm-calls 1` → 通过（返回模型 `deepseek-flash`，指纹 `aeb56401ca74e127821c4f9126dcb669`，与既往批次一致）。
7. smoke 通过后才执行 `run --confirm-calls 484`；运行中**只观察进度**，未挑样本、未中途改参、未运行 repairlens-readiness。
8. `audit` → PASS；`export` → 成功；`verify` → **`{"pass": true, "entries": 2327}`**。

**未**执行任何 retry/unlock、未删锁、未循环执行、未用新目录重新采样。

## 2. 核心结果（240 条记录 = 48 任务位置 × 5 策略）

| 策略 | 成功 | 成功率 | 探针数 | 陈旧相关失败 | 接口失败 | LLM 延迟(s) |
|---|---|---|---|---|---|---|
| recheck（DP） | 43/48 | **0.896** | 30 | 2 | 1 | 399.9 |
| myopic | 46/48 | **0.958** | 25 | 2 | 0 | 353.4 |
| ttl (TTL=3) | 43/48 | 0.896 | 32 | 5 | 0 | 380.5 |
| always | 47/48 | **0.979** | **96** | 0 | 1 | 359.7 |
| never（对照） | 42/48 | 0.875 | **0** | 4 | 2 | 285.2 |

**48 个任务位置**（4 流 × 12 步）是独立单元，**240 行不是 240 个独立样本**；真实独立单元只有 **4 条流**。

## 3. 分区设计按预注册精确生效（本批次最干净的正向证据）

| 区域 | 流 | recheck vs myopic 决策 | 预检查预言 | 实际 |
|---|---|---|---|---|
| **0.18 等价区** | 0, 1 | **12/12 完全相同** | 0 个差异 | **0 个差异** ✓ |
| **0.22 分离区** | 2 | 不同步骤 = [1, 4, 9, 10] | [1, 4, 9, 10] | **完全一致** ✓ |
| **0.22 分离区** | 3 | 不同步骤 = [1, 2, 3, 9] | [1, 2, 3, 9] | **完全一致** ✓ |

合计 8 个轨迹决策差异，全部落在 0.22 区。**预检查在没有构造隐藏模式、没有读取答案的情况下准确预言了分歧位置** —— 这条是本轮可复现的机制性发现。

## 4. 关键阴性结果：DP 在分离区没有兑现优势

- 总体：**recheck 0.896 < myopic 0.958**，且 recheck 探针更多（30 vs 25）。
- 分离区逐流（12 步）：
  - 流 2（0.22 / 无漂移）：recheck 11 胜 7 探针；**myopic 12 胜 5 探针**
  - 流 3（0.22 / 有漂移）：recheck 11 胜 7 探针；myopic 11 胜 4 探针
- 即：**设计确实制造了分歧机会（8 处），分歧也确实发生了，但 DP 既没有更准，还多花探针。**
- 这说明 DP 的"最优"仅对其声明的最小化代理代价成立，**未转化为本模型的端到端正确率**。

## 5. 失败归因分解（240 行）

| 策略 | 成功 | 仅接口违规 | 仅陈旧 | **陈旧无关的错误** |
|---|---|---|---|---|
| recheck | 43 | 1 | 2 | **2** |
| myopic | 46 | 0 | 2 | 0 |
| ttl | 43 | 0 | 5 | 0 |
| always | 47 | 1 | 0 | 0 |
| never | 42 | 2 | 4 | 0 |
| **合计** | **221** | **4** | **13** | **2** |

**陈旧传播一致性**：所有含陈旧记忆的行（13 行）**100% 与陈旧一致**——陈旧必然导致错误，没有一例"陈旧却答对"。反之，**19 个失败中有 6 个与陈旧无关**。

### 5.1 四例接口违规（计划 schema 非法 → 工具拒绝执行）

| 位置 | 策略 | 违规内容 |
|---|---|---|
| s0 t4 | recheck | `amount_divisor=1`，但该题只需 count，必须为 `null` |
| s2 t0 | never | `time_bound=8`，超出 cutoff=9 允许窗口 [8,11] 的下界 |
| s2 t1 | always | `time_bound=13`，超出 cutoff=14 允许窗口 [13,16] 的下界 |
| s3 t8 | never | `time_bound=9`，超出 cutoff=10 允许窗口 [9,12] 的下界 |

模式清楚：模型**没有读取任务中的 cutoff 数值**来生成边界，而是给了偏移值，落在允许窗口之外被判非法。

### 5.2 两例"记忆新鲜却算错"（重点发现，与 R1 同源）

| 位置 | 策略 | 工具返回 | 模型答案 | 偏差 |
|---|---|---|---|---|
| s1 t7 | recheck | count_before=9（即正确值） | **11** | **+2** |
| s2 t5 | recheck | count_before=11（即正确值） | **12** | **+1** |

同一位置的其他四个策略**全部把工具返回值原样输出**（myopic/always 给 9，ttl/never 给 10），只有 recheck 擅自加数。

读该行 `reasoning_content`（22475 字符）可见模型明确纠结：

> "The key `count_before` suggests number before cutoff, not including? … If `endpoint_inclusive` true, then if there are orders exactly at 8, count could be `count_before` + number at 8?"

**根因（工具设计层面的问题，非模型缺陷）**：工具字段名 `count_before` 暗示"不含端点"，而记忆里 `endpoint_inclusive=true` 又暗示"要包含"，两者对模型的字面语义互相冲突。工具返回的计数**其实已经是**按真实端点语义算好的最终值（`World.execute` 依 `self.mode[1]` 选择 `<` 或 `<=`），但字段名让模型以为还要再修正一次。

此外 `memory.checked_at` 的值等于当前步号（如 `[8,8]` 出现在第 8 步），这**看起来**像"刚刚检查过"，也是潜在的误导源（它是相对初始检查的计数，不是时间戳）。

**这是本轮与 R1 一致的复发模式**：R1 的 `rc_001_001_ttl` 也是"记忆正确却用错除数"。两轮合计 3 例此类错误，**说明模型在把工具原始值转换成最终答案时会偶发地重复施加语义**。

## 6. 重放审计（本轮最强的一致性证据）

`replay_audit.json`：

```json
{"pass": true, "request_bodies_checked": 484, "completed_calls_consumed": 484,
 "stop_reason": null, "request_mismatches": [], "artifact_mismatches": [],
 "unconsumed_calls": [], "new_model_calls": 0}
```

含义：用**冻结的响应**在临时目录重建全部 484 个请求体与 SQLite 记录，**逐字节比对全部一致**（仅排除三个本地耗时字段）。这证明：请求构造与实验逻辑是确定性的、可复现的，且**没有新模型调用**。

## 7. 真实 token 与成本

| 指标 | 数值 |
|---|---|
| prompt tokens | 117,707（缺失 0） |
| completion tokens | 351,640（缺失 0） |
| 其中 reasoning tokens | **345,640（98.3%）** |
| 本地列表价估算 | **全为 null（unknown×484）** |
| 记录的调用总墙钟 | 2030.6 s |

按 prompt 要求，**费用保持 unknown**：未填入任何单价、未换汇、未沿用旧价目。因此本轮**只能**分析 tokens 与延迟，**不能**给出金额结论。

## 8. 离线成本诊断（零新增 RepairLens 调用）

`REPAIR_COST_DIAGNOSTIC.json`（基于 R1 预检的冻结记录，标签 `PRIOR_R1_READINESS_NOT_REPAIRLENS_ALGORITHM`）：

- 局部修补调用比 = 0.833（比全量少 16.7% 调用）
- **局部修补成本比 = 2.224**（反而更贵 —— 选择调用本身昂贵）
- 选择成本 / 全量生成成本 = 1.721
- **选择成本 / 省下的生成成本 = 3.459**（选择花的钱是省下的 3.5 倍）
- 结论：`R2 pauses new RepairLens API trials. Need net-cost policy with a direct-recompute fallback.`

**本轮未新增任何 RepairLens 模型调用**，符合授权范围。

## 9. 必须写明的限制（不替研究做解释）

1. **4 条流**是唯一独立单元，**不支持确证性结论或 p 值**。
2. 科学门为 `PENDING_RESEARCHER_REVIEW_NOT_AUTOMATIC_PASS` —— 本地检查通过**不等于**科研结论成立，也**不等于**达到任何录用要求。
3. 0.18/0.22 是**控制器内的无量纲代价**，不是人民币或 API 单价，**不可与账单相加**。
4. 参数 0.18/0.22 是**看过 R1 策略分析后**选的，属开发性设计，**不是外部预注册**。
5. 本轮结论均为**阴性/中性**：DP 未优于 myopic；always 正确率最高但探针是 recheck 的 3.2 倍；never 零探针仍有 87.5%。
6. 中断原因、计费、后端权重、操作者动机 —— **不知道就是 unknown**。

## 10. 需操作者与研究助手注意

- **未修改**协议、种子、阈值与 `SOURCE_MANIFEST.json`；`source_snapshot_mismatches` 为空。
- `uploads/` 内有三个 ZIP：`...T114451...` 是 smoke 后自动导出，`...T121846...` 是主实验结束时导出，**`...T121950...`（本文件夹内）是最终 export，含重放审计，是回传用的那一份**。
- 本文件夹的 README 与 `审核/` 下的分析由本地助手撰写；**不得**替代研究助手的独立判断。

## 文件

| 文件 | 说明 |
|---|---|
| `原始记录/R2_feedback_20260912T121950_472258Z.zip` | **回传用**。2327 条目：smoke + 主实验全部原始请求/响应/尝试、共同前缀、工具返回、隐藏评测数据、代码快照、离线审查 |
| `原始记录/summary.json` / `per_task.csv` / `per_call.csv` / `method_summary.csv` / `SUMMARY.md` | 离线汇总 |
| `原始记录/replay_audit.json` | 重放审计结果 |
| `原始记录/run_events.jsonl` | 调用起止与墙钟记录 |
| `原始记录/manifest.json` / `status.json` | 冻结配置与状态 |
| `审核/PREFLIGHT.json` | 预检查（分区预言） |
| `审核/REGRESSION.json` | 用 R1 真实失败记录做的回归核对 |
| `审核/REPAIR_COST_DIAGNOSTIC.json` | 离线成本诊断 |
| `审核/PREPARED.json` | 配置/协议/代码哈希绑定 |
