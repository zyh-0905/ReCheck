# 反馈 18：R10 目标选择与最小写入诊断 —— **完成（四臂全部满分，四种读法零分歧）**

| 项 | 内容 |
|---|---|
| 协议 | `R10_SELECTION_AND_WRITE_SCOPE_DIAGNOSIS_01` / **`r10-1.0.0`** ✔ |
| 程序 | **`r10.py`** ✔ |
| 后端 | **Python 标准库文件 SQLite**（`sqlite 3.53.1`），**不导入 ToolSandbox** |
| 依赖 | **零第三方依赖**（`requirements.txt` 仅注释），未建虚拟环境、未 pip 安装 |
| 解释器 | `/Users/user/.local/bin/python3.11`（Python 3.11.15）；旧目录绝对路径复用，**未改动旧工程** |
| 执行时间（原始 UTC） | prepare **13:46:48Z**；run **13:47:52Z → 13:54:52Z**；audit/export **13:55:01Z** |
| **`status`** | **`completed`** |
| 完成回合 | **48/48 主回合**（12 情形 × 4 臂；无重复回合） |
| **账本内请求数** | **237 / 384**（未发满，提前完成即停） |
| 数据库工具事件 | **214 / 214 完成**，部分事件 **0** |
| 保留的响应失败 | **[]** |
| 金额 | **UNKNOWN** |

## 1. 命令与退出码

| 命令 | 退出码 |
|---|---|
| `r10.py status`（只读） | 0（`{"status": "not_started", "has_lock": false}`） |
| `r10.py prepare` | **0**（`new_model_calls: 0`，`new_smoke_required: false`） |
| `r10.py run --confirm-calls 384` | **0** |
| `r10.py audit` | **0** |
| `r10.py export` | **0** |

无 smoke、无 qualify、无 curl / `/models` / SDK 探针 / 用户模拟器 / 裁判。**未运行 96 条离线实验，未跑全套单元测试，未安装任何依赖。**

## 2. 主结果：四臂**完全相同**，全部满分

| 臂 | n | `tool_success_proxy` | `goal_final` | `final_state_clean` | **`trace_safe_success`** | `false_completion_claim` |
|---|---|---|---|---|---|---|
| generic | 12 | 12 | 12 | 12 | **12** | 0 |
| minimal | 12 | 12 | 12 | 12 | **12** | 0 |
| intent | 12 | 12 | 12 | 12 | **12** | 0 |
| both | 12 | 12 | 12 | 12 | **12** | 0 |
| **全体** | **48** | **48** | **48** | **48** | **48** | **0** |

安全计数全部为零：`wrong_target_field_changes = 0`、`protected_field_changes = 0`、`goal_only_false_accept = 0`、`final_clean_false_accept = 0`。

**四种读法在 48/48 个回合上判断一致，分歧回合数 = 0。**

> **本轮未复现上一轮（R9NT1）的读法分歧。** R9NT1 中 4/32 个回合出现"工具成功但轨迹不安全"的分歧，本轮在同模型、同原生工具接口下为 **0/48**。这是**阴性/天花板结果**，按协议保留；我**不做**单变量归因（任务族、后端、提示载体均已改变），也**不据此宣称泛化或方法优越**。

## 3. 合法业务冲突：22 个回合各遇到 1 次，全部被解决

| 项 | 值 |
|---|---|
| 遇到冲突的回合 | **22/48**（每回合恰好 1 次；其余 26 个回合 0 次） |
| 按臂分布 | generic 5、minimal 6、intent 5、both 6 |
| 工具回执中出现的冲突码 | `ROW_VERSION_CONFLICT` 93 次、`SELECTION_CONFLICT` 59 次、`NOT_FOUND` 0 次 |
| 结果 | 22 个冲突回合**全部**最终 `trace_safe_success = true` |

即：**冲突由程序真实回传，模型在原 8 轮预算内查询、处理并完成**（协议允许的任务决策，不是后台网络重试）。

## 4. 工具使用与调用规模

| 工具 | 调用次数 |
|---|---|
| `finish_task` | 48（每回合恰好 1 次） |
| `resolve_service` | 40 |
| `get_batch` | 37 |
| `update_config` | 36 |
| `select_batch` | 34 |
| `update_batch` | 34 |
| `get_config` | 33 |

| 指标 | 值 |
|---|---|
| 主回合 `model_calls` | 合计 **237**，分布 {4 次×26, 6 次×21, 7 次×1}（每回合上限 8） |
| 主回合 `database_tool_calls` | 合计 **214**，分布 {3×16, 4×10, 5×10, 6×8, 7×4}，最大 **7**（每回合上限 32） |
| `completion_claim` | **`completed` 48/48**，`false_completion_claim = 0` |
| `finish_reason` | **`tool_calls` 237/237**（每回合以 `finish_task` 结束，无散文终止） |

## 5. 事件暴露

| (scheduled, triggered) | 回合数 |
|---|---|
| (True, True) | **40** |
| (False, False) | 8 |

`opportunity_closed = 48/48` —— 每个回合的更新机会窗口均按协议关闭，已安排事件在 40 个回合中**全部触发**。

## 6. 审核结果（`audit`）

| 项 | 值 |
|---|---|
| `mechanical_pass` | **true** |
| `execution_complete` | **true** |
| `status` | `completed` |
| `primary_episodes` | **48** |
| `recorded_requests` / `reconstructed_requests` | **237 / 237** |
| `database_tool_events` / `partial_database_events` | **214 / 0** |
| `retained_response_failures` | **[]** |
| `new_remote_model_calls` | **0** |
| `cost_currency` | **UNKNOWN** |
| `scientific_superiority_claim` | **false** |
| `automatic_next_batch_authorized` | **false** |

**usage 合计**（237 次响应）：prompt **463,672** / completion **49,679**（其中 reasoning **15,101**）；模型延迟合计 **343.2 s**。返回模型 `deepseek-flash` 237/237，指纹 `aeb56401ca74e127821c4f9126dcb669` 单一。

## 7. 交付 ZIP

```
/Users/user/代码/DeepSeek harness/REcheck/实验反馈/反馈18_R10选择与写入范围诊断_满分_20260914/原始记录/R10_feedback_20260914T135501.482319Z.zip
```

**已独立核验**：**1092 条目**，`BUNDLE_MANIFEST.json` 逐文件 SHA-256 **失配 0**。密钥扫描：真实密钥 **0** 命中、任意 `sk-` 模式 **0** 命中；**不含** `config.local.json`、`.env`、`.key`、`.pem`。本轮 `uploads/` 只有**一份** ZIP。

## 8. 预算沿革（如实）

- 本轮 **237 / 384** 次（未发满，提前完成即停；**未追加、未补足**）。
- **无** smoke、**无** qualify、**无** `/models`、**无** curl/SDK 探针、**无**第二模型或并发实例；未换模型/参数/种子/提示/字段/判分/预算、未截取 JSON、未修改提示、未根据输出选择回合、未重采样、未删锁、未另开副本。
- 此包**不自动授权**下一模型、下一批次或论文投稿。

## 9. 声明与边界

- **未宣称任何优越性**：`scientific_superiority_claim: false`、`automatic_next_batch_authorized: false`。四臂**完全相同**，本轮**没有**区分出 generic / minimal / intent / both 的差异。
- **12 个配对构造情形不是 48 个独立真实样本**；两个任务族为研究者构造数据，**非公开 benchmark / 生产事故**，也**不是**已有方法被证明有效。**少量模板上的成功不证明泛化**；未复现误写时**不调提示诱导、不扩大同模板直到显著**。
- **本轮未复现 R9NT1 的读法分歧**（0/48 vs 4/32），但接口与任务族同时改变，**不做单变量归因**，也不以本轮结果覆盖旧记录。
- **返回标签与指纹一致仅表示元数据批次一致，不是权重认证**；不声称 `deepseek-flash` 与 `deepseek-v4-flash` 同权重。
- `finish_task` **只是报告**，不读取私有评分、不给安全认证；普通文字结束会另标 `unstructured`，**不从正文提取动作**。
- **所有工具只访问本次临时 SQLite 文件，不连接任何用户业务数据库或真实账户**；旧实验原样保留。**机械 audit 通过只表示记录可重建，不代表论文结论成立**。
- 本轮**没有 RepairLens 新增证据**。

## 文件

| 文件 | 说明 |
|---|---|
| `原始记录/R10_feedback_20260914T135501.482319Z.zip` | **回传用**。1092 条目：237 次请求的原始响应字节/请求/工具回执/前后状态/事件、48 个回合逐条评分、快照、源码与协议、审核 |
| `原始记录/PREPARED.json` | 冻结绑定（源码/配置/协议哈希、环境含 `sqlite: 3.53.1`、零模型调用） |
| `原始记录/config.json` / `protocol.json` | 请求配置与协议 |
| `审核/audit完整输出.txt` | 完整审核输出（48/48、237/237、214 数据库工具事件） |
| `审核/main_status_逐回合评分.json` | **48 个回合的逐条评分、违规计数与暴露标记** |
| `审核/ANALYSIS_LOCK_ZH.md` | 研究端预先分析规则（原包文档，供对照） |
| `审核/批次摘要.json` | 起止 UTC、墙钟、请求数、授权标志 |
