# R7C1：R7C请求/返回标签校验修订

协议 `R7C1_NATIVE_AGENT_DIAGNOSIS_01`，版本 `r7c-1.0.1`。
**这是模型接口门槛修订，不是新科研方法，不更改任务、提示、分组、种子、工具、评分或结果选择规则。**
R7C旧批次仅完成1次接口请求、0个任务回合。旧目录和paused状态原样保留；不要覆盖、解锁或导入成新smoke。

## 本次唯一功能修订
请求仍固定为 `deepseek-v4-flash`，所有请求参数与旧版相同。旧版要求返回model与请求model逐字相等；已保存的一次响应返回 `deepseek-flash`。
新版仅在新smoke建立身份记录时允许两个明确的返回标签：`deepseek-v4-flash`、`deepseek-flash`。之后每次调用必须与**本次smoke**的返回model及system_fingerprint完全一致；任何变化均暂停。请求字段不能改、不能前缀匹配、不能自动换模型或地址。
两标签被允许只表示一个已披露的元数据协议：**不是对别名关系、相同权重、正确后端或服务商内部路由的认证。**论文记录request/response标签对，不把它写成已核实模型版本。
公开文档仍列出请求名deepseek-v4-flash；观察到的其他返回名依据保留的smoke证据，不是声称官方已经确认该映射。

## 固定实验内容（不变）
14构造情形，3意图模板、2底层工具领域；stateless/inherited/resolve_rule三组。
42主回合＋6独立重复回合，每回合最多8次请求；完成即停止，不强行发满。
模型自主选工具；仅操作包内模拟联系人、消息和提醒。无真实短信、无用户模拟器、无评分模型。
工具权限、模型提示、初始任务、状态变化、私有评测和评分代码与1.0.0保持逐字节一致。
重复结果不得替换主结果；首次误写不会被事后纠正抹去。

## 请求与预算
- 请求：deepseek-v4-flash；max_tokens=16384；thinking enabled；reasoning_effort high；stream=false；不发送temperature。
- 本修订新smoke上限1次；主run上限384次；**本修订新增最多385次请求尝试**。
- 旧R7C已记录1次，因此已记录生成调用的整个修订沿革**累计最多386次**。比原最大预算多一次smoke；本地脚本不自行启动，只有你执行确认命令才产生调用。
- 未回传的额外探针不在这个可核对的累计数中。所有额外GET /models、curl、SDK检查、聊天试探都不属于本轮操作；不要执行。
- 费用UNKNOWN，次数上限不是金额上限。额外smoke也可能收费；严格金额预算由服务商侧控制。
- smoke请求本身已不变；这是独立新检查，不重写旧响应或扣掉旧花费。

## 执行（用户只运行真实端点必要步骤）
解压到**新目录R7C1_Research_Kit**，不要覆盖原R7C_Research_Kit。
需要Python3.11.x；已经装好旧包requirements的3.11解释器可直接复用，只将脚本路径指向这个新目录，不改旧工程。无须重跑完整单元测试。

全新安装，macOS/Linux：
```bash
python3.11 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python r7c.py prepare
.venv/bin/python r7c.py smoke --confirm-calls 1
```
Windows PowerShell：
```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe r7c.py prepare
.\.venv\Scripts\python.exe r7c.py smoke --confirm-calls 1
```
准备和导出不访问模型。smoke须status=completed、shape_ok/json_ok=true；否则直接audit/export，**不要运行主批次试探是否被拒绝**。

smoke通过后：
```bash
.venv/bin/python r7c.py run --confirm-calls 384
```
完成或暂停后：
```bash
.venv/bin/python r7c.py audit
.venv/bin/python r7c.py export
```
Windows替换Python路径。虽然程序名仍为r7c.py、内部日志目录仍为runs/R7C_smoke和R7C_main，但它们位于全新R7C1根目录，不与旧目录混用。导出名是：
```text
uploads/R7C1_feedback_<UTC时间>.zip
```
回传这个完整ZIP即可。不要单独编写肯定性研究结论。

## 停止规则与隐私
密钥只从LLM_API_KEY或终端隐藏输入读取，不贴入聊天、命令参数、配置文件或反馈。不得搜索旧目录的密钥；不读.env。
HTTP错误、截断、非法JSON、usage异常、缺少有效指纹或批次内身份变化：保留响应后暂停。合法JSON的工具错误可在原8轮内恢复，无隐藏重试。
不删锁、不循环smoke、不换模型、不提高预算、不改源码；失败亦导出。已完成run重复执行不新增调用。
导出有凭据模式扫描，但不是全面隐私认证。离线审核的mechanical_pass只表示机械一致性；execution_complete单独报告，科学判断始终待审核。

## 可得与不可得的结论
允许收集一个显式请求/返回元数据记录下的受控诊断样本。不能声称已认证权重；不能将0任务旧smoke写成0%成功率；不能宣称ReCheck优越或官方ToolSandbox榜单；RepairLens无新增调用。
