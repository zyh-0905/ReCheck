# 反馈 16：R9TQ1 原生工具调用接口资格测试 —— **qualification_pass = true**

| 项 | 内容 |
|---|---|
| 协议 | `R9TQ1_NATIVE_TOOL_QUALIFICATION_01` / **`r9tq-1.0.0`** ✔ |
| 程序 | **`r9tq.py`**（不是 `r9.py`）✔ |
| 源码绑定 | `SOURCE_MANIFEST.json` **110/110 文件哈希一致** |
| 执行时间（原始 UTC） | prepare **15:42:27Z**；qualify **15:42:30Z → 15:42:44Z**；audit/export **15:42:48Z** |
| **`status`** | **`completed`** |
| **`qualification_pass`** | **`true`** |
| 账本内请求数 | **10 / 12**（未用满；每案提前完成即停） |
| 完成案例 | **q0_read、q1_message、q2_reminder（3/3）** |
| 原生工具事件 | **7** |
| 保留的响应失败 | **[]** |
| `research_complete` | **false**（本测试不是主研究） |
| `automatic_full_research_authorized` | **false** |
| 金额 | **UNKNOWN** |

## 1. 命令与退出码

| 命令 | 退出码 |
|---|---|
| `r9tq.py status`（只读检查，未运行资格测试） | — |
| `r9tq.py prepare` | **0**（`new_model_calls: 0`） |
| `r9tq.py qualify --confirm-calls 12` | **0** |
| `r9tq.py audit` | **0** |
| `r9tq.py export` | **0** |

解释器复用已装好 R9J1 依赖的绝对路径（`R9J1_Research_Kit/.venv/bin/python`，Python 3.11.15 / numpy 1.26.4 / polars 0.20.31），**工作脚本来自新 R9TQ1 目录**，旧工程未改动。**未复制旧 runs/PREPARED/身份文件。**

## 2. 本轮接口变更（这是通过的关键）

| | 旧 R9 / R9J1 | **本 R9TQ1** |
|---|---|---|
| 动作载体 | `content` 里的 JSON 文本 | **API 原生 `tools` / `tool_calls` + `role=tool` 真实回执** |
| `response_format` | R9J1 曾启用 `json_object` | **不使用** |
| 动作提取 | 严格解析单 JSON 对象 | **不从散文/推理/代码围栏提取或执行任何动作** |
| 请求模型标签 | `deepseek-v4-flash` | **`deepseek-flash`**（本次明确指定的新标签） |
| `tool_choice` | — | `auto`（未用 forced/required、strict/beta、parallel 参数） |

请求侧固定：`max_tokens=16384`、`thinking enabled`、`reasoning_effort high`、`stream=false`。

## 3. 逐案例结果（`qualify` 输出原文）

| 案例 | qualified | roundtrip_ready | task_state_ok | terminated | 工具调用 | 原生工具错误 |
|---|---|---|---|---|---|---|
| **q0_read** | ✔ true | ✔ true | ✔ true | ✔ true | **1** | 0 |
| **q1_message** | ✔ true | ✔ true | ✔ true | ✔ true | **3** | 0 |
| **q2_reminder** | ✔ true | ✔ true | ✔ true | ✔ true | **3** | 0 |

q0 评分：`read_only_state_preserved: true`、`observed_value_reported: true`
q1 / q2 评分：`tool_success_proxy / goal_final / final_state_clean / trace_safe_success` 均 **true**；`wrong_write: false`、`violations: []`、`tool_errors: 0`、`goal_only_false_accept: false`、`final_clean_false_accept: false`

三个案例的 `not_a_research_success_rate: true`（脚本自标：这不是科研成功率）。

## 4. 十次响应结构（逐条核实，非从 content 提取）

| # | logical_id | finish_reason | 原生调用 | `content` 内容 |
|---|---|---|---|---|
| 1 | q0_read/turn_00 | **tool_calls** | `get_cellular_service_status` | 空 |
| 2 | q0_read/turn_01 | stop | 无 | `CELLULAR_ON` |
| 3 | q1_message/turn_00 | **tool_calls** | `get_cellular_service_status` | 空 |
| 4 | q1_message/turn_01 | **tool_calls** | `send_message_with_phone_number` | "Cellular service is already on. Sending the message now." |
| 5 | q1_message/turn_02 | **tool_calls** | `search_messages` | "Message sent. Confirming the record." |
| 6 | q1_message/turn_03 | stop | 无 | "Done. One text was sent to the literal number +12453344098 with exact…" |
| 7 | q2_reminder/turn_00 | **tool_calls** | `search_reminder` | 空 |
| 8 | q2_reminder/turn_01 | **tool_calls** | `modify_reminder` | 空 |
| 9 | q2_reminder/turn_02 | **tool_calls** | `search_reminder` | 空 |
| 10 | q2_reminder/turn_03 | stop | 无 | "Done. The reminder \"Review the indigo rehearsal plan\" (id `54f20be9-e…" |

**关键对照**：前两轮（R9、R9J1）在同一 episode 出现的是"一次 completion 内多个 JSON 文本动作 + 虚构工具结果"；本轮的**每次动作都是真正的 `tool_calls`（`finish_reason: tool_calls`），散文只出现在 `content` 中，工具回执由 `role=tool` 真实返回**。全部 10 次响应 HTTP=200，`model=deepseek-flash`。

**我不宣称"零错误"**：脚本报告 `native_tool_errors: 0`、`violations: []`，但任务/参数层面的正确性由研究端人工式逐条审阅（README 第 89–91 条明确：接收正确结构不保证参数与任务都正确；纯散文即使声称成功也不会执行）。

## 5. 审核结果（`audit`）

| 项 | 值 |
|---|---|
| `mechanical_pass` | **true** |
| `execution_complete` | **true** |
| `qualification_pass` | **true** |
| `recorded_requests` / `reconstructed_requests` | **10 / 10** |
| `completed_qualification_cases` | q0_read、q1_message、q2_reminder |
| `native_tool_events` | **7** |
| `retained_response_failures` | **[]** |
| `status` | `completed` |
| `research_complete` | **false** |
| `automatic_full_research_authorized` | **false** |
| `new_remote_model_calls` | **0**（审核不产生新调用） |
| `monetary_cost` | **UNKNOWN** |
| `note` | `Engineering qualification, not model reliability or experiment success rate; same-assistant replay` |

**usage 合计**：prompt **24,165** / completion **858** / total 25,023；模型延迟合计 **9.94 s**（单次 0.66–1.26 s）。缓存命中输入共 16,896 token。逐次明细见 `审核/audit完整输出.txt`。

## 6. 交付 ZIP

```
/Users/user/代码/DeepSeek harness/REcheck/实验反馈/反馈16_R9TQ1原生工具资格测试_通过_20260913/原始记录/R9TQ1_feedback_20260913T154248.814167Z.zip
```

**已独立核验**：**173 条目**，`BUNDLE_MANIFEST.json` 逐文件 SHA-256 **失配 0**。

| 顶层 | 条目数 |
|---|---|
| `vendor/` | 77 |
| `runs/`（10 次请求的 `_request.json` / `_response.json` / `_response.raw` / `_send_intent.json`，含 `AUDIT.json`） | 60 |
| `tests/`、`tq/` | 各 7 |
| `docs/` 4、`legacy/` 4、`fixtures/` 2 | — |
| 根文件（`PREPARED.json`、`config.json`、`protocol.json`、源码清单、README、LICENSE 等） | 8 |

> 本轮 `uploads/` 只有**一份** ZIP（前几轮的多份快照因运行方式不同未出现），请直接回传这一份。

密钥扫描：真实密钥 **0** 命中、任意 `sk-` 模式 **0** 命中；**不含** `config.local.json`、`.env`、`.key`、`.pem`。脚本声明的定点脱敏分支**未被触发**（无回显密钥）。

## 7. 预算沿革（如实）

- 本轮 **10** 次（上限 12，未用满；`additional_smoke: 0`）。
- 此前 R9 与 R9J1 各记录 **2** 份生成响应 → **沿革累计 14** 次，未超协议所述本轮上限 16。
- **未**另做 smoke、**未**发 `GET /models`、**未**做 curl/SDK 探针、**未**换模型或参数、**未**重采样、**未**执行旧目录、**未**新建副本试跑。

## 8. 明确区分与声明

- **`completed` 与 `qualification_pass` 是两个字段**：本轮两者**均为真**，但这只是**接口资格**（结构、真实回执链接、显式结束、模拟状态合格）通过。
- **这不等于**：模型可靠、零错误、任务全对、权重一致、R9 主实验可发表。`automatic_full_research_authorized: false` —— **通过本测试不自动放行完整研究批次**。
- **请求/响应标签与指纹一致**仅表示元数据批次一致，**不是权重认证**；本次标签由 `deepseek-v4-flash` 明确改为 `deepseek-flash`，**不声称两者同权重或互为别名**。
- 三个案例**不是** 3 个独立科研样本，**不计算 ReCheck 成功率**；参数与消息角色均已变化，**不能与旧设置做单变量效果比较**。
- 思考文本仅作接口上下文与审计保存，**不用于解释模型内部因果**。
- 金额 **UNKNOWN**；`12×16384=196,608` 只是输出极端上界，**不是预计花费**。
- RepairLens **无新增调用**，旧 R9 分数**未回填**。**未宣称零错误、可发表或权重一致**；**未**自动启动正式 R9 任务、**未**提交论文、**未**再发任何模型请求。

## 9. 安全边界

所有真实写操作**只发生在 ToolSandbox 的模拟数据库**；**未**连接任何真实个人账户、联系人、短信、邮箱、系统设置或连接器。密钥仅经 `LLM_API_KEY` 环境变量提供，未写入聊天/命令参数/日志/配置，未读 `.env`，未搜索旧目录凭据。未删锁、未在写入中打包。

## 文件

| 文件 | 说明 |
|---|---|
| `原始记录/R9TQ1_feedback_20260913T154248.814167Z.zip` | **回传用**。173 条目：10 次请求的原始请求/响应/raw 字节、发送意图、快照、源码与清单、审核 |
| `原始记录/PREPARED.json` | 冻结绑定（源码/配置/协议哈希、环境、`new_model_calls: 0`） |
| `原始记录/config.json` / `protocol.json` | 本轮请求配置与资格协议 |
| `审核/RUNS_AUDIT.json` | 运行目录内的审核报告 |
| `审核/audit完整输出.txt` | **完整审核输出**：逐案结果、10 条 usage 明细、模型延迟 |
