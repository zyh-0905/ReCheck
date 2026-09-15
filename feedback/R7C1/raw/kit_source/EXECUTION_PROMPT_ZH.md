# 本地执行助手Prompt：R7C1标签门槛修订后的固定任务

你只运行固定实验，不改代码、模型、任务、提示、参数或评分，不写因果/先进性结论。

1. 使用全新R7C1_Research_Kit目录，读取README_ZH.md和protocol.json。原R7C_Research_Kit及其paused记录保持原样。不得删除锁或将旧smoke状态改为completed。
2. 使用Python3.11.x和requirements.txt固定依赖。可直接使用已经安装好这些依赖的旧虚拟环境**解释器**，但执行的是新目录的r7c.py，不操作旧研究目录。若新建环境，仅安装依赖，不再运行研究端的全部离线测试。
3. 本修订请求model仍是deepseek-v4-flash。允许新smoke返回deepseek-v4-flash或deepseek-flash；随后将其返回标签与指纹固定为本批记录。不要推断两个标签相同权重，不做全局字符串替换。
4. 密钥只用用户已经配置的LLM_API_KEY，或让用户在脚本终端隐藏输入。不要在对话、命令参数或文件写密钥，不读.env，不搜索其他工程凭据。
5. 顺序运行：
   - `<python> r7c.py prepare`
   - 一次`<python> r7c.py smoke --confirm-calls 1`
   - **只有smoke completed且shape_ok/json_ok=true**，才运行一次`<python> r7c.py run --confirm-calls 384`。
   - 若smoke暂停，直接执行第6步，禁止再运行主命令来验证它会不会被拒绝。
6. 正常完成或暂停均执行`<python> r7c.py audit`，然后`<python> r7c.py export`，交付最后的uploads/R7C1_feedback_*.zip。审核退出非零时也应尝试导出，不删证据来修通过。
7. 新版新增最多385次生成请求尝试；旧版已记录1次，修订沿革最多386次，比原上限多一次smoke。不是金额保证、不强制发满；只有这些确认命令获准发请求。
8. **禁止任何额外端点探测**：无论在smoke之前或之后，都不运行curl、GET /models、GET余额、SDK测试、聊天测试或另一个smoke。不启动官方CLI、用户模拟器、RapidAPI，不真实发短信或连接个人联系人。
9. 不并行、不重试到成功、不改上限/seed/模型/端点/指纹。每个回合8次上限和全部失败保留；重复回合不能替换主结果。
10. 结尾只报告：实际运行到哪一步、文件路径、记录的请求数量、原始错误。不存在的探针/账单/任务结果写未知，不猜别名映射必然性、权重、操作者原因或统计结论。

研究端已经完成代码核查、已存响应的离线回归和模拟接口验证；本任务不要求你重跑它们。所有模型费用由用户侧实际发生，凭据不得发给研究助手。
