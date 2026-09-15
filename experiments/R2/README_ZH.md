# R2：ReCheck机制预实验执行说明
版本：r2-2.0.0 / R2_RECHECK_MECHANISM_01。**开发实验，不是论文最终测试集。**

## 本轮范围
运行新的 ReCheck 小批次；旧4096、16384和R1文件保持不变。
RepairLens本轮只有离线成本诊断，**不新增其LLM调用**。
源代码、参数、种子、方法、顺序和输出上限已冻结；不要为了结果更好而修改。

## 1. 下载、解压与安装
独立解压到 `R2_Research_Kit`，不要覆盖旧的 `LLM_Pilot_Kit`。
使用Python 3.11+。依赖沿用 `numpy==2.3.5`；不需要GPU、Docker或LaTeX。

macOS / Linux，在包含r2.py的目录：
```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m unittest discover -s tests -v
```
Windows PowerShell：
```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```
测试只使用本机回环HTTP fixture，不访问模型服务。测试数据不是LLM结果。
如果安装或测试失败，保留错误，不改代码来绕过。

## 2. 离线准备，零模型调用
```bash
.venv/bin/python r2.py prepare
```
Windows把 `.venv/bin/python` 换成 `.\.venv\Scripts\python.exe`，以下同理。

prepare创建本地配置（没有密钥）并输出：
- PREFLIGHT：只使用任务类型、年龄和模型假设，不构造隐藏模式、不读取正确答案。
- REGRESSION：用上轮真实TTL/Always记录验证新鲜性与接口归因。
- REPAIR_COST_DIAGNOSTIC：从之前的预检记录计算净成本边界。
- PREPARED：绑定配置、协议和代码哈希。

预定4条流的DP/Myopic刷新决策差异数为 `[0,0,4,4]`。
0.18等价区作为负例保留，0.22区有8个不同决策；**不是预言新方法会获胜**。
这两个参数是控制器中的无量纲代价，不是人民币/API单价。
参数选择基于已经看过的R1策略分析，已披露为开发性设计，不能称外部预注册。

## 3. 模型配置与费用
默认沿用你已使用的 `https://api.deepseek.com/v1` 和 `deepseek-flash`；
这是既往日志中的可用标识，不代表独立认证其当前权重。
输出上限固定16384。本轮显式发送：
```json
{"thinking":{"type":"enabled"},"reasoning_effort":"high"}
```
temperature不发送。相对R1默认模式，这属于新的明确配置，不能混合为同一协议。
官方接口文档对该参数格式有说明；实际兼容性仅由下面的一次smoke检查。
若端点不再接受模型ID/参数，停止回传，**不自动改名称、路由或思考强度**。

密钥只从 `LLM_API_KEY` 环境变量或终端隐藏输入读取。
不发送给研究助手、不写配置、不放入命令参数、不打印、不提交。
脚本不读取.env，不主动登录账号，不充值或购买资源。

费用默认UNKNOWN，不沿用旧价目、不自动换汇、不猜峰谷。
可选billing.local.json只用于离线估价，必须在prepare和smoke前由用户按真实资料填写；
不需要为本轮专门收集账单。缺费用仍可以分析tokens与延迟。
日历按UTC和显式工作日窗口处理，跨价格边界/资料不足保留unknown。
每个API响应的原始usage保留，缓存与思考token分开核对。

**硬上限是次数，不是金额：1次smoke + 484次主实验 = 最多485次请求尝试。**
16384是每次输出上限而非预期用量。服务商可能对失败请求收费。
有严格金额预算时，在服务侧设置额度；程序不承诺账单硬上限。

## 4. 单次接口检查
```bash
.venv/bin/python r2.py smoke --confirm-calls 1
```
应看到 `runs/R2_smoke/status.json` 为completed且smoke_result.json的json_ok为true。
如果暂停：直接用第6节export打包回传，不继续主实验。
smoke也检查返回模型ID、停止原因和usage；数据保存后才做通过/暂停判断。

## 5. 运行主实验
```bash
.venv/bin/python r2.py run --confirm-calls 484
```
固定配置：
- 4条独立合成任务流，每条12任务；
- 5策略：ReCheck、Myopic、TTL=3、Always、Never；
- 每流1次共享初始记忆写入；
- 每任务/策略2次LLM调用：生成有界计划、读取真实SQLite返回后回答；
- 共48个独立于方法的任务位置、240条方法记录、484次逻辑调用。
这些240行不是240个独立统计样本，真正的独立单元只有4条流。
状态变化由固定独立随机流产生；即使某流没有发生变化，也不替换seed。

各策略均独立调用模型，不共享最终答案缓存；只有共同初始前缀共享。
方法执行顺序预先随机排列再轮换。模型请求中不包含方法名、正确答案、
当前隐藏模式、真实漂移率、价格或未来任务。
控制器仍是给定有限模型，不是已学会通用记忆或漂移估计的LLM。
实际运行SQLite，但不执行模型生成的任意SQL、Python或shell。

## 6. 审核与回传
完成后运行：
```bash
.venv/bin/python r2.py audit
.venv/bin/python r2.py export
```
将最后一次export输出的 `uploads/R2_feedback_<时间>.zip` 上传本对话。
该ZIP同时包含smoke、主实验、配置摘要、原始请求/响应/尝试、共同前缀、
工具返回、隐藏评测数据、代码快照、离线审查和清单。
**隐藏评测文件仅用于离线审查，不得提供给运行模型。**

audit会独立重算值正确性、接口、JSON、截断、新鲜性与规范执行诊断，
并用已保存响应重建模型请求和SQLite记录。不会新调用模型。
Scientific gate始终为PENDING_RESEARCHER_REVIEW，脚本不能自动宣布论文成立。

可验证反馈ZIP：
```bash
.venv/bin/python r2.py verify uploads/实际反馈包.zip
```
不要只发汇总分数或本地助手撰写的报告。不要由本地助手猜测中断原因、
后端版本、账单或操作者动机；不知道就是unknown。

## 7. 失败、中断与重复执行规则
- HTTP/网络错误、截断、无法解析JSON、返回身份信息改变：保存原始响应后暂停。
- 合法JSON但违反接口、计算错误：按失败记录，不重试到正确。
- 未完成start不证明请求已经被服务商接收；send_intent也只是本地发送意图。
- 默认暂停后立即回传，不更换配置、不增加上限、不自动恢复或开启新目录。
- 完成的逻辑调用只在其原ID下恢复，不重新采样；已完成整个run再次运行不会新增调用。
- 没有授权的retry或unlock命令。强杀留下锁时可export，不删除锁强行续跑。
- 不删失败样本，不把R1/4096/16384和R2挑选合并。
- 根目录SOURCE_MANIFEST防止意外修改；不是数字签名或独立服务证明。
- export排除config.local.json、billing.local.json、环境变量、密钥与私有系统文件；
  常见凭据模式扫描不是完整隐私保证，上传前仍需检查响应中是否带账户资料。

## 8. 等待反馈后的决策
研究助手核查原始证据后，分别判断执行合规性、实验可区分性、效果/成本、
是否需要局部修正或新协议。阴性结果不等于违规，不靠重复运行到显著推进。
本轮不更新论文主结果、不宣称胜过GLOVE/SafeCommit，不自动启动RepairLens。
