# R9NT1：原生工具接口下的状态变化与真实续行

协议：`R9NT1_LIVE_NATIVE_TOOL_CONTINUATION_01`，版本：`r9nt-1.0.0`。
**本轮接入已通过R9TQ1资格的接口，不再做资格测试或smoke。它仍是开发诊断，不是新算法优越性、正式ToolSandbox榜单或RepairLens实验。**

## 固定内容与新旧边界
- 16个构造情形，人物号码／字面号码／提醒描述／Wi-Fi四个模板，各有stable、pre_relevant、post_relevant、post_unrelated。
- 两组inherited与verify_confirm，32个主回合；n02、n10各组重复一次，共4个重复回合。第一次结果始终保留为主结果。
- 冻结的cases.json、工具schema、原生工具、事件调度与评分来自R9J1/R9TQ1；顺序与原R9一致，不按结果选样本。
- 原生tools/tool_calls与role=tool回执，保留reasoning_content。不从正文、推理、代码围栏或JSON片段提取动作。
- 请求名称deepseek-flash，max_tokens=16384、thinking enabled、reasoning_effort high、tool_choice auto、非流式。不加response_format、强制选工具、beta strict或parallel_tool_calls。
- 接口和提示载体相对R9J1改变，不能做单变量归因，旧文本失败不能被新结果覆盖。请求参数与R9TQ1兼容格式一致，但新任务更长、有事件，不能保证始终成功。
- 不导入旧smoke或旧响应。第一份合格的研究响应记录本批返回model与指纹，后续必须一致；允许的首次返回标签仍为deepseek-flash或deepseek-v4-flash。这是元数据检查，不认证权重。

## 时序：特别注意同一响应中的多个工具
先检查整批结构、所有工具名、参数schema和调用ID，再执行任何工具。每份响应最多4个调用，按返回顺序逐个执行，不是并行、事务或原子动作。

一次预设状态更新发生在首个合格的写前查询实际返回后、下一个原生工具执行前。即使查询与写入在同一份模型响应中，更新也可以位于两个调用之间。查询返回值保持真实旧值，不会被改写；后一个工具执行新状态，但使用模型此前已生成的参数。**同一响应内没有机会根据本批前一个结果重选参数。**

所有本批工具回执都在下一次模型请求前按调用ID加入messages。模型可以随后查询、处理异常、补救或结束。事件只触发一次，不在每次查询后追击；跳过锚定查询的情形保留未暴露标记，不强行注入。事件标签、私有状态和分数不传给模型。

## 预算
- 每回合最多10次模型请求，包括最终自然语言结束响应。
- 每响应最多4个原生工具；每回合最多40个；全部36回合最多1440个外层工具执行，都是本地模拟。
- **新增最多360次生成请求；没有额外smoke、/models或探针。**提前结束不补次数，不因失败另开副本。
- 前R9/R9J1/R9TQ1共14份已归档响应单列，本协议最大沿革总量374。不是回收先前剩余配额，也不要求发满。
- 360×16384=5,898,240是极端输出token上界，另有输入，不是预计用量。费用UNKNOWN；次数上限不能保证金额上限。严格金额限制使用服务商侧额度。
- 不触发模型用户模拟器、评分模型、搜索服务、真实短信、真实联系人或其他外部账户。

## 用户只做真实模型必要步骤
需要Python3.11.x。可以复用已安装R9TQ1依赖的解释器绝对路径，不改旧工程；不要复制旧runs或PREPARED。
解压到全新`R9NT1_Research_Kit`。

已有环境：在新根目录运行该解释器下的`r9nt.py`。
全新安装（macOS/Linux）：
```bash
python3.11 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python r9nt.py prepare
.venv/bin/python r9nt.py status
```
Windows PowerShell：
```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe r9nt.py prepare
.\.venv\Scripts\python.exe r9nt.py status
```
prepare只校验源码/依赖/冻结快照，不调用模型，不重跑研究端规则实验。安装可能访问公开包索引。

只有本目录尚未运行main时，执行一次：
```bash
.venv/bin/python r9nt.py run --confirm-calls 360
```
Windows替换Python路径即可。**没有smoke命令。**密钥只由`LLM_API_KEY`环境变量或终端隐藏输入提供；不读.env、不搜索旧目录密钥、不贴入聊天/Prompt/命令参数/配置文件。

结束或暂停后：
```bash
.venv/bin/python r9nt.py audit
.venv/bin/python r9nt.py export
```
回传：`uploads/R9NT1_feedback_<UTC时间>.zip`。不需要自己写原因分析或修改报告。

## 先看状态，不重复付费
- completed：只audit/export，run也会原样返回，不产生新请求。
- paused/running/孤立记录/遗留锁：先确认原进程不在写入，然后只尝试audit/export；不删锁、不恢复、不复制新目录重试。
- HTTP失败、截断、结构/参数schema违规、未知工具、身份变化、异常usage：保存原响应并全局暂停；不得抽取正文或修复输出。
- 原生工具返回的合法业务异常：作为真实tool结果交给模型，在本回合原预算内继续；这不是隐藏网络重试。
- 有效的最后一条自然语言声明只表示模型终止；失败、放弃、误写均照实评分，不以任务失败停止整个批次。
- 第10次模型响应做对写入但未明确结束：终止与任务状态分别记录，不能补第11次。
- 每个已完成工具调用之后保存tool_progress。若进程在本地工具批次中途异常，审核可能需要人工复核部分前缀，不自动重放产生新的付费回答。

## 评分和信息边界
同一轨迹分别报告tool_success_proxy、goal_final、final_state_clean、trace_safe_success（主终点）。后者要求目标达成且全程没有协议定义的未授权写入；terminated独立报告。
先改错再改对不能清除误写，外部变更不能合法化更早的代理错误。提醒creation_timestamp沿用原业务投影豁免，不等于所有物理字段恢复。字面号码目标不被强行改成人物目标。

多工具响应可以影响事件暴露和读写间隔，审核另存每个工具对应的模型轮次、batch_index、事件索引及同响应写入标记。暴露是模型行为的结果，不是随机处理。主比较保留所有预定情形，不能仅挑触发者做因果推断。

32个主回合不是32个独立领域样本；16格共享4个模板、一个ToolSandbox后端、一个端点配置。不做确认性优越/等价声明，不把软件fixture数据当作模型结果。本轮尚未证明投稿贡献。
导出保留所有错误原始字节（凭据回显时定点脱敏并暂停），含免费本地状态与私有评分数据，但这些不在模型payload中；导出扫描不是全面隐私认证。HTTP正文不是TLS或服务商内部抓包，指纹不是权重认证。
