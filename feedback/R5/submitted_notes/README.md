# 反馈 09：R5 任务损失核与共享预算的离线跨机复现

| 项 | 内容 |
|---|---|
| 协议 | `R5_TASK_LOSS_OFFLINE_01`（r5-5.0.0） |
| 执行时间 | 2026-09-13 UTC 00:56–00:59（本机 CST 08:56–08:59） |
| **LLM / API 请求** | **0**（协议规定严格为 0；`remote_llm_calls: 0`、`new_llm_calls: 0`） |
| 是否读取 API Key | **否**（无密钥、无 .env、无模型配置、无 smoke、无登录/充值） |
| 实验进程网络 | 由 `storage.no_network()` 在进程内禁用 |
| 本机环境 | macOS 26.5.2 arm64、Python 3.11.15、numpy 2.3.5 |
| 规模 | 1024 条轨迹、8192 条任务记录、64 流 × 2 菜单 × 8 策略 |
| 单元测试 | **45 tests, OK（退出码 0）** |
| **`execute` 退出码** | **2**（机械 PASS 为 false，原因见下） |
| **输出包** | `R5_feedback_20260912T165933788165Z.zip`，`verify: pass=True, files=1115` |

## 1. 实际执行的命令与退出码

| 命令 | 退出码 |
|---|---|
| `.venv/bin/python -m unittest discover -s tests -v` | **0**（45 tests OK） |
| `.venv/bin/python r5.py execute` | **2** |
| `.venv/bin/python r5.py export` | **0**（`pass: True, files: 1115`） |
| `.venv/bin/python r5.py verify <zip>` | **0**（`pass: True, files: 1115`） |

依赖安装访问了包索引（唯一一次网络使用）；实验命令本身禁用网络。只执行了一次完整批次，未重跑、未改源码/参数/种子/清单/参考结果、未删锁。

## 2. 机械审查结果（逐项，以 `audit/report.json` 为准）

| 项 | 值 |
|---|---|
| `mechanical_pass` | **false** |
| `complete` | **true** |
| `rows` | **8192** |
| `trajectories` / `expected_trajectories` | **1024 / 1024** |
| `replayed_task_records` | **8192** |
| `source.pass`（源码绑定） | **true** |
| `new_llm_calls` | **0** |
| `rule_execution_only` | true |
| `calibration_only_learning` | true |
| `validation_not_used_by_test_schedulers` | true |
| `no_money_or_model_performance_claim` | true |
| **`reference_science_match`** | **false** |
| `scientific_gate` | `PENDING_RESEARCHER_REVIEW` |
| `issues` | **仅 1 条**：`reference scientific outputs differ: preserve records for review` |

**唯一的问题是参考科学轨迹哈希不一致。`issues` 中没有 `:replay difference`，即本机 8192 条记录全部重放一致。**

## 3. 参考比对：哪些一致、哪些不一致（可核实数据）

| 对照对象 | 结果 |
|---|---|
| `summary.csv`（64 行 × 13 列） | **数值差异 0 个单元格** —— 完全一致 |
| `paired.csv`（72 行） | **数值差异 0 个单元格** —— 完全一致 |
| `calibration_diagnostic.json`（5 项） | **逐键一致**（MAE 0.0173828125、max 0.203125 等） |
| 校准 `fitted.json` | 本机自动重算==已存文件（`calibration was changed` 未触发）；指纹 `5f4376ef…`；表为 (5,8,8)，取值全为 1/64 的干净二进制小数 |
| `model_validation.json` | **16 个叶子不同，全部在 1e-16 量级**（浮点表示差异） |
| `scientific_hashes.json` | **1024 条中 119 条相同、905 条不同** |

### 3.1 我做的排除性检查（全部为可复核事实，非推测）

1. **不是计时副作用**：`runtime.science()` 明确剔除所有 `*_seconds`、`cache_info`、`wall_started/wall_finished`。
2. **不是统一浮点精度差**：把浮点四舍五入到 6 位/4 位小数后重算哈希，匹配数从 119 降到 1/0（即差异不是"末位精度"性质）；完全剔除 `predicted_task_error_after_receipts` 后匹配数为 0。
3. **本机自洽**：抽样 20 条重算 `science()` 哈希与已存审计哈希 **20/20 一致**；审计重放 8192/8192 一致。
4. **数据生成一致**：64 个 `case_sha256` 与本机由协议种子重新生成的 case 全部绑定正确（不匹配 0）。
5. **差异呈"逐流非随机"分布**：并非均匀散布 —— 34 条流 16/16 全不同，另一些流有 2–12 条相同（如流 2 为 12/16、流 12 为 11/16、流 22 为 9/16）。无任何一条流 16/16 全同。
6. **按字段组无法定位单一元凶**：plans / answers / packets / memory / budget / trace / receipts / predicted / initial 各组在"相同集合"与"不同集合"内部都有多种取值，不存在某一组单独解释全部差异。
7. **已确认存在的机器相关浮点差异**：`model_validation.json` 中 `expected_task_cost` 有 16 个叶子在 1e-16 量级不同（例：`1.9597743092060993` vs `1.9597743092060989`）。
8. **哈希投影是否包含该字段，未能确认**：参考包只提供哈希、未提供参考轨迹原文，因此无法对内容做逐字段 diff。

**我不对根因下结论**，也不重采样去"修"到与参考一致 —— 按 prompt 与 README，科学差异交研究审核判别。

## 4. 本机规划成本记录（本轮第二个目的）

冷启动规划时间与 Python 轨迹内存（计时与内存分两次独立执行，各 2 次重复；`scope` 字段声明这不是进程 RSS）：

| 方法 | H | 冷启动秒(rep0) | 冷启动秒(rep1) | 峰值轨迹字节 | value 状态数 |
|---|---|---|---|---|---|
| task_exact | 2 | 0.001180 | 0.001190 | 123,281 | 7 |
| task_exact | 4 | 0.010983 | 0.010937 | 1,441,997 | 221 |
| task_exact | 6 | 0.044982 | 0.044605 | 6,893,753 | 1,294 |
| task_exact | 8 | 0.126977 | 0.120212 | 20,227,689 | 4,097 |
| task_rollout2 | 2 | 0.001318 | 0.001271 | 129,297 | 0 |
| task_rollout2 | 4 | 0.005666 | 0.005669 | 555,393 | 189 |
| task_rollout2 | 6 | 0.007924 | 0.008257 | 802,153 | 318 |
| task_rollout2 | 8 | 0.010587 | 0.010631 | 1,091,681 | 468 |
| task_myopic | 2 | 0.000213 | 0.000210 | 33,489 | 0 |
| task_myopic | 4 | 0.000212 | 0.000207 | 33,437 | 0 |
| task_myopic | 6 | 0.000291 | 0.000225 | 33,489 | 0 |
| task_myopic | 8 | 0.000213 | 0.000224 | 33,489 | 0 |

分段计时（`calibration/timing.json`，`amortization` 声明这是一张共享拟合表，**不是免费的生产维护**）：

| 阶段 | 秒 | 工具执行次数 |
|---|---|---|
| 校准拟合 | 0.266830 | 20,480 |
| 独立验证 | 0.131213 | 10,240 |

全批执行墙钟 **6.675 s**（`execution_summary.json`）。

**本机计时与研究端不同属待审信息**：我只运行一次，未反复运行挑选最好耗时。

## 5. 输出包路径

```
/Users/user/代码/DeepSeek harness/REcheck/实验反馈/反馈09_R5_任务损失核离线复现_20260913/原始记录/R5_feedback_20260912T165933788165Z.zip
```

**verify 结果：`{'pass': True, 'files': 1115, 'sha256': '665d459d93db648c0ed904d8046ea755708884a912d04ef8387bf8116abe31ea'}`**

（`uploads/` 内另有一份 `...T165808...zip`，是 `execute` 步骤内已生成的包，内容同类；**请用上面这一份**。）

## 6. 未解决的错误

**1 项，且只有 1 项**：`reference_science_match = false`（1024 条科学轨迹哈希中 905 条与参考不同）。其余机械检查全部通过（见第 2 节）。根因未确定，已在第 3 节列出 8 项排除性事实供研究端判别。

## 7. 边界声明（不越界）

- 机械 PASS **不等于**方法有效；`reference_science_match` 只是与同一冻结批次的科学输出一致性。
- 同一冻结随机带的重复运行**不是新增独立样本**，不可加入论文 n。
- 主指标 = 实际任务失败 + 0.05 × 运行期额度，**不是货币、不是墙钟时间**。每条策略轨迹运行期 8 额度、每轮 4；共同启动校准等价 6 额度单列。
- 本轮**没有**模型表现或货币节约主张；R5 未给模型做字段复制付费；RepairLens 本轮无新主算法证据。
- 我**未**自行编造因果解释、模型版本、账单或操作者原因；**未**声称已满足投稿要求。
- 完成后停止：未启动任何 LLM 实验、未改变样本量、未推进下一轮。

## 文件

| 文件 | 说明 |
|---|---|
| `原始记录/R5_feedback_20260912T165933788165Z.zip` | **回传用**。1115 文件：1024 条完整轨迹、校准/验证材料、私有合成评测数据、统计、计时、代码快照与清单 |
| `原始记录/manifest.json` / `status.json` / `execution_summary.json` | 冻结绑定、状态、执行摘要 |
| `原始记录/scaling.json` / `compilation.json` | H=2/4/6/8 冷启动计时与内存；各方法编译状态数 |
| `原始记录/model_validation.json` | 离线模型验证（含 1e-16 浮点差异，见 §3） |
| `原始记录/fitted.json` / `diagnostic.json` / `timing.json` / `split_ids.json` | 校准拟合表、诊断、分段计时、训练/验证划分 |
| `审核/report.json` | **机械审查报告（本批次核心结论）** |
| `审核/summary.csv` / `paired.csv` / `per_task.csv` | 统计输出（summary 与 paired 与参考零差异） |
| `审核/scientific_hashes.json` | 本机 1024 条轨迹哈希（与参考比对用） |
| `审核/单元测试完整输出.txt` / `execute完整输出.txt` | 完整终端输出与退出码证据 |
