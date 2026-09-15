# 反馈 13：R7C1 原生 ToolSandbox Agent 诊断 —— **完成**

| 项 | 内容 |
|---|---|
| 协议 | `R7C1_NATIVE_AGENT_DIAGNOSIS_01` / **version `r7c-1.0.1`** ✔ 与 prompt 要求一致 |
| 包名校验 | 唯一允许包 `Research_Handoff_R7C1.zip`；本目录即新解压的 `R7C1_Research_Kit` |
| 源码绑定 | `SOURCE_MANIFEST.json` **116/116 文件哈希一致**（`source.pass: true`） |
| 执行时间（原始 UTC） | prepare → smoke **08:44:46Z**；主批次 **08:44:51Z → 08:49:22Z**（墙钟 270.5 s）；export **08:49:47Z** |
| 解释器 | 复用 `R7C_Research_Kit/.venv` 的 3.11.15（**工作目录与 `r7c.py` 均来自新 R7C1 根目录**，旧研究目录未操作） |
| **最终状态** | **`completed`**（smoke 与主批次均 completed） |
| **账本内请求数** | **169**（新 smoke 1 + 主批次 **168**；上限 385，**未发满、未补足**） |
| 完成的 episode | **42/42 主 + 6/6 重复** |
| **wrong_write** | **0**（全部 48 个 episode） |
| 科学门 | `PENDING_RESEARCHER_REVIEW` |

## 1. 先检查状态（prompt 第一步，只读）

| 检查项 | 结果 |
|---|---|
| `protocol.json` | `R7C1_NATIVE_AGENT_DIAGNOSIS_01` / `r7c-1.0.1` ✔ |
| `PREPARED.json` | **不存在** |
| `.run.lock` | **不存在** |
| `runs/R7C_smoke/status.json` | **不存在** |
| `runs/R7C_main/status.json` | **不存在** |
| `runs/` 目录 | **不存在** |

→ 命中 prompt 第 6 条分支：**两批次都未开始、无遗留请求**，故准备环境并各执行一次 `prepare` / `smoke` / `run`。**未创建第二份目录绕过停止限制**；旧 `R7C_Research_Kit` 及其 `paused` 状态保持原样（其 `status.json` 现仍为 `paused` / `ended_utc: 2026-09-13T08:00:06Z`，未被改动）。

## 2. 执行到哪一步（逐步核实）

| 步骤 | 退出码 | 结果 |
|---|---|---|
| `r7c.py prepare` | **0** | fingerprint `6f5ad5d42981bb36593df14d8d90d858186f83b2c6bedb6eae8128036b8af921`，cap 385 |
| `r7c.py smoke --confirm-calls 1` | **0** | **`completed`**，`json_ok: true`、`shape_ok: true` |
| `r7c.py run --confirm-calls 384` | **0** | **`completed`**，168 次请求 |
| `r7c.py audit` | **0** | `mechanical_pass: true`，`issues: []` |
| `r7c.py export` | **0** | — |
| `r7c.py verify <zip>` | **0** | `{"pass": true, "files": 1070}` |

**原始错误：无。** 未出现 HTTP 错误、截断（`finish_reason` 全为 `stop`）、非法 JSON、usage 缺失或身份字段变化。

## 3. 响应标签政策与批次内锁定（本版本的核心修订）

smoke 时按 `R7C1_RESPONSE_LABELS_V1` 建立的**唯一 cohort**（写入 `runs/R7C_smoke/endpoint_identity.json`，主批次继承）：

```json
{
  "policy_id": "R7C1_RESPONSE_LABELS_V1",
  "requested_model": "deepseek-v4-flash",
  "returned_model": "deepseek-flash",
  "system_fingerprint": "aeb56401ca74e127821c4f9126dcb669",
  "weight_identity_verified": false
}
```

- **请求 model 始终为 `deepseek-v4-flash`**（未替换任何名称）。
- 返回标签 `deepseek-flash` 落在本版本显式允许清单 `('deepseek-v4-flash','deepseek-flash')` 内，因此 smoke 通过 —— 这正是上一轮 R7C 被阻断的那一点。
- 批次内 169 次调用的返回标签与指纹**完全一致**（返回模型集合 = {`deepseek-flash`}，指纹集合 = {`aeb56401…`}）。
- 审计自报：`response_label_policy: "R7C1_RESPONSE_LABELS_V1; smoke establishes a single returned-label/fingerprint cohort, not verified weights"`，且 `weight_identity_verified: false`。
- **我不推断该标签等于真实权重、也不断言与历史 `deepseek-flash` 同权重。**

## 4. 结果（`offline_reports/summary.csv`）

| 阶段 | 臂 | 完成/计划 | safe_success | **wrong_write** | 模型调用 | 工具调用 |
|---|---|---|---|---|---|---|
| primary | stateless | 14/14 | **14** | **0** | 51 | 37 |
| primary | inherited | 14/14 | **14** | **0** | 49 | 35 |
| primary | resolve_rule | 14/14 | **14** | **0** | 49 | 35 |
| repeat | stateless | 2/2 | 2 | 0 | 7 | 5 |
| repeat | inherited | 2/2 | 2 | 0 | 6 | 4 |
| repeat | resolve_rule | 2/2 | 2 | 0 | 6 | 4 |

**三臂在本批次上没有可区分的差异：全部 14/14 安全成功、0 误写。** 唯一的量级差别是 `stateless` 多用了 2 次模型调用（51 vs 49）与 2 次工具调用（37 vs 35）；但按 prompt，我**不据此宣布任何臂优越**，也**不宣布方法先进或满足录用条件**。

## 5. 重复诊断（`offline_reports/repeats.csv`）

6 对重复的初始输入**全部严格相同**（`same_initial_messages: True`，6/6），主/重复均安全成功（6/6 与 6/6），但：

**`same_actions: False` —— 6/6 对的动作序列都不同。**

即：**相同输入下模型自主轨迹不稳定**（与 R7C 协议"重复仅初始输入/状态严格相同；若自主轨迹不同，后续请求也可不同"一致）。重复**未替换主结果**，未采用 best-of-two。

## 6. 每回合轮数（`offline_reports/episodes.csv`，48 行）

| 阶段/臂 | 模型调用分布 | 工具调用分布 |
|---|---|---|
| primary / stateless | 3相×6, 4相×7, 5相×1 | 2相×6, 3相×7, 4相×1 |
| primary / inherited | 3相×8, 4相×5, 5相×1 | 2相×8, 3相×5, 4相×1 |
| primary / resolve_rule | 3相×8, 4相×5, 5相×1 | 2相×8, 3相×5, 4相×1 |

全部 episode 的 `safe_success` 与 `goal_achieved` 均为 True、`wrong_write` 均为 False、`terminated` 均为 True（即**都自行给出 `done` 结束**，未撞 8 轮上限）。

## 7. 真实 token 与延迟（本地记录，**不是发票**）

| 分组 | 调用 | prompt | completion | 其中 reasoning | 延迟 |
|---|---|---|---|---|---|
| 主批次 | 168 | 322,402 | 13,687 | 7,672 | 186.0 s |
| smoke | 1 | 48 | 23 | 17 | 0.9 s |
| **合计** | **169** | **322,450** | **13,710** | **7,689** | **186.9 s** |

- 缺失 usage 的调用：**0**；估价：**全部 unknown**（未填单价、未换汇）。
- 费用 **UNKNOWN**；`385×16384` 只是名义输出上界，**不是预计用量**，本轮实际只用了 168/384 次请求、13,710 输出 token。**我不据此估算金额**，以服务商账单为准。

## 8. 审核结果（`offline_reports/AUDIT.json`）

| 项 | 值 |
|---|---|
| `mechanical_pass` | **true** |
| `issues` | **[]** |
| `new_model_calls` | **0**（审核仅用已有响应重建，不产生新答案） |
| `source.pass` / `files` / manifest SHA | **true** / 116 / `4c20c6b6f88cd2314792d647c35e191ce1c530ba041f40b08dacfdebb1f2cfa1` |
| `evidence_kind` | `response_reconstruction_not_new_samples` |
| `smoke_status` / `run_status` | **completed / completed** |
| `planned_primary` / `completed_primary` | **42 / 42** |
| `planned_repeat` / `completed_repeat` | **6 / 6** |
| `requests_registered` / `reconstructed_requests` | **169 / 168** |
| `execution_complete` | **true** |
| `partial_data_note` | 缺失/暂停的 episode 不会被静默计为成功，也不从计划分母中剔除 |
| `grouping_note` | 14 构造情形、3 意图模板、2 工具领域；**不是独立基准样本** |
| `scientific_gate` | `PENDING_RESEARCHER_REVIEW` |

## 9. 交付 ZIP

```
/Users/user/代码/DeepSeek harness/REcheck/实验反馈/反馈13_R7C1原生Agent诊断_完成_20260913/原始记录/R7C1_feedback_20260913T084947017083Z.zip
```

**verify：`{"pass": true, "files": 1070}`**，1071 条目：

| 顶层 | 数量 |
|---|---|
| `runs/`（smoke + 主批次全部原始请求/响应/动作/工具结果） | 947 |
| `kit_source/` | 117 |
| `offline_reports/` | 5（`AUDIT.json`、`calls.csv`、`episodes.csv`、`repeats.csv`、`summary.csv`） |
| `PREPARED.json` / `BUNDLE_MANIFEST.json` | 1 / 1 |

`uploads/` 内另有两份更早的快照（`…T084446…` 120 条目、`…T084922…` 1066 条目），**均缺少 `offline_reports/` 的 5 份审核文件**。**请回传上面这一份（1071 条目）。**

密钥扫描：真实密钥 **0** 命中、任意 `sk-` 模式 **0** 命中；**不含** `config.local.json`、`.env`、`.key`、`.pem`。

## 10. 遵守的边界

未修改任务、提示、seed、轮数、源码、参考 hash、停止条件与评分；未替换 model、未做 `GET /models`、余额检查、curl 探针或 SDK 聊天测试；未启动上游 CLI / 用户模拟器 / RapidAPI；未把重复回合替换主回合、未删除失败、未重采样、未自动重试；未删锁；工具只作用于包内模拟数据，**未连接任何私人联系人、短信或提醒服务**；密钥仅从 `LLM_API_KEY` 环境变量读取，未写入聊天/命令参数/报告/配置，未读 `.env`，未搜索旧工程凭据。

## 11. 声明

**未宣布方法先进或满足录用条件**；本批次三臂**无可区分差异**，且 42 主 episode **不是 42 个独立样本**。费用、真实权重身份、操作者动机均保留 **UNKNOWN**。完成后停止，未启动后续实验或 RepairLens 调用。

## 文件

| 文件 | 说明 |
|---|---|
| `原始记录/R7C1_feedback_20260913T084947017083Z.zip` | **回传用**。1071 条目：原始请求/响应、逐轮动作与工具结果、状态、快照、私有评分对象、源码与清单、5 份审核报告 |
| `原始记录/endpoint_identity.json` | 批次内锁定的返回标签与指纹 cohort |
| `原始记录/status.json` / `smoke_result.json` / `PREPARED.json` | 状态、冒烟结果与冻结绑定 |
| `审核/AUDIT.json` | 独立审核报告（`mechanical_pass: true`，42/42 + 6/6） |
| `审核/summary.csv` / `episodes.csv` / `repeats.csv` / `calls.csv` | 逐臂汇总、逐 episode、重复诊断、逐调用明细 |
