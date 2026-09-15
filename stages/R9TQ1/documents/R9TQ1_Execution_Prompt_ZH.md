# 给本地代码助手：只运行一次R9TQ1原生工具调用资格测试

你是执行者，不是实验设计者。使用用户提供的`R9TQ1_Research_Kit`新目录。
本轮最多12次模型请求，没有额外smoke，没有R9/R9J1的360次实验。
不要增加测试、调整提示、查询/models、SDK探针、换参数、换模型、重采样或执行旧目录。

1. 阅读新目录README_ZH.md、protocol.json和config.json，确认：
   - R9TQ1_NATIVE_TOOL_QUALIFICATION_01 / r9tq-1.0.0；
   - 请求deepseek-flash（本次明确的新请求标签，不是让你自行选择）；
   - 2+5+5=12次总上限，tools原生交互，没有response_format；
   - 程序名r9tq.py，不是r9.py。
2. 只定位用户指定目录和已知的Python3.11解释器。不要搜索密钥、.env或私人文件。
   已装好R9J1依赖的虚拟环境可以用解释器绝对路径复用，不改变旧工程。
   缺环境时按README创建新3.11环境并安装requirements；不要强改依赖以迁就3.13。
3. 运行status或只读查看本目录状态与锁。已经completed/ completed_not_qualified只导出。
   paused/running/孤立账本/锁不恢复、不删锁、不新建另一个副本试跑。
4. 从未执行时：运行prepare（离线机械检查），成功后只运行一次：
   <python3.11解释器> r9tq.py qualify --confirm-calls 12
   API Key只由用户本地LLM_API_KEY环境变量或隐藏终端输入提供；
   不让用户把密钥贴进任何助手聊天，不把密钥写进命令/配置/报告。
5. 中间出现格式、身份、网络、工具结构错误即保留并停止；不得从content挑JSON动作。
   若程序返回任务不合格，不去修改答案、state、源码、manifest或参考结果。
6. 完成或暂停后：运行audit和export。audit不通过也尝试export。
   若锁存在导致export拒绝，确认进程是否仍在写入；不得删锁，记录错误交用户回传。
7. 给用户最终uploads/R9TQ1_feedback_*.zip的实际路径。无需另写肯定性科研报告。
   不宣称“零错误/已可发表/权重一致”；准确区分completed和qualification_pass。
8. 不进行任何新一轮模型请求，不自动启动正式R9任务或提交论文。

允许的命令仅限必要环境准备及本包status/prepare/qualify/audit/export。
本轮所有真实写操作都只发生在ToolSandbox的模拟数据库，禁止连接真实个人账户。
