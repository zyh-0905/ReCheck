# R3：调度净收益与模型执行噪声分离实验

版本 `r3-3.0.0`，协议 `R3_FACTORED_REFRESH_01`。这是**新的开发实验**，不是正式论文主实验、外部预注册或公开 benchmark 成绩。旧4096、16384、R1、R2目录保持原样。

## 本轮要回答什么

R2表明：刷新动作有8处不同，但真正影响任务的语义只不同2处；相同输入也出现不同输出。R3先精确评估给定模型的净收益，再用统一的混合执行架构检查真实模型是否正确使用证据。

**架构明确改变：**所有方法都只让LLM生成任务所需的计划字段；SQLite真正执行，数值答案由确定性程序呈现。没有第二次LLM回答调用。初始化由两次实际校准探测的确定性解码获得，不再学习初始记忆。只给LLM当前任务相关的语义，不给核验时间戳或无关记忆。不能把R3与R2正确率差解释为提示优化或模型推理能力提升。

## 规模与固定配置

- 离线：3种假定漂移率 ×4种检查价格 ×3种任务持续性 ×4种真实/假定漂移比 ×2种时域 = **288组精确模型配置**。每组评估ReCheck、Myopic、TTL、Always、Never；保留全部正负结果。没有真实模型调用，也不使用抽样种子筛选胜负。
- 真实端点：4条件×4条独立流=16条流；每流12任务；两种方法ReCheck、Myopic。每个任务一个计划调用，**384次主调用**。
- 每流第6个任务（零基step=5），每个方法各独立重复一次相同请求，**32次重复诊断调用**。第二次答案只做诊断，不替换主答案、不影响后续状态。
- 合计主命令416次，smoke一次：**最多417次HTTP请求尝试**，不是金额上限。
- 条件：匹配(.22,.70,.12)、匹配(.40,.95,.12)、无变化(.40,.95,0)、漂移低估(.40,.95,.24)，括号为检查价格、任务持续性、真实漂移率；控制器假定漂移率均为.12。每条件首任务类型0/1/2/3分层平衡，后续随机流独立，种子全部固定。
- 保留R2已实际使用的端点及请求格式：`deepseek-flash`、max_tokens=16384、thinking=enabled、reasoning_effort=high、不发送temperature。此处是历史配置复用，不是独立认证当前后端版本。发生不兼容或身份字段变化时暂停，不自动改模型。
- Always/TTL/Never只在本轮**离线精确期望参考**中出现，不冒充已经跑过它们的LLM结果。RepairLens本轮新增调用为0。

## 一、安装与离线检查

独立解压到 `R3_Research_Kit`，在包含 `r3.py` 的目录打开终端。Python3.11+，依赖 `numpy==2.3.5`。不需要GPU、Docker或LaTeX。

macOS/Linux：
```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python r3.py prepare
```
Windows PowerShell：
```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe r3.py prepare
```
测试包含**本机回环HTTP模拟服务**，不是向模型服务发请求。测试数据始终标记SOFTWARE_TEST_NOT_RESEARCH。不要把测试响应当作实验成果。

prepare生成离线精确表、R2六个失败案例回归、RepairLens历史成本门槛诊断和PREPARED绑定。它不生成隐藏世界来筛选付费任务。模型内机会指标约20.76是**期望值，不是已经观察到20.76次真实差异**。所有预先列出的流都保留，包括无收益流。

离线门槛失败则export回传，不改参数/seed让它通过。开始过任何请求后，不再运行prepare改写绑定。

## 二、一次接口检查

```bash
.venv/bin/python r3.py smoke --confirm-calls 1
```
Windows将Python路径换成 `.\.venv\Scripts\python.exe`。密钥从 `LLM_API_KEY` 环境变量读取，或在本地终端隐藏输入。不要把密钥写进Prompt、命令参数、配置、报告或反馈ZIP。

只认可当前R3目录的smoke，不能拿旧R2 smoke跳过检查。成功时 `runs/R3_smoke/status.json` 为completed且smoke_result的json_ok为true。

**失败、暂停、截断或缺usage时直接audit/export。**不单独curl测试模型、不循环smoke、不切换thinking或输出上限。

## 三、运行固定批次

smoke成功后：
```bash
.venv/bin/python r3.py run --confirm-calls 416
```
程序在全批次完成或中途暂停后保存原始记录，并尽可能导出反馈ZIP。所有结果都保留；接口违反或计算错误不是重新采样的理由。

若先前run为paused/running或残留写锁，拒绝新增请求。没有retry/unlock命令，不删锁强行继续。已完成run再次运行不会重新采样。

## 四、反馈

```bash
.venv/bin/python r3.py audit
.venv/bin/python r3.py export
```
上传最后生成的：
```text
uploads/R3_feedback_<UTC时间>.zip
```
包含原始请求/响应/尝试、共同校准、真实SQL返回、384个主结果和至多32个重复诊断结果、代码与LICENSE、离线审核及清单。重复结果单列，不做best-of-two。

验证ZIP：
```bash
.venv/bin/python r3.py verify uploads/实际文件名.zip
```
脚本的PASS只代表机械检查。科学有效性、重跑范围及后续实验放行仍由研究审核决定。

## 五、费用与隐私

默认价格UNKNOWN，不是免费或0元。不猜当前价格、不按固定汇率换汇、不使用旧费率冒充现在账单。可以比较token与延迟；次数上限不保证服务商账单上限。有严格金额预算应在服务侧控制。

可选billing.local.json仅用于离线估价，必须在首次prepare前设置并保留来源、模型和UTC有效区间。缺账单不阻断本轮。不要让本地助手猜星期、峰谷、后端路由、收费或中断动机。

导出不包含config.local.json、billing.local.json、环境变量、.env或私钥。常见凭据扫描不是完整隐私保证；上传前检查原始响应是否带账户信息。

## 六、结果该如何理解

1. 模型内目标J是可加语义失配损失＋无量纲探测价格，不是人民币、美元或LLM正确率。经典精确DP在假设匹配时优于部分启发式，不等于新科学定理。
2. 主结果仅使用第一次调用。重复调用的token/延迟单列为诊断开销，同时计入本次实际总量；不能偷偷忽略支付成本。
3. 每条件4条流，共16独立流；384行不是384独立样本。不同条件不能当成同一部署分布盲目合并。没有确认性p值。
4. 真实模式和正确答案只供离线评测；不提供给运行模型、调度器或本地助手用来挑选任务。
5. 成功也不直接满足发表要求：仍缺公开环境、原生近邻对照、未知漂移学习和更强的新颖性。
6. RepairLens仅把已观测成本写成条件性direct-recompute门槛。历史点估计不是未来可靠上界；没有新RepairLens算法或付费实测结论。

本轮正常完成和中断都回传ZIP；不要只发平均分，不重写旧数据，不自行扩大实验。
