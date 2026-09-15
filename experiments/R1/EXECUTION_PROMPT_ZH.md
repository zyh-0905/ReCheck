# 本地执行 Prompt：R1 中断批次证据补齐

将下面整段交给已打开本地工作区的代码助手。把本任务包和原 `LLM_Pilot_Kit` 的位置告诉它即可；不要提供 API Key。

---

你是本次研究的本地执行者，不是实验设计者或最终审稿人。请完成任务 `R1_EVIDENCE_COMPLETION`。

## 目标

仅补齐此前输出上限4096的中断 ReCheck 批次原始记录，生成一个可回传审查的ZIP。本轮不是新实验，不续跑、不重试、不改模型参数，不覆盖任何既有实验。

默认目标为原实验工程中的：
`runs/recheck_deepseek_v41_flash`

不要误选 `recheck_deepseek_v41_flash_cap16384`。16384完成批次已回传，无需重跑。

## 权限与停止边界

1. 允许读取用户明确指定的原工程目录和本任务包；允许在本任务包的 `uploads/` 写入新反馈ZIP。
2. 不调用任何模型实验API，不联网取数据、不购买资源、不读取或打印环境变量全集、`.env`、`config.local.json`、Cookie、密码或私钥。
3. 不执行原工程的 `run`、`smoke`、`summarize`、`unlock`，不运行 `--retry-uncertain` 或 `--retry-failed-requests`；不删除旧锁、不修改旧manifest、不移动、覆盖或补写原始日志。
4. 不调整研究方法、种子、任务、提示或参数；不把不完整批次命名为“完整通过”。
5. 只在用户指定工作区或明确给出的原工程位置定位文件，不扫描整个硬盘/主目录。路径不明时只询问路径，不索取密钥。
6. 先确认没有实验进程仍在向原目录写入。如果仍在运行，不要自行终止或续跑，向用户报告并停止收集。
7. 原始记录不存在、被移动或已经丢失时，如实报告；不得重新调用模型来“补齐”历史。
8. 发现疑似敏感信息时不输出敏感值，不改写原证据。保留安全诊断，报告阻断；后续脱敏需独立副本及明确说明。

## 执行步骤

A. 阅读本任务包的 `README_ZH.md`、`TASK_CONTRACT.json`、`collect_feedback.py`。代码是独立的Python标准库脚本，不需要安装新的依赖。

B. 使用现有 Python 3.10+。可先在任务包根目录运行：

```bash
python3 -m unittest discover -s tests -v
```

Windows 可用 `python` 代替 `python3`。测试不调用真实模型。不要为了让测试通过擅自修改代码。

C. 如果用户已知中断情况，可复制 `operator_statement.example.json` 为 `operator_statement.json`，只填写用户确实知道的内容。未知写 `unknown`，账单没有写 `unavailable`。这份说明是可选的；不要猜测中断原因或替用户编造说明。

D. 在确认旧实验写入已停止后执行：

```bash
python3 collect_feedback.py --project "/用户指定的原工程路径/LLM_Pilot_Kit" --stopped
```

带可选说明时：

```bash
python3 collect_feedback.py --project "/用户指定的原工程路径/LLM_Pilot_Kit" --stopped --statement operator_statement.json
```

原运行目录确实改过名字时，可用 `--run runs/实际目录名` 指向同一旧批次；不要修改 `TASK_CONTRACT.json` 中的期望fingerprint来使不相符的数据通过。错批次会被如实标注。

E. 账单是可选证据。仅当用户已提供脱敏的TXT/MD/JSON/CSV文字记录时，才加入 `--billing-note "/用户指定的脱敏账单说明.md"`。不要登录服务商账号，不读取用户账户连接，不自动抓取账单。图片/PDF账单由用户检查后单独上传，不由脚本自动采集。

F. 读取终端输出的 `return_zip` 路径，并执行：

```bash
python3 collect_feedback.py --verify "生成的ZIP完整路径"
```

G. 到此停止，不继续任何付费实验。即使状态为 `EVIDENCE_WITH_ISSUES` 或 `MISSING_SOURCE`，也回传诊断包，不用重新跑模型修复历史。`BLOCKED_SENSITIVE_CONTENT` 只应导出诊断而没有原始证据；这不是允许你关闭安全检查。

## 最终向用户交付

输出真实生成的ZIP路径、完整性验证是否通过、找到的开始/结束/完成调用数量、未完成请求和截断数量、是否缺少文件、是否提供账单说明，以及本轮新增模型实验调用为0。不要仅提供平均分、截图或“所有检查通过”一句话。

所有自动判定仅是证据收集和账本检查，不是研究有效性、结果显著性、模型权重认证或论文可投稿的最终结论。将ZIP交回研究审核者，由其决定保留数据、局部修正、另开新批次或停止某条路线。

---
