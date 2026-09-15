# 两篇论文的用户侧 LLM 预实验包

版本：llm-pilot-0.1。用途：你在自己的机器执行真实模型调用，回传完整记录；随后审核实验有效性、分析结果并更新研究。**不要直接把这个小样本预实验当成最终论文主结果。**

## 先看结论

第一轮建议只使用一个稳定模型：先跑 1 次接口测试，确认成功后跑 ReCheck 默认预实验（260 次逻辑模型调用）。不要先购买新硬件，不要先扩大到多个模型。RepairLens 的命令是独立的重放预检，最多 40 次调用，**不是 RepairLens 主算法效果测试**。

这个包独立运行，不必把文件覆盖到之前的 ICASSP 工程。旧论文与模拟结果不会被自动改写。`vendor/recheck_core.py` 从原工程原样保留，来源校验在 `docs/VENDOR_PROVENANCE.json`。

## 1. 安装

项目建议使用 Python 3.11 或更新版本。无需安装 LaTeX、Docker 或 GPU 驱动才能运行本轮 API 预实验。第三方 Python 依赖只有固定版本 numpy。

### Windows PowerShell

解压后进入包含 `run.py` 的 `LLM_Pilot_Kit` 目录，在该目录打开 PowerShell：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

后面的命令不需要激活虚拟环境，因此不需要修改 PowerShell 的 ExecutionPolicy。

### macOS / Linux

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m unittest discover -s tests -v
```

以下教程使用 Windows 的 Python 路径；macOS/Linux 将 `.\.venv\Scripts\python.exe` 换成 `.venv/bin/python`，其余参数相同。

## 2. 配置接口（不保存密钥）

```powershell
.\.venv\Scripts\python.exe run.py configure
.\.venv\Scripts\python.exe run.py doctor
```

`configure` 将询问接口 Base URL、精确模型 ID、输出上限参数名、输出 token 上限、请求次数上限，以及可选计费单价；保存到 `config.local.json`。**不填写或保存 API Key**。`doctor` 不调用模型、不联网，只检查本地配置。

支持范围：非流式 Chat Completions 形状的接口。Base URL 通常包含 `/v1`，但不要填写 `/chat/completions`；脚本会自行追加。实际服务路径以你的服务文档为准。**不支持原生 Anthropic Messages、仅 Responses 的端点、网页登录会话、图片/音频输入。**不做自动协议猜测或偷偷换模型。接口不支持时回传 smoke 错误包再调整适配器。

模型使用 `max_tokens` 还是 `max_completion_tokens`，按提供方文档选择；默认 `temperature=null` 表示不发送这一参数，不是 temperature=0。额外思考参数需要明确写入 `extra_body` 并固定，不会自动开关。默认输出上限 1024；推理模型可能因内部思考耗尽额度而没有完整可见 JSON，这应先在 smoke 中检查。

### 密钥如何输入

在 `smoke` 或 `run` 时，如果执行进程没有 `LLM_API_KEY` 环境变量，程序会在终端隐藏输入提示中询问密钥，只保留在当前进程内。不要把密钥粘贴到聊天、配置 JSON、命令参数、代码仓库或结果包。

若本地无需鉴权的服务运行在 `localhost`/`127.0.0.1`，可设置 `local_no_auth=true`。远程服务必须 HTTPS，不接受含用户名密码、query 或 fragment 的 Base URL，不跟随重定向携带凭据。

### 费用边界

- 默认每个运行目录最多 300 次 HTTP 请求尝试；失败和明确重试都计入，达到上限不再发请求。
- 默认 ReCheck 260 次，不含另一个目录中的 smoke 1 次；RepairLens 预检至多 40 次。
- 计费价格需由你填入，脚本不猜价格。未知 usage/价格保留为未知，不写成免费。
- `max_estimated_spend` 是本地预估停止阈值，**不是服务商硬限额**。发送前估算可能不适用某个分词器或计费策略，失败请求也可能已计费。严格费用限制应在你使用的服务侧设置。
- 不自动购买、充值、租用 GPU；不自动重试失败答案。所有金额都必须注明币种。

## 3. 第一关：只跑一次接口测试

```powershell
.\.venv\Scripts\python.exe run.py smoke --out runs/smoke_modelA
.\.venv\Scripts\python.exe run.py export --run runs/smoke_modelA --out uploads/smoke_modelA.zip
```

`smoke_result.json` 应有 `json_ok: true`，同时检查 returned_model、usage_present 和 finish_reason。它只验证连通性及最简单 JSON 输出，不证明所有任务可用。

如果出现 HTTP 401/403、404、429、参数不支持、超时或截断，不要反复重跑。不必继续大批量实验，先把 `uploads/smoke_modelA.zip` 回传。响应的 model 字段是提供方声明，不是对后端权重身份的独立证明。

修改模型或参数后使用新目录，例如 `runs/smoke_modelA_v2`；不得在同一个冻结目录内替换配置后覆写旧响应。

## 4. 第二关：ReCheck 默认预实验

确认 smoke 通过后执行：

```powershell
.\.venv\Scripts\python.exe run.py run --study recheck --out runs/recheck_modelA
.\.venv\Scripts\python.exe run.py summarize --run runs/recheck_modelA
.\.venv\Scripts\python.exe run.py export --run runs/recheck_modelA --out uploads/recheck_modelA.zip
```

默认：4 条独立任务流、每流 8 个任务、4 种策略。每流先用 1 次 LLM 调用形成所有策略共享的初始记忆；每个任务—策略组合用 2 次 LLM 调用（执行计划＋工具返回后的答案）。总计 `4 × (1 + 8 × 4 × 2) = 260` 次逻辑调用，128 条任务—策略结果。

4 种策略为原版 ReCheck DP、只考虑当前损失的 myopic、固定 TTL=3 和每次检查全部前提的 always。这里的 TTL 未通过新实验调参，不是最终“最强 TTL”主对照。

任务实际访问 SQLite，工具语义包含金额单位和时间端点。模型先给出有界 JSON 计划，再读取真实工具返回并作答；不执行模型生成的任意代码或 SQL。原始世界状态和正确答案只用于本地环境与独立离线评测，不发给模型、不返回给调度器。控制器仍是给定模型版本，不是已经学会漂移估计的完整 Agent。计划和答案每轮是限定接口，不代表自由长程 agent benchmark。

本轮用途：检查真实模型能否理解证据、生成参数、处理工具返回；区分缓存失效与模型本身的错误；测量真实 token、延迟、API 错误和初始记忆误差。**不是检验所有研究假设，也不是正式投稿统计。**

## 5. RepairLens：只做重放准备诊断（建议等首轮审核后再运行）

```powershell
.\.venv\Scripts\python.exe run.py run --study repairlens-readiness --out runs/repair_readiness_modelA
.\.venv\Scripts\python.exe run.py summarize --run runs/repair_readiness_modelA
.\.venv\Scripts\python.exe run.py export --run runs/repair_readiness_modelA --out uploads/repair_readiness_modelA.zip
```

默认 4 个程序化生成的修订案例、3 个产物。每个案例先实际调用 LLM 生成 3 个旧产物，随后固定这些字节形成共同前缀；公开源值发生修订后，比较：全部产物重新生成、LLM 选择产物再局部生成、保持旧状态。最多 40 次逻辑调用。

该诊断回答：相同前缀能否保留？局部修改会不会漏改？模型重算会不会出错？真实调用费用是否值得进一步投入？

**它没有运行原始 RepairLens 的主动假设调度，不得把 llm_selected_patch 重命名为 RepairLens，也不得据此声称 RepairLens 胜过其他方法。**规则在公开任务中给出，日志中的依赖记录不完整，但这不是任意隐含依赖学习。源值修订案例不是自然收集的 agent 失败。后续正式算法实验需要在这些边界检查通过之后单独冻结协议。

## 6. 中断与续跑

正常按 Ctrl+C 后，重新执行完全相同的 `run` 命令、同一配置和同一目录。已经完成的逻辑调用按 request hash 恢复，不重复付费重采样；模型答错、无效 JSON 和截断响应也会原样保留，不自动“修到正确”。方法间不共享最终答案缓存，只有明确设计的初始前缀共享。

HTTP/网络失败已经记录，明确允许重试基础设施故障时：

```powershell
.\.venv\Scripts\python.exe run.py run --study recheck --out runs/recheck_modelA --retry-failed-requests
```

如果程序在已发出请求但尚未写回响应时被强制关闭，请求可能已经收费。核实日志后才使用：

```powershell
.\.venv\Scripts\python.exe run.py run --study recheck --out runs/recheck_modelA --retry-uncertain
```

每一次重试都新增记录并计入请求上限。不是重试模型答案。

程序阻止同一目录两个写进程并发运行。强杀后有遗留锁时，先确认原进程确已停止，再运行：

```powershell
.\.venv\Scripts\python.exe run.py unlock --run runs/recheck_modelA --confirm-stopped
```

达到固定请求次数上限时，不要通过修改配置、删除旧请求记录绕过。回传已有包，先审查原因。不要同时运行多个变体或改动冻结的任务、提示、种子；这会使续跑被拒绝，或导致结果不可比较。

## 7. 回传什么

优先上传 `uploads/recheck_modelA.zip`；若第一关失败则先上传 `uploads/smoke_modelA.zip`。后续按需加 RepairLens 预检包。不要只发截图、平均分、论文表格或成功样本。

导出包括：

| 内容 | 用途 |
|---|---|
| manifest.json | 模型配置摘要、协议、代码哈希、运行环境；端点只保留哈希 |
| calls/、attempts/ | 完整生成请求正文、响应、usage、finish_reason、延迟、错误、所有尝试 |
| prefixes/ | 共同初始记忆或失败/修订前缀 |
| records/ | 每个任务与策略的执行结果、工具返回、错误和调用关联 |
| private/ | 离线评测所需的合成环境真值；这些没有进入模型请求 |
| code_snapshot/ | 产生这批数据的实际代码版本 |
| summary.json、per_task.csv | 离线汇总与逐例评分 |
| EXPORT_MANIFEST.json | 导出文件的 SHA-256 索引 |

API 密钥和 Authorization 请求头不写日志；`config.local.json`、`.env`、虚拟环境、机器其他目录、私钥不在导出白名单内。接口响应若包含你的账户信息，上传前检查，必要脱敏需保留脱敏说明；不要擅自删除失败案例。

同时用一句话注明模型服务商、模型是否固定版本、有没有自动路由/回退、计费币种及实际账单与本地估计是否一致。未知就写未知。

## 8. 回传后的研究审核

先审查代码/配置一致性、请求记录完整性、隐藏答案泄露、共同前缀、错误率、token 与费用缺失，之后才比较方法表现。Pilot 数据全部留在开发/诊断用途，不偷偷变成最终测试集。

通过后再单独设计：ReCheck 的第二环境、自然语言依赖、学习到的漂移、公开任务和近邻原生对照；RepairLens 的主动调度、随机重放校验、候选覆盖与真实昂贵工作流。最终实验需新冻结的数据/任务族与统计协议。阴性结果也保留，不能以“反复运行到显著”为完成标准。

## 9. 本包已验证与未验证

本包的单元测试与本地 HTTP fixture 测试不调用真实 LLM。fixture 输出明确标为 `SOFTWARE_TEST_NOT_RESEARCH`，不能混入你的真实模型结果。实际提供方的连通性、参数兼容和性能由你执行 smoke/pilot 后才能确认。

标准 Python API 测试与代码审查不是独立同行审核；这里也没有替用户完成任何购买、模型训练、公开 benchmark 验证或论文投递。
