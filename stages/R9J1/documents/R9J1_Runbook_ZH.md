# R9J1：状态变化后自主续行的JSON输出修订

**本包是R9的输出契约修订，不是新任务/新算法。**协议 `R9J1_LIVE_CONTINUATION_DIAGNOSIS_01`，版本 `r9-1.0.1`。
旧R9在第一个主请求输出多对象和说明文字后暂停，未形成研究回合。旧目录保持原样；不覆盖、不删锁、不重写原始响应。
唯一推理设置变化为所有请求启用 `response_format={"type":"json_object"}`。32主回合+4重复、每回合10次请求、所有任务提示和评分不变。详见 `docs/AMENDMENT_ZH.md`。

## 你负责的范围
仅真实模型阶段。研究端已完成离线测试与重放，不要求再次运行全套测试/规则实验。需要Python 3.11.x，已安装R9依赖的解释器可以通过绝对路径复用。
本包不需要真实联系人、短信、RapidAPI或评分模型。工具只操作原生ToolSandbox模拟数据库。

## 先检查状态，避免重复花费
1. 在全新 `R9J1_Research_Kit` 中执行，程序仍叫 `r9.py`，内部目录仍为 `runs/R9_smoke` / `runs/R9_main`，但根目录不同。
2. 新根目录main已经completed：只audit/export。
3. 新smoke完成而main从未开始：不重跑smoke，只run。
4. main或smoke暂停、running、孤立账本或锁：确认没有进程继续写入后仅导出，不删除锁，不开新副本重采样。

## 环境
复用现有解释器时，例如先进入新根目录，再以旧R9虚拟环境的绝对路径运行这个新目录的 `r9.py`。不要将旧runs/PREPARED复制到新目录。
需要新建环境时：

macOS/Linux：
```bash
python3.11 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python r9.py prepare
```
Windows PowerShell：
```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe r9.py prepare
```
准备不调用模型。安装可能访问公开包索引，不启用模型账户或附加下载服务。

## 实际模型运行
密钥只用本地 `LLM_API_KEY` 或终端隐藏输入。不得贴进助手聊天、Prompt、命令参数、配置文件或ZIP，不读.env或搜索旧目录的密钥。

首次只运行一次：
```bash
.venv/bin/python r9.py smoke --confirm-calls 1
```
只有本目录smoke为completed且json_ok/shape_ok通过才运行：
```bash
.venv/bin/python r9.py run --confirm-calls 360
```
Windows替换解释器路径。提前done结束，不补齐上限。

本轮新增上限361次；加旧R9记录的2次，沿革累计最多363次。输出上限16384保持不变。次数上限不是金额上限；费用UNKNOWN，严格金额限制依赖服务商侧设置。
新smoke不保证复杂任务始终输出正确JSON。再遇HTTP/截断/非法JSON/usage/身份异常时保留后暂停，不自行修复格式或重复请求。

## 结束或暂停后回传
```bash
.venv/bin/python r9.py audit
.venv/bin/python r9.py export
```
即使audit非零也保留证据导出。只上传最后生成的：
```text
uploads/R9J1_feedback_<UTC时间>.zip
```
不需要另写结果解释。不删除原始失败，不换seed，不混合主/重复结果，不从两次回答选最好者。

## 研究边界
R9J1是启用JSON模式的新推理配置。与旧R9不能归为完全相同设置；旧格式失败单独列入沿革，不能用新成功覆盖。
四种评分（tool_success_proxy、goal_final、final_state_clean、trace_safe_success）及事件暴露都按原版记录；终止另列。未完成回合不自动变成0分或满分。
全部是一个原生模拟后端、四个构造模板、单端点开发诊断，非官方榜单、自然事故发生率或可发表性保证。没有RepairLens新增调用。
