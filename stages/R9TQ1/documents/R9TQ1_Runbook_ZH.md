# R9TQ1：原生工具调用接口资格测试（最多12次请求）

协议：`R9TQ1_NATIVE_TOOL_QUALIFICATION_01`，版本`r9tq-1.0.0`。
**不是R9主实验，不是新算法结果，不自动启动360次研究请求。**只跑一次固定的小规模资格测试。

## 此前材料与本次边界
旧R9、R9J1各有2份生成响应，均未形成完整主回合，继续原样保留。
本次不再让模型在content里写动作JSON。使用API的tools/tool_calls和role=tool真实回执，
并按官方思考模式要求原样保留reasoning_content进入后续messages。
不从散文/推理/代码围栏里提取或执行任何动作，不生成虚拟工具返回，不用LLM修复格式。

本次请求模型明确改成当前官方文档列出的`deepseek-flash`。
前两轮请求为`deepseek-v4-flash`；这不是声称两者同权重或别名关系。
输出上限16384，thinking enabled，reasoning_effort high，stream=false，tool_choice=auto。
不使用JSON response_format、forced/required工具、beta strict或未列出的parallel_tool_calls参数。
参数、消息角色和指令都已变化，因此本次数据不能与旧设置做单变量效果比较。

## 三项测试与预算
|测试|实际内容|工具集合|请求上限|
|---|---|---|---:|
|q0_read|原生读取蜂窝状态；通过真实回执后回答CELLULAR_ON/OFF|只读状态工具1个|2|
|q1_message|原失败任务的公开历史与明确号码消息任务；不注入外部更新|原R9白名单11工具|5|
|q2_reminder|完整历史与提醒查找/修改任务；不注入外部更新|原R9白名单11工具|5|

总计最多12次，不另做smoke，不发GET /models，不做curl或SDK探针。
每个案例提前完成即停，不把未用额度转给其他案例；一个案例不合格就不继续后续案例。
每条响应最多接受4个原生工具调用，先检查整批结构再按返回顺序执行；
这不是并行或原子执行，所有回执都有实际调用ID。一次生成多个调用看不到本批前面
调用的结果，依赖性错误会由原生工具实际报错，不能假造回执。工具异常可在原请求
上限内继续处理；结构违规/未知工具/参数违规整批执行前暂停。
每个案例最多8/20/20次外层工具调用（12个请求共最多48次），仅本地模拟操作。

这不是3个独立科研样本，也不计算ReCheck成功率。
全部请求耗尽输出上限时最多196608个输出tokens，另有输入；这是极端上界，不是预计花费。
货币UNKNOWN，次数上限不是账单上限。严格金额限制在服务商侧设置。
加上此前4份响应，当前已明确授权的资格沿革最多16次；不叠加旧主实验的未用预算。

## 环境与准备
解压到新目录`R9TQ1_Research_Kit`；不覆盖任何旧目录。
需要Python 3.11.x。已经安装R9J1依赖的解释器可以用绝对路径复用；无需重装或跑全套测试。
不要复制旧runs、PREPARED或响应身份文件。

全新环境，macOS/Linux：
```bash
python3.11 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python r9tq.py prepare
```
Windows PowerShell：
```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe r9tq.py prepare
```
安装可能联网下载公开依赖。prepare只校验源码、固定依赖和3个快照；不调用模型，
不重复离线研究，不发送真实短信，不操作系统实际设置。

## 唯一模型命令
先查看状态：
```bash
.venv/bin/python r9tq.py status
```
仅当本目录从未运行资格测试时执行：
```bash
.venv/bin/python r9tq.py qualify --confirm-calls 12
```
Windows替换解释器路径，其他参数不变。
密钥仅由本地LLM_API_KEY或终端隐藏输入提供；不要发到聊天、命令参数、配置文件或Prompt。
代码不读取.env，不搜索旧目录，不查余额或其他模型。

若completed或completed_not_qualified：仅audit/export，不重抽样。
若paused/running/孤立账本/遗留锁：不要删除锁或恢复；确认无进程继续写入后导出可得证据。
不打开新副本试到成功，不换模型、不增加请求/输出限制。已完成运行再次调用不会新采样。

## 回传
完成或暂停后：
```bash
.venv/bin/python r9tq.py audit
.venv/bin/python r9tq.py export
```
上传最后生成的`uploads/R9TQ1_feedback_<UTC时间>.zip`即可，不需写主观结果解释。
audit失败也保留结果并export。若有遗留锁而export拒绝，不删锁，回传错误说明；
不在仍写入时打包。实际HTTP响应原始字节存档，但若发现回显密钥会做定点脱敏、标记并暂停；
此时不得声称wire原字节不变。导出还有凭据模式扫描，但不是全面隐私审计。

## 验收范围
分别报告：响应结构、真实回执链接、模型是否明确结束、模拟状态是否满足资格条件。
纯散文即使说工具成功也不会执行；若没有真实原生调用，资格不通过。
接收正确结构不保证工具参数/任务都正确；例如重复发送仍是任务违规。
q0核对回执中的实际布尔值；q1/q2检查状态与全过程副作用。
后两者的自由结束语不由模型裁判自动判断真实性，研究端回传后人工式逐条审阅。
记录request/response标签及指纹，仅表示元数据一致，非权重认证。
所有思考文本只作为接口上下文与审计保存，不用于解释模型内部因果。
通过本资格测试也不能自动放行完整研究批次；等待回传审查与新协议。
RepairLens无新增调用，旧R9分数不回填。
