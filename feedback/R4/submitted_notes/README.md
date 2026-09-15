# 反馈 08：R4 共享探测与硬预算下的证据刷新

| 项 | 内容 |
|---|---|
| 协议 | `R4_BUNDLE_BUDGET_01`（r4-4.0.0） |
| 执行时间 | 2026-09-12 UTC 15:37–15:53（CST 23:37–23:53，约 16 分钟） |
| **模型返回名称** | **`deepseek-flash`**（请求 ID 与返回 ID 一致，408/408） |
| system_fingerprint | `aeb56401ca74e127821c4f9126dcb669`（全程唯一） |
| 端点 | `https://api.deepseek.com/v1`（沿用；复用历史配置**不是**当前权重证明） |
| 请求配置 | `max_tokens=16384`、`thinking=enabled`、`reasoning_effort=high`、**不发送 temperature** |
| smoke | **1 次**，`json_ok=true`，finish=stop |
| 主批次 | **408 / 408**（384 primary + 24 repeat） |
| 记录 | **408 / 408** |
| **脚本报告调用数** | `registered_attempts: 408`、`responses: 408`、`completed_call_records: 408`、`uncertain: 0` |
| **是否出现错误** | **无**：HTTP 错误 0、截断 0（finish 全为 stop）、非法 JSON 0、usage 异常 0、身份字段变化 0、计划 schema 非法 0、预算违规 0 |
| 本地检查 | `pass: true`（ledger + **replay_audit 408/408 零失配**） |
| 科学门 | `PENDING_RESEARCHER_REVIEW` |
| 价格状态 | **UNKNOWN**（未填单价、未换汇、未用旧费率） |
| **本轮新增模型调用** | **409 次**（1 smoke + 408 主批次，未超授权） |
| RepairLens 新增调用 | **0** |

## 最终状态：**COMPLETED**

## 实际命令与退出码

| 命令 | 退出码 |
|---|---|
| `.venv/bin/python -m unittest discover -s tests -v` | 0（**65 tests OK**，给足时限，未因超时改测试） |
| `.venv/bin/python r4.py prepare` | 0（`offline_gate: PASS`，`remote_model_calls: 0`） |
| `.venv/bin/python r4.py smoke --confirm-calls 1` | 0 |
| `.venv/bin/python r4.py run --confirm-calls 408` | 0 |
| `.venv/bin/python r4.py audit` | 0（两 run 均 `pass: true`） |
| `.venv/bin/python r4.py export` | 0 |
| `.venv/bin/python r4.py verify <zip>` | 0（`{"pass": true, "entries": 2206}`） |

未执行 curl 或自写 API 探测、未调用额外模型、未执行 unlock/retry、未删锁、未续跑 paused 目录、未加 cap、未新建另一实验目录重采样、未改源码/参数/seed/测试/清单。

## 主结果（只用第一次调用；384 行 = 96 × 4 方法）

| 条件 | 方法 | 成功/24 | 成功率 | 额度消耗 | 语义损失 | 代理 J（**非货币**） |
|---|---|---|---|---|---|---|
| overlap_matched | bundle_rollout | **22** | **0.917** | 23 | 2 | **3.15** |
| | recheck_joint | 20 | 0.833 | 23 | 4 | 5.15 |
| | bundle_myopic | 18 | 0.750 | 24 | 9 | 10.20 |
| | age_paced | 18 | 0.750 | 23 | 7 | 8.15 |
| disjoint_matched | recheck_joint | **13** | **0.542** | 24 | 13 | 14.20 |
| | bundle_rollout | **13** | **0.542** | 24 | 12 | 13.20 |
| | bundle_myopic | 12 | 0.500 | 24 | 12 | 13.20 |
| | age_paced | 12 | 0.500 | 24 | 15 | 16.20 |
| overlap_no_drift | 全部四种 | **24** | **1.000** | 23–24 | 0 | 1.15–1.20 |
| overlap_underestimated | bundle_rollout | **17** | **0.708** | 23 | 9 | **10.15** |
| | age_paced | 16 | 0.667 | 23 | 10 | 11.15 |
| | recheck_joint | 15 | 0.625 | 22 | 10 | 11.10 |
| | bundle_myopic | 14 | 0.583 | 24 | 13 | 14.20 |
| **ALL（描述性）** | **bundle_rollout** | **76/96** | **0.7917** | 94 | 23 | **27.70** |
| | recheck_joint | 72/96 | 0.7500 | 93 | 27 | 31.65 |
| | age_paced | 70/96 | 0.7292 | 93 | 32 | 36.65 |
| | bundle_myopic | 68/96 | 0.7083 | 95 | 34 | 38.75 |

**12 条独立流**是唯一独立单元（每条件仅 3 条）；**384 行不是 384 个独立样本**。表格中的 `ALL_DESCRIPTIVE_ONLY` 标签是脚本自带的，不同条件不应盲目合并。无确认性 p 值。

## 关键发现：本轮 LLM 与"同公开输入的规则执行器"成绩**完全相同**

| 方法 | LLM 成功 | 规则执行器成功（非 LLM） | 计划遵循证据 | 接口失败 |
|---|---|---|---|---|
| recheck_joint | 72 | **72** | 384/384 | 0 |
| bundle_rollout | 76 | **76** | 384/384 | 0 |
| bundle_myopic | 68 | **68** | 384/384 | 0 |
| age_paced | 70 | **70** | 384/384 | 0 |

- **计划字段与 `rule_plan(view)` 逐字节相同：384/384。**
- **计划 schema 合法：384/384**；工具执行返回 `INVALID_PLAN`：**0/384**。
- 含义：在 R4 这个窄输出契约下（计划 = 复制公开 request + 照抄 evidence），**模型没有引入任何计划编译误差**；方法间成绩差异**完全来自调度实验臂**，不来自模型能力。计划编制时间也印证了这点：`bundle_rollout`/`bundle_myopic`/`age_paced` 接近 0 秒，只有 `recheck_joint` 有约 0.97 s 的本地 DP 构建时间（那**不是** API 成本）。

## 错误 100% 归因于记忆陈旧（与 R3 一致）

| 记忆状态 | 答对 | 答错 |
|---|---|---|
| **陈旧** | 3 | **98** |
| **新鲜** | **283** | 0 |

**新鲜时错误率 0.0000**；陈旧时 0.9703。

### 3 例"陈旧却答对"的机制（重要环境边界）

这 3 例**全部只涉及 `first_page` 一个通道陈旧**，且方向都是"真实=0、记忆=1"。逐流验证后确认：

- 执行器从 `first_page` 开始**持续翻页直到 `has_more=false`**，所以 `start=0` 与 `start=1` 最终**收集到完全相同的行集合**（在全部 12 条流上均相同）。
- 反过来（真实=1、记忆=0）会第一步就取到 `{"error":"PAGE_BEFORE_FIRST"}` 而失败。

因此 `first_page` 在本环境里是**单向不对称**的：

| 陈旧通道 | 答错 | 答对 |
|---|---|---|
| `(0,)` = first_page | 26 | **3** |
| `(1,)` = active_code | 23 | 0 |
| `(2,)` = stock_semantics | 35 | 0 |
| 多通道组合 | 14 | 0 |

**这是"陈旧必然导致错误"的一个已知例外**，属环境设计产物，不是模型能力。

## 成对处理（288 对 primary）

| 指标 | 数量 |
|---|---|
| 请求/证据真正不同（`relevant_semantic_difference`） | **49** |
| 校准包选择不同（`packet_difference`） | 150 |
| 覆盖集不同（`coverage_difference`） | 150 |
| 实际请求体不同（`payload_difference`） | **49** |

注意：**150 处选包差异中只有 49 处真正改变了给模型的证据** —— 与 R2/R3 同一模式（动作差异多于语义差异）。

在 49 个语义真正不同的对上，`recheck_joint`（精确联合 DP）**并未占优**：

| 对比 | 对 | joint 胜 | 对方胜 |
|---|---|---|---|
| joint vs bundle_rollout | 8 | 1 | **5** |
| joint vs bundle_myopic | 24 | **11** | 7 |
| joint vs age_paced | 17 | **7** | 5 |

全体 288 对上 `bundle_rollout` 的总体成功率（0.7917）与代理 J（27.70）都优于 `recheck_joint`（0.7500 / 31.65）。**我不能据此宣称任何方法优越** —— 每条件仅 3 条流，且这是脚本自带描述性汇总。

## 独立重复诊断（24 对，零 best-of-two）

| 指标 | 结果 |
|---|---|
| 请求体相同 | **24/24** |
| 计划相同 | **24/24** |
| 答案相同 | **24/24** |
| 可见文本相同 | **24/24** |
| 重复被扣额度 | **0**（`budget_violations` 中无 `repeat_charged`） |

与 R3 相同：窄输出契约下**相同输入无输出差异**。重复开销 24 次调用 / 6,316 输出 token，**单列并计入总量**，未替换主答案、未影响后续状态。

## 硬预算执行核查

- `budget_violations: []` —— 每流每方法逐步核对 `budget_before` / `budget_after` / `credits_spent` 一致性，无越界、无负余额。
- 单轮上限 4 额度、8 任务期间共 8 额度，由工具层检查并扣减；失败准入**不查询**。
- 逐方法额度消耗 93–95（`credit_units` 是**受控配额，不是人民币/美元/token/耗时**）。
- 共同初始化校准：12 流 × 3 通道检查 ≈ 6 等价额度/策略，**在运行期预算之外，对各方法一致**（`startup_excluded_from_runtime_budget: true`）。

## 真实 token 与延迟

| 指标 | 数值 |
|---|---|
| prompt tokens | 136,240（缺失 0） |
| completion tokens | 121,777（缺失 0） |
| 其中 reasoning tokens | **106,036（占输出 87.1%）** |
| 重复诊断输出 token | 6,316（24 次） |
| 模型延迟合计 | 695.9 s |
| run 墙钟 | 901.7 s |
| 本地估价 | **全部 unknown** |

**按 prompt 要求不给金额结论**：未填单价、未换汇、未用旧费率。次数上限 409 只是请求次数上限，**不是账单金额上限**。

## 离线报告（零模型调用）

- `PREFLIGHT.json`：`pass: true`、`worlds_constructed: false`、`new_model_calls: 0`；4 条件 × 12 流全部保留，**包括无漂移与不利条件**。
- `EXACT_GRID.json`：**72 组**给定模型条件，标签 `EXACT_FINITE_MODEL_NOT_LLM`（**不是真实 LLM 成绩**）。
- **反例（counterexample）**：`independent_singleton_costs = [2,2,2]`（合计 6）＞ `step_cap = 4`，`independent_all_is_feasible: false`；而 `one_pair_packet_cost = 3`。这形式化了"独立动作需要联合可行性/覆盖决策，且所有方法必须拿到相同包目录"。
- `REPAIR_COST_DIAGNOSTIC.json`：`new_llm_calls: 0`，两条路径均判 `direct_recompute`（认证节省为 **负**），限制原文保留（历史点成本**不是**未来有效上界）。

## 必须写明的限制

1. **12 条流**（每条件 3 条）是唯一独立单元；无确认性 p 值；不同条件不可盲目合并。
2. **R4 不是公开 benchmark**、不是生产 API、不是 AppWorld；任务是本地可控 JSON API。
3. 本环境**不是自由长程 Agent**：模型只把公开请求编译为有限工作流计划，最终答案由确定性执行器给出。
4. 任务输出**本轮不更新调度信念**（只有收费校准更新）—— 这是有限模型范围，**不能改写成已解决未知漂移学习**。
5. 额度和 0.05 损失权重**不是货币**；联合 DP、覆盖选择、rollout 均有传统研究，**不因加入硬预算就声称新定理**。
6. 未猜操作者动机、中断原因、后台模型版本、账单、峰谷与星期 —— **不知道就是 unknown**。
7. `separable_projected` 与 `never` **只在离线表格中**，未冒充 LLM 成绩。
8. **我未判断任何方法优越**；上表计数为原始观察值，解释权归研究端。

## 产出的 ZIP（可能有多个）

| ZIP | 生成时机 | 是否回传 |
|---|---|---|
| `R4_feedback_20260912T153747_465507Z.zip` | smoke 后自动导出 | 否 |
| **`R4_feedback_20260912T155338_644551Z.zip`** | **主批次完成后的最终 export（含 replay_audit）** | **是** |

## 反馈 ZIP 完整路径

```
/Users/user/代码/DeepSeek harness/REcheck/实验反馈/反馈08_R4_共享探测硬预算_20260912/原始记录/R4_feedback_20260912T155338_644551Z.zip
```

**verify 结果：`{"pass": true, "entries": 2206}`**

## 文件

| 文件 | 说明 |
|---|---|
| `原始记录/R4_feedback_20260912T155338_644551Z.zip` | **回传用**。2206 条目：smoke、全部主/重复原始记录、工具轨迹、校准收据、预算扣减、代码与 LICENSE、私有合成评测数据、离线审核、哈希清单 |
| `原始记录/summary.json` / `method_summary.csv` / `per_task.csv` / `per_call.csv` / `SUMMARY.md` | 离线汇总（主结果、重复诊断、规则执行器分开） |
| `原始记录/replay_audit.json` | 重放审计：408/408 请求体零失配重建 |
| `审核/EXACT_GRID.json` / `PREFLIGHT.json` / `REGRESSION.json` / `REPAIR_COST_DIAGNOSTIC.json` / `PREPARED.json` | 离线精确表、预检查与反例、回归、成本门槛、哈希绑定 |
