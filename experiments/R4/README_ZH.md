# R4：共享探测与硬预算下的证据刷新

版本 `r4-4.0.0`；协议 `R4_BUNDLE_BUDGET_01`。新开发实验，不是论文最终测试、外部预注册或公开benchmark成绩。旧4096、16384、R1、R2、R3目录原样保留。

## 本轮范围
三种工具语义可能变化：目录分页从0还是1开始、active状态编码、库存数值是净可用量还是包含预留的总量。任务调用本地可执行JSON API，真实完成分页、状态筛选、库存关联和聚合；不是生产API或AppWorld。程序不运行模型生成的任意SQL/Python/shell。

一次校准包可检查一个语义或两个重叠语义；单项包2额度、双项包3额度。每轮最多4额度，8个任务期间总共最多8额度。实际由工具层检查并扣减。初始化共同校准另计3个通道检查、6个等价额度，在运行期预算之外，对各方法一致。额度和0.05损失权重不是人民币、美元、token或真实耗时。

四种LLM实验方法得到相同工具和额度：
- recheck_joint：有限给定模型的精确联合DP参考。
- bundle_rollout：两步规划＋预算节奏基线的精确期望尾值，记录实际规划成本。
- bundle_myopic：相同预算/共享包下的单步最优选择，不削弱为只会单项检查。
- age_paced：预算节奏控制的加权年龄基线。

separable_projected和never只在离线表格中；规则编译器使用与LLM相同的公开输入，离线比较执行结果，不冒充新LLM成绩。联合DP、覆盖选择、rollout均有传统研究，不因加入硬预算就声称新定理。

## 固定规模
4条件（共享匹配、单项匹配、共享无漂移、共享漂移低估）×3独立流×8任务×4方法＝384主调用。每流零基第3步，joint和myopic各重复一次相同输入，共24次诊断调用。主命令408，smoke一次：**最多409次HTTP请求尝试**。

第二次响应不替换主答案，不影响后续状态，不新增探测扣费。12条流每条件只有3条，不把384行当独立样本。所有预定种子保留，不筛掉没有漂移、没有差异或不利的流。

## 1. 安装、测试、离线prepare
独立解压到 `R4_Research_Kit`，在包含 `r4.py` 的目录运行。Python3.11+、numpy==2.3.5，无需GPU/Docker/LaTeX。

macOS/Linux：
```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python r4.py prepare
```
Windows PowerShell：
```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe r4.py prepare
```
测试只使用本机HTTP fixture；它的请求和结果均为SOFTWARE_TEST_NOT_RESEARCH。完整测试不应设置过短超时；超时是本地测试中断，不是模型故障。不为通过测试修改源码。

prepare冻结代码/协议/配置/费用摘要，计算72组给定模型条件的全部结果、已知失效回归与历史RepairLens成本。无远端模型调用，不生成隐藏真实模式来挑选待跑流。若失败，直接export回传诊断，不调参数通过门槛。

## 2. 一次smoke
macOS/Linux（Windows换Python路径，参数相同）：
```bash
.venv/bin/python r4.py smoke --confirm-calls 1
```
端点和请求沿用前轮已可用标识：deepseek-flash，max_tokens=16384，thinking enabled，reasoning_effort high，不发送temperature。复用历史配置不是当前权重证明。实际是否兼容由这一次检查决定，不兼容就暂停，不猜替代ID。

密钥只从LLM_API_KEY环境变量或本地隐藏输入读取。不要把密钥发送给研究助手、本地代码助手的对话、配置文件、命令参数或反馈。脚本不读取.env，不登录账户，不充值，不购置资源。

## 3. 固定主批次
只有当前R4 smoke完成且原始响应检查通过后：
```bash
.venv/bin/python r4.py run --confirm-calls 408
```
程序记录每次请求、响应、usage、延迟、预算扣减、校准收据、任务工具轨迹。每方法有独立规划缓存，不借用另一方法的规划计算。模型只编译公开请求为有限工作流计划，最终答案由确定性执行器给出；并非自由长程Agent。

任务输出本轮不更新调度信念；只有收费校准更新，这是有限模型范围。真实工具的免费反馈、未知漂移学习、语义候选遗漏和不完整依赖均不在本轮主实验。不要将这些限制改写成已解决能力。

## 4. 审核并导出
```bash
.venv/bin/python r4.py audit
.venv/bin/python r4.py export
```
上传最后生成的 `uploads/R4_feedback_<时间>.zip`。这一个包包含smoke、全部主/重复原始记录、代码和LICENSE、私有合成评测数据、离线审核与哈希清单。私有评测仅供离线审核，不能手工交给运行模型。无需另写主观研究解释。

可验证：
```bash
.venv/bin/python r4.py verify uploads/实际反馈文件.zip
```

## 停止与安全规则
HTTP错误、截断、非法JSON、usage异常或身份字段变化：保存证据后暂停。合法JSON但违反接口或计划错误：计失败，不重采样至成功。暂停后audit/export，不解锁、不删除start、不循环smoke、不换模型/seed/cap、不新开目录绕过。

运行完成后重复同一run命令不会重新调用模型；未完成/paused/running目录不自动恢复。start与send_intent只是本地记录，不证明远端收到或已收费。预算409是请求次数上限，不是账单金额上限；严格金额限制由服务侧设置。

费用默认UNKNOWN而不是0，不猜当前价格、不换汇。可选用户费用表必须在首次prepare前配置；缺账单不阻断研究。导出排除密钥配置和系统文件，常见凭据扫描不是完整隐私认证。

## 研究解释
主结果、独立重复、规则执行器、精确模型期望必须分开。共享与单项两种环境都保留，无漂移负例也保留。不能把更换为更有利环境的结果与旧分数拼接。不会自动编译替换论文或投递。只有审核后，才决定继续、重设科学问题、或暂停下一轮模型调用。
