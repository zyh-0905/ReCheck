# R13公开来源及真实轨迹接入检查

访问日期：2026-09-15。检索使用Exa、公开网页读取与GitHub只读接口。下载/网页读取不是LLM生成实验；没有模型或裁判账户调用。

## 1. 本轮执行采用的固定源码
- ToolSandbox: https://github.com/apple-aiml-research/ToolSandbox/tree/c8571d7854316d2e1c5f288e59fe1e34e53f6dd1
- 原生多轮任务的用户模拟器规格、允许工具和里程碑：`tool_sandbox/scenarios/multiple_user_turn_scenarios.py`，1103行开始。
- 本次直接读取的GitHub文件blob为`0df9029c1e45dcbfb8a32a253e5fae5fe09384df`，与随包源码对应。
- 原始用户规格要求先把原friends改为enemy，之后再改回friend。此处是顺序完成两个请求，不是未完成第一请求时主动取消它。不能把本轮区间规则推广到所有取消任务。

仓库release查询返回空集合，固定源树没有完整论文模型轨迹目录。README所列`data/.../trajectories/...`是运行输出路径说明，不足以证明这些文件已随仓库发布。以上只是所读入口范围，不能推出互联网上没有任何相关轨迹。

## 2. 已定位到真实公开记录，不再声称“没有数据”

### SAP/agent-quality-inspect
- 数据卡：https://huggingface.co/datasets/SAP/agent-quality-inspect
- 目录：https://huggingface.co/datasets/SAP/agent-quality-inspect/tree/main/toolsandbox
- 本次实际通过网页读取的JSON：https://huggingface.co/datasets/SAP/agent-quality-inspect/raw/main/toolsandbox/gpt_4_1/expert/trial_0_results.json
- 代码：https://github.com/SAP/agent-quality-inspect
- 查询到的runner版本：`23c256af44af28f8f7b1b94be8acdb24c8ec80ea`，`paper_experiments/runner.py`中EvaluationResult将status解释为执行状态。

数据卡列Apache-2.0。该文件头记载azure/gpt-4.1、expert用户设置、trial_id=0、37个sample。该数字是来源自述，不是本轮完成了37条重评分。网页视图读取的是main；本轮没有得到该JSON的完整本地字节，不能报告其SHA-256、冻结版本或完整语料统计。

实际定向阅读了两个记录：
1. `wifi_off`：工具调用on=false，对应SETTING快照wifi=false；本例不是达成后撤销。
2. `turn_on_wifi_low_battery_mode`：status=success，但progress_rates最后为0.5；工具链包含低电量限制异常。这里只用于确认字段语义，不把运行成功标记当作完整任务成功，不对未知执行顺序或用户后续要求作未验证归因。

这两项是**网页定向读取和模式检查**，不是完整原始文件离线核查，更不是自然回退发生率估计。没有把模型解释、LLM裁判解释复制成状态真值；没有把本数据的AUC/PPT或progress替换为ToolSandbox原始similarity。本轮尚未确认自然轨迹中的“历史满分但终态错误”案例，计为未完成检查，不计为0%发生率。

原始JSON下载分别经容器HTTP（DNS解析失败）和下载工具尝试，未成功落地；网页raw内容可读。没有执行任意下载的pickle，也没有为读取公开数据索要密钥。当前没有用户下载或运行任务。

### 次级候选，不进入主分析
https://huggingface.co/datasets/tarsur385/toolsandbox-data/tree/main

目录包含多个模型/训练配置及原生conversation、execution_context路径线索，但未完成许可证、版本、来源和原始字节检查。不能仅凭目录名宣布获得官方模型结果。本轮不再分发其日志。

## 3. 必须正面对比的已有评测研究

Talk, Evaluate, Diagnose: User-aware Agent Evaluation with Automated Error Analysis.
https://arxiv.org/html/2603.15483v1

第3.2节已经研究子目标、逐轮进展和效率；第4节明确说明ToolSandbox采用37个改编基础场景，以自然语言grading notes和LLM裁判评估，并排除原多轮变体。其AUC说明采用已完成里程碑不会撤销的假设。该假设提供了可检查的适用边界，不等于我们已证明论文表格或模型排名错误。

因此：“有中间进度”“按子目标评价”“计入多轮交互”都不是本轮独有贡献。真正下一步是：在可核对状态、用户修订范围和评分来源的公开轨迹中，检验可撤销效果与累计进度的关系；没有实际偏差就保留阴性结果。

## 4. 下一步固定顺序（未授权付费）

先取得固定版本JSON字节并保存许可证和摘要；再检验调用ID、工具回执及database_update表示全量还是增量、初始化缺失与多工具顺序。先锁定可判断的任务条件及排除理由，再按模型/用户类型/试验批次分层核查。缺失状态保留UNKNOWN。数据集status字段、subgoal进展、原始benchmark分数与我们的局部谓词分开保存。不运行LLM裁判，不选出失败后再扩样，不改已有榜单成绩。
