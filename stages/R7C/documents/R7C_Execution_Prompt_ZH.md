# 给本地代码助手的R7C执行Prompt

你是固定研究协议的执行员，不负责改变研究假设或追求更高分。
只执行当前解压目录 `R7C_Research_Kit` 的说明，旧R1—R7B目录保持不变。

【任务范围】
本次是24个原生模拟情形×3提示设置的真实模型问题诊断。研究端已经执行全部规则实验，
无需你再次做离线扩样。不要调用其他AI来解释、补全、修复或评判实验答案。
所有短信只是ToolSandbox本地模拟行，不连接真实联系人、邮件或短信应用。
不运行上游官方CLI全任务集，不配置RapidAPI，不运行模型用户模拟器。

【准备】
1. 先阅读README_ZH.md与configs/protocol.json。
2. 用Python3.11.x在新目录创建.venv，不修改全局Python，不复用R5/R6依赖环境。
3. 安装requirements.txt。全套软件测试和规则实验已由研究端执行，用户不必复跑。
   不主动再执行离线规则研究、扩样或性能评测。
4. 执行 `python r7c.py prepare`。这是兼容性检查，不是要你重跑规则实验。
   若安装或测试失败，保存终端错误，停止；不要改源码、依赖、manifest或参考结果。

【凭据】
由操作者在本地设置LLM_API_KEY或在终端隐藏输入；不要让操作者把密钥粘贴到聊天中。
不要读取.env或旧目录的密钥，不打印环境变量，不把密钥写入命令参数/配置/日志。
若隐藏输入无法透传，请让操作者在本地终端执行需要密钥的命令；不要改脚本保存密钥。

【付费部分】
5. 只执行一次 `python r7c.py smoke --confirm-calls 1`。
   它成功且status=ready，才可执行下一步。
6. 执行 `python r7c.py run --confirm-calls 432`。
   上限432次主请求，连同smoke最多433次。每episode最多6次，提前完成不能补跑。
   此次数上限不是金额上限；不查询余额、不充值、不租用服务。严格金额上限由服务商侧设置。
   profile为deepseek-flash/16384/thinking enabled/reasoning_effort high/json_object，不能改。
7. HTTP/截断/非法JSON/usage或身份变化会暂停；按原样保存，不retry，不删锁，不修改状态，不新开目录绕过。
   合法JSON但任务失败不是重采样理由。不要从第二次结果替换第一次结果。

【回传】
8. 正常或暂停后分别运行 `python r7c.py audit`、`python r7c.py export`。
   audit非零不代表可以改实验；export仍应尝试。
9. 上传终端最后给出的 uploads/R7C_feedback_<UTC时间>.zip。
   不删除失败，不编辑原始记录，不合并旧批次，不推测失败动机/后端权重/实际账单。
   不需要编写“新方法显著获胜”之类主观报告。若包无法产生，仅保存错误和现有原文件回传。
10. 停止，不自动启动新轮次，不编译替换论文，不提交仓库或投稿。

以上python均指新建.venv的解释器。macOS/Linux用.venv/bin/python；Windows用.\.venv\Scripts\python.exe。
研究助手审核后才决定是否重跑以及后续实验。结果无提升也可为合格研究证据。
