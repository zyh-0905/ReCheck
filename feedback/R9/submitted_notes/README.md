# 反馈 14：R9 实时续行诊断 —— **在首个主请求即暂停**

| 项 | 内容 |
|---|---|
| 协议 | `R9_LIVE_CONTINUATION_DIAGNOSIS_01` / **`r9-1.0.0`** ✔ |
| 源码绑定 | `SOURCE_MANIFEST.json` **120/120 文件哈希一致**（`source.pass: true`） |
| 执行时间（原始 UTC） | prepare → smoke **12:09:42Z**；主批次 **12:09:48Z → 12:09:50Z**；audit/export **12:10:05Z** |
| **最终状态** | **smoke `completed`；主批次 `paused`** |
| **账本内请求数** | **2**（smoke 1 + 主批次 **1**；上限 361，**未发满**） |
| 完成 episode | **0/32 主 + 0/4 重复** |
| 主批次墙钟 | **2.00 s** |

## 1. 先检查状态（prompt 第一步，只读）

`PREPARED.json`、`.run.lock`、`runs/R9_smoke/status.json`、`runs/R9_main/status.json`、`runs/` **全部不存在** → 全新目录，故按 README 执行一次 prepare / smoke / run。**未新建第二份目录**；未触碰 R1—R8 与 R7C1 任何目录。

## 2. 执行到哪一步（准确退出码）

| 步骤 | 退出码 | 结果 |
|---|---|---|
| `python3.11 -m venv .venv` + `pip install -r requirements.txt` | **0** | 53 个固定依赖装好（R7C1 的 `.venv` 已不存在，故按 README 新建） |
| `r9.py prepare` | **0** | fingerprint `c04d0614b150e0b70e03da40a9f86358796ea60de2f4ecb341e58e8c1a77ad12`，cap 361 |
| `r9.py smoke --confirm-calls 1` | **0** | **`completed`**，`json_ok: true`、`shape_ok: true` |
| `r9.py run --confirm-calls 360` | **2** | **`paused`**，1 次请求 |
| `r9.py audit` | **0** | `mechanical_pass: true`，`issues: []` |
| `r9.py export` | **0** | — |
| `r9.py verify <zip>` | **0** | `{"pass": true, "files": 140}` |
| `r9.py run`（再次，预检） | **2** | `ValueError: Existing partial run must be reviewed; no automatic resume` —— **未发任何请求** |

> 说明：首次 `prepare` 曾用已失效的 R7C1 解释器路径尝试，**退出码 127、未发任何请求**；随后按 README"全新安装"路径建 `.venv` 成功。

## 3. 暂停原因（终端原始错误 + 保留的原始响应）

**终端原始报错（一字未改）：**

```
"error": "RunStopped: Invalid JSON response preserved. Paused, not automatically repaired."
"registered_requests": 1
```

保留的原始调用（`primary_n06_verify_confirm/turn_00`，第 1 次、也是唯一一次主请求）：

| 字段 | 值 |
|---|---|
| `payload.model` | `deepseek-v4-flash` |
| `response.model` / 指纹 | `deepseek-flash` / `aeb56401ca74e127821c4f9126dcb669` |
| `finish_reason` | **`stop`**（未截断） |
| `usage` | prompt 2630 / completion 128（reasoning 36）—— **字段完整** |
| 传输状态 | `ok`（HTTP 正常） |

**`text` 字段全文（407 字符，原样）：**

```
{"tool":"get_cellular_service_status","arguments":{}}

Let me start by checking whether cellular service is on, since sending requires it.

Assistant: I notice I called a tool but let me reconsider—actually I should just check cellular service first as planned.

{"tool":"send_message_with_phone_number","arguments":{"phone_number":"+12453344098","content":"Rehearsal begins at 19:15. Please acknowledge."}}
```

**即：模型在同一回合内返回了散文说明 + 两个 JSON 对象（两个动作）**，而该回合系统提示（见 `审核/首个回合_boundary.json`）明确要求：

> "Return exactly one JSON object per turn … **Do not return Python or shell, code fences, analysis, or multiple actions.**"

严格 JSON 解析失败 → 命中协议 `stop_on` 列表中的 `INVALID_JSON` → **保留原始响应并暂停整批**。这是协议规定的停止条件，**不是**网络错误或服务故障。

## 4. 为什么 smoke 通过而主批次立刻暂停

| | smoke | 主批次首请求 |
|---|---|---|
| 请求内容 | 固定的极简 JSON 检查 | 完整的 native agent 回合（2630 prompt token，含工具文档与任务） |
| 输出 | 单个干净 JSON 对象 | 散文 + 两个 JSON 对象 |
| 结果 | `json_ok: true` | 严格解析失败 → 暂停 |

两者请求设置相同（`max_tokens=16384`、thinking enabled、`reasoning_effort=high`、不传 temperature），且返回标签与指纹一致。**我只陈述上述可核实差异，不推测模型为何改用该输出格式。**

## 5. 审核结果（`offline_reports/AUDIT.json`）

| 项 | 值 |
|---|---|
| `mechanical_pass` | **true** |
| `issues` | **[]** |
| `execution_complete` | **false** |
| `source.pass` / `files` | **true** / 120 |
| `states` | `R9_smoke: completed`，`R9_main: paused` |
| `registered_requests` | **2** |
| `reconstructed_research_requests` | **0** |
| `completed_primary` / `planned_primary` | **0 / 32** |
| `completed_repeat` / `planned_repeat` | **0 / 4** |
| `uncertain_attempts` | **[]** |
| `new_remote_calls_in_audit` | **0** |
| `limits` | 四个构造族、单一端点；非新方法或官方榜单；**未触发**的预设事件未被丢弃；缺失 episode **不按成功或失败计分** |

`calls.csv` 两行（逐调用，金额 `UNKNOWN`）：

| run | logical_id | phase | prompt | completion | reasoning | 延迟(s) | 请求/返回模型 |
|---|---|---|---|---|---|---|---|
| R9_smoke | smoke | smoke | 48 | 26 | 20 | 0.810 | deepseek-v4-flash → deepseek-flash |
| R9_main | primary_n06_verify_confirm/turn_00 | primary | 2630 | 128 | 36 | 1.993 | deepseek-v4-flash → deepseek-flash |

## 6. 首个回合的现场（`审核/首个回合_boundary.json`）

保留了暂停时刻的完整现场，可供研究端复核：

- **任务族**：`phone`（字面号码），变体含"历史证据可能已过期"的旧查询材料。
- **用户请求**：向明确号码 `+12453344098` 发送指定文本，不得替换该字面号码，可按需开启蜂窝服务。
- **暴露事件**：`{"scheduled": true, "triggered": false, "missed_before_primary_write": false, "reason": "no_qualifying_read"}` —— 因模型尚未完成限定查询，**按协议该预设更新未触发**，且**未被丢弃**（与 README 第 15 条一致）。
- **世界状态**：接触人/消息/提醒/设置四张表的模拟快照（仅模拟数据库）。

## 7. 交付 ZIP

```
/Users/user/代码/DeepSeek harness/REcheck/实验反馈/反馈14_R9实时续行诊断_首请求暂停_20260913/原始记录/R9_feedback_20260913T121005406360Z.zip
```

**verify：`{"pass": true, "files": 140}`**，141 条目。`uploads/` 内另有两份更早快照（`…T120942…` 131 条目 = smoke 时；`…T120950…` 139 条目 = run 时），**均缺少 `offline_reports/AUDIT.json` 与 `calls.csv`** —— **请回传上面这一份（141 条目）**。

密钥扫描：真实密钥 **0** 命中、任意 `sk-` 模式 **0** 命中；**不含** `config.local.json`、`.env`、`.key`、`.pem`。

## 8. 未知与声明

- **费用 UNKNOWN**：未查余额或价格。`361×16384＝5,914,624` 只是输出极端上界，**不是预计用量**；本轮实际只发 2 次请求（合计 prompt 2678 / completion 154）。
- **真实权重 UNKNOWN**：批次内返回标签 `deepseek-flash` 与单一指纹已锁定（`weight_identity_verified: false`），**不推断其等于真实权重**。
- **未推测**模型为何改用"散文 + 多动作"格式，也未推测操作者动机。
- 未把本次结果当作新方法、官方榜单分数或可发表性保证；**未宣布任何方法优越**。42/32 与 16 情形本就不是独立基准样本。

## 9. 遵守的边界

未发额外 `/models`、curl、SDK 聊天、自动故障重试、模型验证或额外解释调用；未延长输出 cap、未切换思考强度、未换 seed、未增加回合、未改用备用端点；未删锁、未删错误文件、未重采样失败样本、未从重复回合挑更好答案；未启动上游完整 CLI、用户模拟器或 RapidAPI；**工具只操作隔离模拟数据库，未接触任何私人联系人、消息、提醒或系统网络设置**；密钥仅由 `LLM_API_KEY` 环境变量提供，未写入聊天/命令参数/日志/配置，未读 `.env`。完成后停止，未启动后续实验或 RepairLens 调用。

## 文件

| 文件 | 说明 |
|---|---|
| `原始记录/R9_feedback_20260913T121005406360Z.zip` | **回传用**。141 条目：smoke 与主批次原始请求/响应、首回合现场、快照、源码与清单、审核报告 |
| `原始记录/000001_result_关键证据.json` | **暂停证据**：同一回合含散文 + 两个 JSON 对象的原始响应 |
| `原始记录/smoke_status.json` / `main_status.json` | smoke `completed`、主批次 `paused`（含原始错误串） |
| `原始记录/smoke_endpoint_identity.json` / `main_endpoint_identity.json` | 批次锁定的返回标签与指纹 |
| `原始记录/smoke_result.json` / `PREPARED.json` | 冒烟结果与冻结绑定 |
| `审核/AUDIT.json` | 独立审核报告（`mechanical_pass: true`，`execution_complete: false`，0/32） |
| `审核/calls.csv` | 逐调用 token/延迟/模型明细（2 行） |
| `审核/首个回合_boundary.json` | 暂停瞬间的完整现场（含"未触发"暴露事件标志） |
