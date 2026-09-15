# R7C：真实LLM的目标绑定与旧证据问题诊断

协议：R7C_NATIVE_AGENT_DIAGNOSIS_01 / r7c-1.0.0。
这是基于固定ToolSandbox原生工具的研究者构造扩展，不是官方榜单、ReCheck优越性实验或RepairLens实验。
研究端已完成离线代码、规则基线与测试；用户只运行真实端点阶段并回传。

## 固定内容
- 三种意图模板：按人的当前号码发消息、按用户指定的字面号码发消息、修改当前具有某文本的提醒。
- 两个底层领域：联系人/消息与提醒；不是三个独立数据集。
- 12个核心情形：3模板 × 无变化/无关变化/变化后旧观察/变化后新观察。
- 另2个消息任务同时包含联系信息变化与蜂窝服务关闭，共14个构造情形。
- 每情形三组：stateless（删除全部前任务记忆/观察）、inherited（保留它们）、
  resolve_rule（与inherited相同信息＋一句通用写前身份/描述核验规则）。
  stateless是信息消融，不是长度匹配或同信息策略对照。所有组有相同工具权限和8轮上限。
- 42主episode；c02、c10在每组再运行一次，共6重复episode。
- 每episode至多8次LLM请求，每次只执行一个JSON动作或done。
- 主run最多384次HTTP请求尝试，smoke最多1次，合计上限385。**不是必须发满385次。**
- 重复仅初始输入/状态严格相同；若自主轨迹不同，后续请求也可不同。
  重复不替换主结果，不采用best-of-two。
- 当前请求开始后，环境不再注入变化；没有TOCTOU或并发安全保证。
- 真实工具反馈供模型继续决策。评分、私有目标、变化标签、原生全数据库不传给模型。
- 预置对象全部来自公开模拟数据或本研究构造；短信仅为模拟数据库行。
- 新模型ID是官方当前文档列出的deepseek-v4-flash；不是历史deepseek-flash的自动重命名，
  不声称二者权重相同。R7C是新协议，不混合前轮分数。smoke返回不兼容时停止。
- max_tokens=16384，thinking enabled，reasoning_effort high，stream=false，不发送temperature。
  采用JSON动作文本，不发送API原生tools参数；保存reasoning_content但不将其用于因果解释或回传到模型。
- 费用UNKNOWN。385×16384=6,307,840是全部请求均耗尽输出上限时的名义输出token总上界，
  不是预计用量，也不包括输入；服务商计费以账单为准。次数上限不保证金额上限。

## 安装与机械准备（不是要求你重跑离线研究）
需要Python 3.11.x。上游ccy/NumPy/Polars是固定旧版本，不在Python3.13上强改源码。
解压到新的R7C_Research_Kit，保留R1—R7B原文件不动。
macOS/Linux：
```bash
python3.11 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python r7c.py prepare
```
Windows PowerShell：
```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe r7c.py prepare
```
安装可能访问公共包索引。prepare只校验源码、固定依赖和14个本地快照，不调用模型。
不要安装整个上游所有云角色依赖，不要启动其CLI或用户模拟器。
无需RapidAPI、OpenAI账号、GPU、Docker或LaTeX。openai包仅是上游类型导入依赖，不被本运行器调用。
这里已完成离线研究测试；不要求你再运行整套单元测试。

## 只做一次smoke
```bash
.venv/bin/python r7c.py smoke --confirm-calls 1
```
Windows替换解释器路径即可。密钥只由本地LLM_API_KEY环境变量或隐藏终端输入读取。
不要将密钥写到Prompt、命令参数、配置或回传文件。本程序不读取.env。
smoke必须completed，shape_ok和json_ok为true，才能运行主实验。

## 运行固定批次
```bash
.venv/bin/python r7c.py run --confirm-calls 384
```
每episode遇done自动结束；完成所有固定episode后结束整个run，不会补齐剩余额度。
真实模型自行选工具和参数；执行器不自动代它查联系人或修好错误。
无用户模拟器、无第二个评分模型，所以上述预算涵盖全部本轮LLM请求。

## 审核与回传
完成或暂停后：
```bash
.venv/bin/python r7c.py audit
.venv/bin/python r7c.py export
```
上传最后生成的uploads/R7C_feedback_<UTC时间>.zip。只要完整ZIP，不需另写成功原因报告。
里面包含原始请求响应、逐轮动作、工具结果与状态、快照、私有评分对象、源码和清单。
审核会用已有响应重建所有完成episode的请求，并运行原生工具重放与独立状态评分。
audit中的UUID/时钟重放只用于复现原生随机字段，不产生新模型答案。
若audit非零仍可export，不删失败记录。

## 停止规则
HTTP/协议错误、输出截断、非法JSON、usage缺失或身份字段变化：保存后暂停整个批次。
合法JSON但工具名/参数不合法，或原生工具返回错误：作为一次失败动作交给模型，可在8轮内恢复。
任何误写都在轨迹评分保留；之后改对不会抹除先前误写。
第8轮已完成正确写入但未done，状态达成与终止标记分别报告，不偷偷追加请求。
暂停/运行中/有锁的目录不自动恢复；完成run再次启动不会重采样。
不要删锁、不循环smoke、不切换模型/seed/提示/cap、不新开目录挑选好结果。
start/send_intent是本地登记，不是服务商接收或收费证明。
没有外部账户写操作；仅模拟工具白名单，模型不能执行任意Python/shell。
这不是操作系统级恶意代码沙箱。依赖只从固定公开来源安装；不暴露私人文件或连接器。
导出有常见凭据扫描，但不是全面隐私认证。上传前检查原始响应是否含账户信息。

## 研究解释
42主episode不是42独立样本；14构造情形共享3模板/2工具领域，只作机制诊断。
正面和负面情形全保留；未知或请求失败不编造任务成绩。
通用resolve规则不是新算法；脚本规则正确不代表LLM会采用规则。
主/重复/本地脚本三类结果分开。没有通过结果自动启动后续实验或提交论文。
本轮不授权额外模型和RepairLens调用。
