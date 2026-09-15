# R10：目标选择与最小写入的真实模型诊断

协议 `R10_SELECTION_AND_WRITE_SCOPE_DIAGNOSIS_01`，版本 `r10-1.0.0`。
研究端已经完成所有离线实验。你只执行下面的真实模型步骤。

## 这一轮是什么
原生tools/tool_calls接口继续沿用已通过的配置；新任务使用Python标准库的实际文件SQLite，不再导入ToolSandbox。两个新任务族为服务路由关联、满足条件后按优先级选择批次。它们仍是研究者构造数据，非公开benchmark/生产事故，也不是已有方法被证明有效。
12个情形×4组=48个主回合；无额外重复。四组分别为generic、minimal、intent、both。所有组可见完全相同的工具、条件写入能力和任务材料，不强迫基线做全字段回写。

## 预算与配置
- 主批次最多384次LLM请求；每回合8次；每响应最多4个可见工具调用；每回合最多32个可见工具调用（包括finish_task）。总计不超过1536次；不需要用满。
- 没有smoke/qualify、额外模型列表、LLM用户模拟器、裁判或格式修复模型。
- 模型请求deepseek-flash；返回deepseek-flash或deepseek-v4-flash仅首份合格响应可建立身份元数据，之后固定其返回标签和指纹；不认证权重。
- max_tokens=16384，thinking enabled，reasoning effort high，tool_choice auto，非流式；没有JSON模式、强制工具或beta strict。
- 本轮新增最多384次，不挪用旧剩余额度。384×16384=6291456是极端输出上界，另有输入，不是预计用量。金额UNKNOWN；服务商侧设置严格金额上限。

## 运行：只用Python 3.11或更新版本，无需pip安装
解压到全新 `R10_Research_Kit`，不要覆盖R9NT1或任何旧目录。
macOS/Linux：
```bash
python3 r10.py prepare
python3 r10.py status
```
Windows：
```powershell
py -3.11 r10.py prepare
py -3.11 r10.py status
```
也可复用以前装好的Python3.11解释器绝对路径。没有第三方依赖，无需GPU、Docker、Git、LaTeX、ToolSandbox运行材料或新建虚拟环境。这里测试的解释器是Linux Python3.13.5；Windows/macOS尚未实机验证。prepare只做一个稳定的SQLite工具兼容检查，不重复96次离线研究。

仅当新目录尚未运行main：
```bash
python3 r10.py run --confirm-calls 384
```
Windows以 `py -3.11` 替换 `python3`。
密钥只使用本地LLM_API_KEY或隐藏终端输入；不贴进助手聊天、Prompt、命令参数或配置。程序不读取.env或搜索旧目录。

完成或暂停后：
```bash
python3 r10.py audit
python3 r10.py export
```
回传最终 `uploads/R10_feedback_<UTC时间>.zip`，无需写主观原因分析。

## 状态优先
completed：只audit/export，不重新采样。
paused/running/已有partial或孤立日志：不恢复、不删锁、不新建副本重跑；确认原进程不再写入后只尝试audit/export。
HTTP、截断、格式/工具schema、未知工具、身份/usage问题：保存后全批暂停。
数据库NOT_FOUND、ROW_VERSION_CONFLICT或SELECTION_CONFLICT是合法业务反馈；模型可在原8轮内查询、处理和重试。这不是后台网络重试。

## 工具与时间线
所有工具只访问本次临时SQLite文件，无真实账户。六个数据库工具加一个finish_task报告工具。finish_task不读取私有评分、不给安全认证，只保存模型自己的completed/incomplete/uncertain判断并结束；普通文字结束另标unstructured，不从正文提取动作。
同一响应先校验全部工具和参数，然后顺序执行；finish_task只能在末尾。工具批次不是原子事务，也没有根据批次中间回执重新推理的机会。
每个情形最多一次更新，发生在第一条合格读取完成后、下一工具执行前。模型跳过读取则更新可能不触发；这些回合保留。版本及选择令牌是所有组可用的真实API参数，不含正确答案。行条件不替代外部选择条件。

## 回传与局限
原始response字节、请求、工具回执、前后状态、事件、代码和协议都保留。常见凭据模式触发时导出拒绝；这不等于全面隐私审计。
机械audit通过只表示记录可重建，不代表论文结论成立。12个配对构造情形不是48个独立真实样本。少量模板上的成功不证明泛化；未复现误写时不调提示诱导或扩大同模板直到显著。
本轮没有RepairLens新增证据。详细预先分析规则见docs/ANALYSIS_LOCK_ZH.md，文献与非新颖性边界见docs/SOURCES_AND_NOVELTY.md。
