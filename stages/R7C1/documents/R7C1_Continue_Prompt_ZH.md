# R7C1续行Prompt：先检查状态，不重复调用

## 唯一允许的实验版本
你是本地执行助手，只负责运行与导出，不负责修改研究假设或结果。
当前唯一允许的包：Research_Handoff_R7C1.zip。
协议必须为 R7C1_NATIVE_AGENT_DIAGNOSIS_01，version 为 r7c-1.0.1。
ZIP SHA-256：60e5e182c6f256b320cf7a2a19ce2b5c50ef690510e90765765a8e507d44fe84。
14个情形、42主回合、6重复回合，每回合最多8次请求；主批次最多384，新smoke最多1。
这份说明不改变原实验协议、源码、状态或预算，不是R8或新的实验版本。

## 先检查已有状态
1. 使用用户指定的R7C1_Research_Kit目录。只读查看 protocol.json、PREPARED.json（若存在）、.run.lock，以及 runs/R7C_smoke/status.json 和 runs/R7C_main/status.json（若存在）。不要搜索其他目录的密钥。
2. 如果用户尚未解压本版本，才解压到新的R7C1目录。若已有R7C1运行目录，不再新建第二份目录绕过停止限制。旧R7C_Research_Kit及其paused状态保持原样。
3. R7C1主批次已completed：不运行prepare、smoke、run；只运行audit和export并交付ZIP。
4. 任一R7C1运行是paused，或有未收尾的running/锁：不增加模型请求，不删除锁。若进程仍实际写入，先等待本次前台运行正常停止，或由用户决定停止；确认不再写入后只运行audit和export。不要从status=running单独断定进程还活着，不自动kill。
5. smoke已completed、主批次从未开始：不重跑smoke；按原运行器验证，通过后仅启动一次主批次。
6. 只有两批次都未开始且没有遗留请求时，才准备环境并执行一次smoke。PREPARED已存在时不得改绑定；如不确定状态，停止并回传，不猜测“应当重置”。

## 环境与命令
使用Python3.11.x与本包requirements.txt。可以复用已经安装好依赖的旧虚拟环境的**解释器绝对路径**，但当前工作目录及所执行r7c.py必须来自新R7C1根目录；不操作旧研究目录。
新建环境时按README_ZH.md安装。无需重跑完整离线研究、无需运行整套测试。
以下 <python> 指实际Python3.11解释器，不要直接将尖括号文本当命令运行。

仅未准备、未开始的目录：
    <python> r7c.py prepare
仅从未执行smoke的目录：
    <python> r7c.py smoke --confirm-calls 1
仅本目录smoke completed且shape_ok/json_ok=true、主批次从未开始时：
    <python> r7c.py run --confirm-calls 384
正常完成或暂停、并且没有并行写入时：
    <python> r7c.py audit
    <python> r7c.py export

如audit退出非零，仍单独尝试export；不能用&&导致审核非零后跳过证据导出。
最终交付 uploads/R7C1_feedback_<UTC时间>.zip。

## 不得改变的边界
- 请求model仍为deepseek-v4-flash；不替换为其他名称。新smoke允许的返回名只有原协议两个标签；批次内必须保持新smoke的返回标签和指纹，不推断已认证真实权重。
- 新版本新增上限385；加已归档旧smoke1次，修订沿革累计上限386。已有R7C1调用消耗本次额度，换目录不会重置授权。
- 上限不是目标，不补足请求数，不重采样失败，不自动重试。费用UNKNOWN，不猜当前价格。
- 禁止额外GET /models、余额检查、curl模型探针、SDK聊天测试；不启动上游CLI、用户模拟器或RapidAPI。
- 密钥仅从已有LLM_API_KEY环境变量或用户在脚本终端隐藏输入获取；不贴聊天、命令参数、报告或配置，不读.env，不搜索旧工程凭据。
- 不修改任务、提示、seed、轮数、源码、参考hash、停止条件和评分。
- 不将重复回合替换主回合，不删除失败，不能重新运行以获取更好结果。
- 工具只作用于包内模拟数据，不接私人联系人、短信或提醒服务。

结尾只给出实际状态、执行到哪一步、导出路径、账本内请求数与原始错误。无需写“成功原因”“模型权重相同”“方法显著更好”等推断。
