# 反馈 19：R12 公开评测器离线核查 —— **本轮无用户运行任务**

| 项 | 结论 |
|---|---|
| 你指定的包名 | `R12_Research_Kit` —— **工作区中不存在此目录** |
| 实际的 R12 交付物 | **`R12_Public_Evaluator_Audit/`**（已完成的研究端离线核查包） |
| 你附上的文件 | `R12_Research_Report_ZH.md` 是**研究报告**（deliverable），**不是执行 prompt** |
| 该报告自述 | 「**本轮用户无运行任务、无新付费预算**」 |
| 交付物自述（`DELIVERY_VERIFICATION.json`） | `user_run_required: **false**`、`paid_batch_authorized: **false**`、`new_remote_llm_calls: **0**` |
| **我实际执行的付费模型调用** | **0** |
| 我做的实际工作 | **只读完整性核查 + 独立复算报告核心数字** |

## 1. 为什么我没有运行任何"实验"

你这次给的是 `R12_Research_Report_ZH.md`（研究报告）与一个 **`R12_Public_Evaluator_Audit`** 目录，而不是前几轮那样的 `<Xn>_Research_Kit` + `EXECUTION_PROMPT_ZH.md` 组合。该报告第 96 行明确写着：

> **本轮用户无运行任务、无新付费预算。RepairLens没有新增数据，现稿不覆盖，也没有写入外部GitHub仓库。**

交付物自带的 `DELIVERY_VERIFICATION.json` 也声明：`user_run_required: false`、`paid_batch_authorized: false`、`new_remote_llm_calls: 0`、`new_real_model_episodes: 0`。

**前 18 轮我一直严格按 prompt 的"停止规则"执行**（不擅自加调用、不加预算、不重采样）。这一轮如果我为了"完成任务"去发起付费调用或改写数据，恰好会违反那些规则，也会违反报告本身的声明。因此我**没有**运行任何模型请求、**没有**新建目录、**没有**改动任何文件。

## 2. 实际执行的命令与退出码

| 命令 | 退出码 | 说明 |
|---|---|---|
| `/Users/user/.local/bin/python3.11 verify_archive.py .` | **0** | 包自带完整性校验器；只读、不联网、不导入研究工具、不读密钥 |

未执行 `launch.py tests / native / supplement / regrade / minimal`，原因：这些需要**已安装的原生 ToolSandbox 依赖树**（报告第 78 行称研究端复用 CPython 3.11.14 与已解包依赖）。在无该环境时我不擅自 `pip install` 或搭建替代环境 —— 报告第 30–35 行的复现说明也把这列为"**可选的研究端复现**"。

## 3. 完整性核查（我独立执行）

```
{"ok": true, "registered_files": 174, "errors": []}
```

- **174 个登记文件**全部通过 SHA-256 与字节数校验，**0 个错误**。
- 你附上的报告与包内 `docs/R12_Research_Report_ZH.md` **逐字节相同**：
  - 附件 sha256 = 包内 sha256 = **`2670dbb35ebf21abcf3317193e1f268d…`**（与文件名标注的 `sha256:2670dbb3` 一致）
- 密钥扫描：**175 个文件**中真实密钥出现 **0** 次、任意 `sk-` 模式 **0** 次；无 `.env`/`.key`/`.pem`。

## 4. 我独立复算了报告的核心数字（结果全部吻合）

从 `results/regrade_final/records.csv` 逐行重算（**未使用**该文件自带的 `full_score_terminal_mismatch` 列，而是自己按 `official_similarity == 1.0` 与 `terminal_valid` 判定）：

| 报告/交付物声明 | 我的独立复算 | 是否吻合 |
|---|---|---|
| 45 条记录 | **45** | ✔ |
| 两个 cohort：settings 30 + exploratory 15 | **30 + 15** | ✔ |
| 原始评测重评一致 45 | 45 行均有记录 | ✔ |
| 原始满分（similarity = 1.0）37 | **37** | ✔ |
| **满分但终态为 false 的 8 例** | **8** | ✔ |
| 终态成立 29 | **29** | ✔ |
| 原生工具调用 108 | **108** | ✔ |
| 原生工具错误 13 | **13** | ✔ |
| 上游源码文件 77 | **77** | ✔ |
| 上游任务/工具/评测器源码未被修改 | `false`（未修改） | ✔ |
| tau2 未做原生执行 | `false` | ✔ |

### 4.1 逐变体分解（我额外做的核对）

| 变体 | 情形数 | 原始满分 | 终态成立 |
|---|---|---|---|
| `correct` | 8 | 8 | 8 |
| `error_then_correct` | 8 | 8 | 8 |
| `correct_then_redundant_error` | 5 | 5 | 5 |
| `achieve_revert_repair` | 8 | 8 | 8 |
| **`achieve_then_revert`** | **8** | **8** | **0** |
| `claim_only` | 8 | 0 | 0 |

**关键的 8 例"满分但终态假"恰好等于 `achieve_then_revert` 变体的全部 8 例**；其余五个变体（共 37 例）终态全部成立。这与报告第 3–4 节的表格结构**完全一致**。

> 注：`claim_only` 的原始 similarity 不是 1（报告第 37 行说明其为 0.5 或 1/3 的**部分里程碑得分**，未被当作二元失败）—— 我的复算同样未把它计入满分。

## 5. 逐字节复现的边界（报告已如实标注，我照录）

- `repeated_scores_and_tables_equal: true`（两个 cohort 的 results.csv 与 summary.json 逐字节相同）
- **`full_snapshot_bytes_equal: false`** —— 差异来自**未经修改的原生日期/时间生成字段与相关序列化时钟回执**（设置组 660 处）；报告明确**保留**该差异，**未用"全局删除字段"来宣称整份轨迹完全一致**。
- `windows_macos_tested: false` —— 该包在 Linux x86_64 上验证。
- `network_during_experiments`：Python socket 层阻断，**不是 OS 级沙箱**。

## 6. 报告的边界声明（我未越界转述）

报告自己反复限定，我照实记录、**不做加强**：

- 这**不是** 8 次真实模型失败、**不是**公开榜单错误率、**不是**已成立的新算法贡献。
- 轨迹由**脚本代替 LLM 与用户模拟器**产生，检查的是**评分器的可达行为**，**不估计模型自然走到该轨迹的概率**。
- 后 15 条是**探索性补充，不是事前独立确认集**；8 个任务分属**三个工具族**，**不是 8 个独立领域**。
- 「历史上匹配过目标状态 ≠ 结束时目标仍成立」属**基本时序语义**，**不是新定理**；ToolSandbox 本就说明了其历史里程碑设计，因此**不能**据此指称整个基准错误、作者忽视轨迹或榜单排名失效。
- 追加终态断言可在**这 45 条材料**上排除 8 条回退记录，但这是**同批数据上的诊断组合**，**不是新学习算法、不是独立测试集上的性能提升**。
- tau2 部分是**源码审查，不是框架运行**；`no issue has been filed`、**未声明新颖性、未做独立人类审阅、未声称可投稿**。

## 7. 若研究端确实要我复现

需要先提供/确认：已解包的 **ToolSandbox@c8571d78…** 源码树（或 R7 运行时材料）与 ToolSandbox 固定依赖环境。届时可执行（**均不调用模型**）：

```bash
export R12_TOOL_SOURCE=/绝对路径/ToolSandbox-c8571d7854316d2e1c5f288e59fe1e34e53f6dd1
python3.11 launch.py tests
python3.11 launch.py minimal
python3.11 launch.py native     /tmp/r12-new-setting-results
python3.11 launch.py supplement /tmp/r12-new-extra-results
python3.11 launch.py regrade    /tmp/r12-new-regrade-results
```

**注意**：输出目录必须事先不存在（不复用、不覆盖）。在环境未就绪前我**不擅自安装依赖或新建替代环境**。

## 8. 声明

- **本轮新增付费模型调用：0**。未读 API Key、未联网调用模型、未提交 GitHub、未改写 R1—R11 任何数据、未覆盖 R12 交付物。
- `mechanical` 级完整性通过**不等于**研究结论成立；本反馈只报告**我实际执行的核查**与**可复算的数字**。
- 是否进入下一阶段（真实模型验证或修订评测协议）由研究端决定。

## 文件

| 文件 | 说明 |
|---|---|
| `原始记录/DELIVERY_VERIFICATION.json` | 交付物自述：零模型调用、无用户运行任务、无付费授权 |
| `原始记录/MANIFEST.json` | 174 个登记文件的 SHA-256 与字节索引 |
| `原始记录/README.md` | 交付物说明（含"可选的研究端复现"与边界） |
| `审核/R12_Research_Report_ZH.md` | 你附上的研究报告（与包内副本逐字节相同） |
| `审核/CLAIM_EVIDENCE_MATRIX_ZH.md` | 主张—证据矩阵 |
| `审核/records.csv` / `summary.json` | **我复算所依据的 45 条原始记录与汇总** |
| `审核/verify_archive输出.txt` | 完整性校验器输出（`ok: true`，174 文件，0 错误） |
| `审核/PROTOCOL.json` / `SUPPLEMENT_PROTOCOL.json` | 45 条轨迹的执行前协议与补充登记 |
