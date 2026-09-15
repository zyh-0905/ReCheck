# R1：中断实验记录补齐包

**这一轮只收集旧记录，不运行新实验。**脚本不调用网络、不执行原实验代码，不需要API Key，不读配置密钥，不改原始文件。使用Python 3.10+标准库即可，不需要pip安装。

## 你现在做什么

解压本包，在包含 `collect_feedback.py` 的目录打开终端。确认原实验已经停止写入后：

macOS / Linux：

```bash
python3 collect_feedback.py --stopped
```

Windows：

```powershell
python collect_feedback.py --stopped
```

脚本会询问**原LLM_Pilot_Kit工程文件夹的完整路径**，不是本收集包路径，也不是ZIP路径。例如原工程中应能看到 `run.py`、`pilot/`、`runs/`。请不要输入密钥。

也可以直接指定路径，便于本地代码助手执行：

```bash
python3 collect_feedback.py --project "/完整路径/LLM_Pilot_Kit" --stopped
```

`--stopped` 表示你确认没有进程仍在写旧日志；它不杀进程、不删锁、不判断进程是否活跃。发现旧 `.run.lock` 会记录警告并保留文件。不要运行旧工具的unlock或retry命令。

## 默认收集的旧批次

```text
runs/recheck_deepseek_v41_flash
```

它是此前4096输出上限的中断批次。脚本核对期望上限、study、旧fingerprint、已上传manifest的哈希，以及请求和代码快照。不会根据当前 `config.local.json` 去改旧文件，也不会自动寻找一个“更好”的16384批次替代。

目录改名时，可显式指定同一个旧批次：

```bash
python3 collect_feedback.py --project "/完整路径/LLM_Pilot_Kit" --run runs/旧批次实际目录名 --stopped
```

路径确认正确而旧目录不存在时，脚本生成 `MISSING_SOURCE` 诊断包。这是可回传的结果，**不得重做一次实验冒充旧记录**。若原工程文件夹本身不存在，请先确认原工程实际位置，不要新建空工程来通过检查。

## 反馈包在哪里

默认在本工具包的 `uploads/` 下生成：

```text
R1_evidence_<UTC时间>.zip
```

终端会显示完整路径。反馈包包括：

| 文件 | 内容 |
|---|---|
| LOCAL_CHECKS.json | 文件身份、请求账本、缺失/截断、代码快照等检查 |
| TASK_CONTRACT.json | 本轮任务边界：零模型调用、不修改旧实验 |
| evidence/run/ | 按白名单复制的原始字节，包含失败与中断记录 |
| operator/ | 仅包含你显式选择提供的说明或脱敏文字账单 |
| BUNDLE_MANIFEST.json | ZIP内文件的SHA-256索引 |

可再验证：

```bash
python3 collect_feedback.py --verify "uploads/实际生成的文件名.zip"
```

**上传这个ZIP即可，不要只发截图或汇总分数。**自动检查通过只表示包装和检查完成，不表示科研结论成立。

## 中断说明与账单：可选

复制 `operator_statement.example.json` 为 `operator_statement.json`，只填已知内容。未知保留unknown。然后加：

```bash
python3 collect_feedback.py --project "/完整路径/LLM_Pilot_Kit" --stopped --statement operator_statement.json
```

字段说明：`interrupted_run_status` 为旧批次现状；`reason` 为已知中断原因；`billing_status` 为是否能提供账单；`other_calls_in_billing_window` 为同一账单窗口是否包含其他调用。不要猜测。

账单有则提供脱敏TXT/MD/JSON/CSV，加 `--billing-note 文件路径`；没有无需额外获取、不需要登录账号。必要的时间范围、时区、币种、扣费及请求对应关系应保留，账号身份等应先脱敏。截图或PDF只能用户自行检查后单独上传，脚本不读取。

**缺账单会限制“实际结算金额”结论，不阻断其他算法研究。**没有账单或日志丢失，均可在后续审核中如实限定证据，不无限要求你补交无法恢复的材料。

## 状态如何处理

| 状态 | 含义与操作 |
|---|---|
| READY_FOR_REVIEW / READY_FOR_REVIEW_WITH_INTERRUPTION | 原始材料已收集；中断保留并非失败；上传ZIP |
| EVIDENCE_WITH_ISSUES | 发现缺项、不一致或错批次；上传ZIP供判断，不改原记录 |
| MISSING_SOURCE | 默认旧运行目录不存在；确认路径后说明实际情况 |
| BLOCKED_SENSITIVE_CONTENT | 命中常见凭据模式，原始数据未导出；只回传诊断包 |
| SOURCE_UNSTABLE | 收集期间源文件变化，原始数据未导出；确认写入停止后另生成新包 |
| COLLECTION_BLOCKED / SOURCE_PATH_REJECTED | 路径、格式或大小问题；反馈错误，不关闭检查 |

输出文件已存在时脚本拒绝覆盖。默认时间戳文件名避免碰撞。没有API自动重试，不会把错误JSON修成成功答案。

## 权限与局限

白名单限定为旧运行的日志、原始响应、前缀、私有合成真值、已登记代码快照及汇总；不会收集`.env`、`config.local.json`、私钥、其他目录或环境变量。命中常见凭据模式时停止原始证据导出，不自动改写数据。此检查不是任意个人隐私或隐蔽密钥的完整检测；上传前仍请检查。

脚本只核对所复制源文件在收集前后的字节稳定性，不认证历史所有运行都已提供、不证明服务商后端模型身份、不替代独立科学审核。含缺失或截断记录并不自动构成研究违规，隐瞒、替换或错误解释才会破坏证据。

单元测试使用软件测试样例；离线兼容性验证只读取以前已回传的三个完整包及中断摘要。**没有生成、恢复或冒充本次尚缺的原始中断数据，也没有新调用模型。**验证日志位于verification/。
