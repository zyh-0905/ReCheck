# 给本地执行助手：R7C付费模型诊断任务

你只负责按冻结文件执行、回传，不设计实验、不调参数、不写因果结论。

1. 确认工作目录是新解压的R7C_Research_Kit，包含r7c.py、SOURCE_MANIFEST.json、protocol.json。
   不触碰R1—R7B。读取README_ZH.md，检查已有Python3.11；不能将下载的Linux运行时用于Mac/Windows。
2. 使用独立.venv，安装requirements.txt；运行r7c.py prepare。
   这些只是机械环境准备，不需要重跑研究端已经完成的离线实验/完整测试。
   若解释器或依赖不兼容，保留报错，停止；不修改源码或版本以强行通过。
3. 只使用用户已配置的LLM_API_KEY；缺少时让用户在终端隐藏输入。
   禁止在聊天、命令参数、日志或配置中粘贴密钥；禁止读.env或搜索旧项目中的凭据。
4. 执行一次 `python r7c.py smoke --confirm-calls 1`（python用.venv中的解释器）。
   使用当前包固定的deepseek-v4-flash，不替换为旧deepseek-flash或其他模型。
   smoke没有completed/合法结果，则直接audit/export回传；不再curl、探测或重复smoke。
5. smoke完成后执行一次 `python r7c.py run --confirm-calls 384`。
   这是384主run＋1smoke的尝试上限，不是要强制发满385次。
   本轮42主episode＋6重复episode，每episode最多8轮。没有用户模拟器或额外LLM评测器。
   不并行多个进程、不自动重试、不删除锁、不切换seed或提高上限。
6. 正常完成或暂停均运行 `python r7c.py audit`，然后 `python r7c.py export`。
   将最后的uploads/R7C_feedback_*.zip交给用户回传，不只给截图或平均分。
7. 不重写已有参考结果，不把重复中的正确答案代替主结果。
   若失败，不猜用户操作原因、后端版本或费用；只附实际终端错误。
8. 不启动官方ToolSandbox CLI、不调用RapidAPI，不发送真实短信或连接个人联系人。
   原生工具只操作包内模拟状态。不要在本地助手中把private gold或case变更标签送给模型。
9. 不创建外部仓库、付费账号、购买服务器或提交论文。
10. 完成后停止。最终只报告执行到哪一步、产生哪个ZIP、是否有错误；不宣布方法先进或满足录用条件。
