# R9J1续行Prompt：先读状态，不重复付费

请在用户明确提供的本地工程路径内，执行冻结的R9J1真实模型诊断。不要自行设计实验、修订代码、选择样本或解释胜负。

## 1. 唯一版本与范围

- 执行包：Research_Handoff_R9J1.zip。
- ZIP SHA-256：0ed0d58c4a6824322ec10b61e70dd7af2740e8778363ff8ed122bdfdfd03fdeb。
- 新目录：R9J1_Research_Kit。程序仍叫r9.py。
- 协议：R9J1_LIVE_CONTINUATION_DIAGNOSIS_01；版本r9-1.0.1。
- 16个构造情形，inherited和verify_confirm两组，32个主回合、4个独立重复回合；每回合最多10个模型请求，含done。
- 本包已经显式启用response_format={"type":"json_object"}。不提取第一个JSON、不合并多动作、不调用模型修复输出。
- 本轮是上一份R9J1的续行指引，不授权另建一份相同实验重新采样，不增加预算。

## 2. 先检查已有本地状态

只在用户提供的路径中读取protocol.json、源码清单、PREPARED.json、runs/R9_smoke/status.json、runs/R9_main/status.json及必要的锁/账本文件。不要搜索私人目录或凭据。

A. 本目录main已经completed：不要调用smoke或run，只audit/export。
B. 本目录smoke已经completed且shape_ok/json_ok为true，main从未启动、没有锁或孤立账本：不再smoke，仅运行主批次一次。
C. 全新且从未尝试R9J1：prepare，一次smoke；只有成功才运行一次主批次。
D. 任何paused/running/孤立请求/遗留锁：不要恢复、重试或删除锁。仍在运行时不并发读写导出；确认原进程不再写入后，只audit/export，并如实记录状态。不要强行终止用户进程。
E. 只有旧R9目录：它不是R9J1。保留旧目录，在独立R9J1目录执行；不得复制旧runs、PREPARED或旧smoke。
F. 路径或状态不明：先询问路径/状态，不试发请求判断。

## 3. 运行环境

Python 3.11.x。已有R9环境可复用其解释器绝对路径，但脚本必须指向新R9J1目录。不要复制整个旧工程，不需要重新执行研究端的规则实验、全部单元测试或离线fixture。

如确实需要新建环境：

macOS/Linux：
```bash
python3.11 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

Windows PowerShell：
```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

依赖安装可访问公共包索引；这不是模型实验。不要启动上游CLI或用户模拟器。

## 4. 真实模型命令（仅执行符合状态的步骤）

以下PY代表已安装依赖的Python 3.11解释器；实际命令请替换，不能将PY当成字面命令。

```text
PY r9.py prepare
PY r9.py smoke --confirm-calls 1
```

仅当前新目录smoke completed且json_ok/shape_ok通过后：

```text
PY r9.py run --confirm-calls 360
```

本轮请求字段固定为包内配置。不要更换base_url/model、JSON模式、思考设置、输出上限、提示、工具权限、种子、任务顺序或轮数。

密钥仅由本地LLM_API_KEY环境变量或用户在运行进程终端中的隐藏输入提供。不把密钥贴到助手聊天、命令参数、日志、配置或反馈文件；不读取.env，也不搜索旧目录寻找密钥。非交互终端无法安全输入时暂停，交由用户在自己的终端处理，不将密钥传给助手。

## 5. 预算与停止

R9J1新smoke最多1次，主命令最多360次；本包总上限361次。加旧R9已经记录的2次响应，沿革累计上限363次。本续行不增加额度。提前done就停止，不补发至上限。次数不保证账单金额，费用仍UNKNOWN。

不要执行额外curl、/models、聊天探针、第二模型或并发实例。HTTP错误、截断、非法JSON、usage异常、返回身份变化出现时，保留证据并暂停。不通过增大上限、删除错误日志、重开新目录或循环smoke修到成功。

合法JSON下的工具/参数异常由原运行器在10轮内交给模型处理，这是协议允许的任务决策，不是后台重新采样。

## 6. 回传

完成或停止且无进程继续写入后：
```text
PY r9.py audit
PY r9.py export
```

即使audit非零，也尝试export；不要改数据以匹配校验。只将最终导出的uploads/R9J1_feedback_<UTC时间>.zip交给用户上传。

若export自身失败，保留终端错误和所有原始文件，不自行扩大导出范围。不得把密钥、.env、私人文件放入反馈。

只报告真实执行状态、已保存请求数量、导出路径和异常，不自写“研究已成功”结论，不自动进入R10，不编造未执行环节。已经完成则只导出，绝不再次运行到获得更好结果。
