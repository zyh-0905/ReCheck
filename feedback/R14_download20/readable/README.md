# 反馈 20：R14 公开研究数据一次性下载 —— **COMPLETE**

| 项 | 内容 |
|---|---|
| 任务性质 | **只下载公开研究数据并回传**（不运行任何 LLM 实验） |
| 工程目录 | `R14_Public_Data_Download_Kit`（工作区中即为该目录，不是 `R14_Research_Kit`） |
| 脚本 | `download_public.py`（协议 `R14_PUBLIC_JSON_TRANSFER_01`） |
| 解释器 | 系统 `python3` **3.9.6**（脚本要求 ≥3.9，仅标准库，**未安装任何依赖**） |
| 执行时间（原始 UTC） | **07:49:15Z → 07:52:31Z**（脚本自报，约 3 分 16 秒） |
| **状态** | **`COMPLETE`** |
| 命令 | `python3 download_public.py --download` |
| **退出码** | **0** |
| **已取得文件数** | **109**（96 trial + 12 aggregate + 1 数据卡） |
| 缺失 / 错误 | `missing_files: []`、`errors: []` |
| 新增 LLM 调用 | **0**（`new_llm_calls: 0`、`research_tasks_executed: 0`） |

## 1. 状态检查（prompt 第 2 步）

执行前确认：**无** `R14_public_data/` 目录、**无** `uploads/R14_public_data_*.zip` → 属"全新目录"，故执行一次下载命令。**未重复启动。**

## 2. 固定范围核对（未被改动）

| 项 | 值 |
|---|---|
| 仓库 | `SAP/agent-quality-inspect` |
| 固定提交 | **`593e686f4d0c2e9fcae5ae664c16a7687907cf97`**（脚本内 `REVISION` 常量；**未改为 main**） |
| 六个模型目录 | `gpt_4_1`、`gpt_4o`、`gpt_4o_mini`、`gpt_5`、`mistral_large_2411`、`mistral_nemo` |
| 人设 | `expert` / `nonexpert` |
| trial 范围 | `trial_0` … `trial_7`（每组合 8 个） |
| `planned_paths()` 计算 | 1（数据卡）+ 6×2×(8+1) = **109** ✔ 与声明一致 |
| 仅公开 HTTPS GET | 是；TLS 校验未关闭、未换镜像、未改脚本 |

**六个模型 × 两人设 × 8 trial = 96**，加 12 份 `aggregate_metrics_results.json` 与 1 份数据卡 = **109**。
我**逐一核对**了打包清单：**109/109 全部命中，0 缺失、0 失配**。

## 3. 完整性核验（我独立执行）

| 核验项 | 结果 |
|---|---|
| 包内 `MANIFEST.json` 登记的 109 个文件逐一 SHA-256 + 字节数比对 | **109/109 一致，0 失配** |
| 原始字节总量 | **167,452,938 字节 ≈ 159.7 MiB**（上限 512 MiB） |
| 单文件上限 | 未超（上限 32 MiB） |
| 压缩包 | 18 MiB |
| ZIP 条目总数 | 111（= `raw/` 下 109 + `MANIFEST.json` + `collector_used.py`） |
| 密钥扫描 | 真实密钥 **0** 命中、任意 `sk-` 模式 **0** 命中；无 `.env`/`.key`/`.pem` |

## 4. 内容结构（逐层核对）

```
raw/README.md                                   ← 数据卡（HuggingFace dataset card）
raw/toolsandbox/<model>/<persona>/trial_0..7_results.json    96 份
raw/toolsandbox/<model>/<persona>/aggregate_metrics_results.json  12 份
MANIFEST.json                                   ← 下载清单（含逐文件 SHA-256）
collector_used.py                               ← 实际使用的采集脚本（证据）
```

- **12 份 aggregate 的元数据全部自洽**：`agent_model` 与目录名对应（`azure/gpt-4.1`、`azure/gpt-4o`、`azure/gpt-4o-mini`、`azure/gpt-5`、`azure/mistral-large-2411`、`azure/mistral-nemo`），`user_proxy_persona` 为 `expert`/`nonexpert`，**`n_trials = 8`、`n_samples = 37`** 在全部 12 份中一致。
- **96 份 trial 的 `trial_id` 集合恰为 `{0,…,7}`**；`samples` 合计 **3551**。
- 数据卡（`raw/README.md`，4633 字节）声明 `license: apache-2.0`，标题为 TED（Talk, Evaluate, Diagnose）。

### 一条中性观察（供研究端判断，我不作解释）

96 份 trial 的 3551 个 sample 中，`status` 字段**全部为 `"success"`**（无其他取值）。
按 README 第 55 行的提醒，**不应**把 `status`/`progress_rates`/`AUC` 解释为原版 ToolSandbox 的 milestone similarity；我**不推断**该分布的原因（是否数据发布时即如此、是否另有筛选），只如实记录这一可核实事实。

## 5. 交付 ZIP

```
/Users/user/代码/DeepSeek harness/REcheck/实验反馈/反馈20_R14公开数据下载_完成_20260915/原始记录/R14_public_data_20260915T074915550182Z.zip
```

脚本自报的 `archive_verification`：`{"verified": true, "files": 109, "status": "COMPLETE"}`。
`uploads/` 内**只有这一份** ZIP。

## 6. 遵守的边界

- **未安装任何依赖**（标准库即可）、**未下载模型**、**未调用 LLM / 裁判 / 用户模拟器**、**未读取或索要任何模型 API Key**。
- **未执行 `tests`、未做额外 audit、未撰写主观成功报告**（按 prompt 第 6 条）。
- **未删除目录、未改脚本、未自动重试、未关闭 TLS 校验、未更换镜像**；每个源文件只尝试一次，无失败即无重试。
- **未重跑 R10 / R12 / R13**，旧结果未修改；**本任务不涉及 GitHub 推送**。
- 原 JSON 字节**原样保存**，未清洗、未改写 `status` 或 `metrics`、未生成或筛选实验结果、**未只留成功样例**（采集范围由 `planned_paths()` 固定，与分数无关）。
- **不得称"下载完成 = 研究实验完成"** —— 本轮 `research_tasks_executed: 0`，仅完成公开数据传输。

## 文件

| 文件 | 说明 |
|---|---|
| `原始记录/R14_public_data_20260915T074915550182Z.zip` | **回传用**。18 MiB / 111 条目：109 个原始公开文件 + 下载清单 + 采集脚本 |
| `原始记录/PACKAGE_MANIFEST.json` | 交付包自身的 9 个文件清单（用于核对脚本未被改动） |
| `原始记录/README_ZH.md` | 交付包说明（固定范围、上限、边界） |
| `审核/下载清单_MANIFEST.json` | **包内下载清单**：109 个源路径的 SHA-256、字节数、状态、缺失与错误 |
| `审核/数据卡_README.md` | HuggingFace 数据集数据卡（Apache-2.0） |
