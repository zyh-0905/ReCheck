# 反馈 12：R7C 付费模型诊断 —— **在 smoke 关卡被阻断**

| 项 | 内容 |
|---|---|
| 协议 | `R7C_NATIVE_AGENT_DIAGNOSIS_01`（r7c-1.0.0） |
| 执行时间（原始 UTC） | prepare → smoke 于 **2026-09-13T08:00:06Z** 暂停；export 于 **08:00:14Z** |
| 环境 | 新建独立 `.venv`，Python **3.11.15**，固定依赖全部安装成功 |
| `prepare` | **退出码 0**，fingerprint `c09439b959ef49fa0f58f1bc6a47c629b75a9c696bb774bb78137d033a300bb8`，cap 385 |
| **`smoke --confirm-calls 1`** | **退出码 2 —— `status: paused`** |
| 主批次 `run` | **未运行**（被正确拒绝，见 §3） |
| **实际发出请求数** | **1 次**（上限 385，未发满） |
| 已完成 episode | **0 / 42 主 + 0 / 6 重复** |
| 方法先进性 / 录用结论 | **未宣布**（`scientific_gate: PENDING_RESEARCHER_REVIEW`） |

## 1. 执行到哪一步（逐步核实）

| 步骤 | 结果 |
|---|---|
| `python3.11 -m venv .venv` + `pip install -r requirements.txt` | **成功**（53 个固定依赖，含本地构建 `rouge-score`） |
| `.venv/bin/python r7c.py prepare` | **退出码 0** |
| `.venv/bin/python r7c.py smoke --confirm-calls 1` | **退出码 2，paused** |
| `.venv/bin/python r7c.py audit` | **退出码 0**，`mechanical_pass: true`、`issues: []` |
| `.venv/bin/python r7c.py export` | **退出码 0** |
| `.venv/bin/python r7c.py verify <zip>` | **`{"pass": true, "files": 121}`** |
| `.venv/bin/python r7c.py run --confirm-calls 384` | **退出码 2，`ValueError: Current-kit smoke must complete first`——未发出任何请求** |

## 2. 阻断原因（终端原始错误 + 保留的原始响应）

**终端原始报错（一字未改）：**

```
{"status": "paused",
 "error": "RunStopped: Returned model differs from requested exact ID. Raw response retained; no fallback.",
 "ended_utc": "2026-09-13T08:00:06.357160+00:00"}
```

保留的原始请求/响应事实（来自 `runs/R7C_smoke/attempts/000001_result.json`）：

| 字段 | 值 |
|---|---|
| `payload.model`（我方请求，协议固定） | **`deepseek-v4-flash`** |
| `response.model`（端点返回） | **`deepseek-flash`** |
| `system_fingerprint` | `aeb56401ca74e127821c4f9126dcb669` |
| `finish_reason` | **`stop`** |
| `usage` | prompt 48 / completion 21（其中 reasoning 15）/ total 69，字段完整 |
| 传输层 `status` | `ok`（即 HTTP 正常、未被截断、JSON 合法） |

**这不是网络或协议故障**：唯一触发暂停的是本包 `r7clib/transport.py:59-60` 的硬校验——

```python
if self.cfg["backend_kind"]=="live" and body.get("model")!=self.cfg["model"]:
    raise RunStopped("Returned model differs from requested exact ID. Raw response retained; no fallback.")
```

即要求"返回模型必须逐字等于请求的确切 ID"。端点在 `/v1/models` 中只列出 `deepseek-flash` 与 `deepseek-v4-pro` 两个 ID，因此请求 `deepseek-v4-flash` 必然返回 `deepseek-flash`，**该关卡必然暂停**。

按 prompt 第 4 条，我**没有**改回旧 `deepseek-flash`、**没有**换其他模型、**没有**重复 smoke、**没有** curl 试探（探针仅用于在执行前确认现状，未用于绕过）。

## 3. 主批次为何没有运行

`r7c.py run` 的第一道绑定检查是"当前 kit 的 smoke 必须 completed"；smoke 为 `paused`，因此 `run` 直接以 `ValueError: Current-kit smoke must complete first` 退出（退出码 2），**未发出任何模型请求**。这符合 README 第 3 节与协议的 `start_over_policy`：暂停/运行中/有锁的目录不自动恢复。

**本轮 384 次主批次全部未使用**；`no_more_paid_followup_authorized: true` 未被触发，也未申请扩大。

## 4. ZIP 路径

```
/Users/user/代码/DeepSeek harness/REcheck/实验反馈/反馈12_R7C付费模型诊断_阻断_20260913/原始记录/R7C_feedback_20260913T080014246462Z.zip
```

**verify 结果：`{"pass": true, "files": 121}`**，122 条目：

| 顶层 | 数量 |
|---|---|
| `kit_source/` | 112（源码快照） |
| `runs/R7C_smoke/` | 6（`attempts/000001_start`、`send_intent`、`result`；`calls/…`；`manifest.json`；`status.json`） |
| `offline_reports/` | 2（`AUDIT.json`、`calls.csv`） |
| `PREPARED.json` / `BUNDLE_MANIFEST.json` | 1 / 1 |

说明：`smoke_result.json` 与 `endpoint_identity.json` **不存在**，因为 smoke 在写入它们之前就抛出了 `RunStopped`——这是本包在失败路径上的正常行为，不表示记录丢失。

`uploads/` 内另有一份 `R7C_feedback_20260913T080006358087Z.zip`（120 条目），是 smoke 步骤内自动导出的快照；它**缺少** `offline_reports/AUDIT.json` 与 `offline_reports/calls.csv`。**请回传上面那一份（122 条目）。**

## 5. 审核结果（`offline_reports/AUDIT.json`）

| 项 | 值 |
|---|---|
| `mechanical_pass` | **true** |
| `issues` | **[]** |
| `new_model_calls` | **0**（审核只重建，不产生新模型答案） |
| `source.pass` / `files` / manifest SHA | **true** / 111 / `e7c011da97123b1b74296fbc09ebaa26c2f8b001ad592b916a820c0be2974e0e` |
| `evidence_kind` | `response_reconstruction_not_new_samples` |
| `planned_primary_episodes` / `completed_primary` | **42 / 0** |
| `planned_repeat_episodes` / `completed_repeat` | **6 / 0** |
| `requests_registered` / `reconstructed_requests` | **1 / 0** |
| `partial_data_note` | 缺失/暂停的 episode **不会**被静默计为成功，也不从计划分母中剔除 |
| `scientific_gate` | `PENDING_RESEARCHER_REVIEW` |

## 6. 尚未解决 / 未知

1. **阻断项**：请求 `deepseek-v4-flash` 时端点返回 `deepseek-flash`，本包含硬校验，故 smoke 暂停、主批次不可运行。这是**协议固定 ID 与端点实际 ID 之间的不一致**，需研究端决定如何处理。
2. **后端版本 unknown**：`system_fingerprint` 有记录，但**我不推测**两端点 ID 是否同权重、是否互为改名——README 本身即声明"不声称二者权重相同"。
3. **费用 unknown**：价格字段为 `UNKNOWN`，`385×16384=6,307,840` 只是"全部请求耗尽输出上限"的名义输出 token 上界，不是预计用量，也不含输入。本轮**实际只发 1 次请求**（48 prompt + 21 completion token），但我**不据此估算金额**，以服务商账单为准。
4. 未推测操作者动机、中断原因或隐藏模型活动。

## 7. 遵守的禁止事项

未触碰 R1—R7B 任何目录与数据；未修改源码/依赖版本/seed/提示/cap/参考结果；未删锁、未并行、未自动重试、未重复 smoke、未切换模型或端点；未把重复答案替代主结果（本轮无重复 episode）；**未启动官方 ToolSandbox CLI、未调用 RapidAPI、未发送真实短信或连接个人联系人**；未把 `fixtures/cases.json` 中的私有 gold 或变化标签送给模型；未创建仓库/付费账号/服务器，未提交论文。密钥仅经进程环境 `LLM_API_KEY` 传入，未写入命令参数、配置或日志，未读取 `.env`，未搜索旧项目凭据。

## 8. 声明

**未宣布方法先进或满足录用条件。** 本轮在 smoke 关卡被阻断，主实验结果**不存在**；`42 主 episode` 也本就不是 42 个独立样本。完成后停止，未自动启动任何后续实验或 RepairLens 调用。

## 文件

| 文件 | 说明 |
|---|---|
| `原始记录/R7C_feedback_20260913T080014246462Z.zip` | **回传用**。122 条目：原始请求/响应、逐轮动作与工具结果、快照、源码清单、审核报告 |
| `原始记录/000001_result.json` | **阻断证据**：请求 `deepseek-v4-flash` vs 返回 `deepseek-flash` 的原始响应 |
| `原始记录/status.json` / `manifest.json` | smoke 暂停状态（含原始错误串）与冻结绑定 |
| `审核/AUDIT.json` | 独立审核报告（`mechanical_pass: true`，0 个完成 episode） |
