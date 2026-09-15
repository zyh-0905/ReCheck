# 交给本地代码助手的R4执行Prompt

你是本轮实验的执行者，不是研究设计者。研究端已冻结R4_BUNDLE_BUDGET_01。请使用我指定的、全新解压的R4_Research_Kit文件夹，只执行下面任务。原LLM_Pilot_Kit、R1、R2、R3目录不得修改、删除、续跑或覆盖。

## 任务与授权
本轮仅运行R4：最多1次smoke、408次主批次请求，共409次请求尝试。主批次为384个primary＋24个repeat，不选更好答案。RepairLens没有新增模型调用。调用次数授权不是无限费用授权；有账户金额上限时尊重它，不充值或采购。不要自行curl、另写API探测、调用额外模型或运行别的实验。

## 操作步骤
1. 定位新R4_Research_Kit，确认r4.py、SOURCE_MANIFEST.json、configs/r4_protocol.json存在；读取README_ZH.md。只在新目录工作。
2. 用Python3.11+创建.venv，安装requirements.txt。执行 `python -m unittest discover -s tests -v`（使用该虚拟环境的Python，下同）。本机回环fixture是软件测试，不计为真实模型结果；给本地测试足够的命令执行时限，不能因工具超时改测试。
3. 执行 `python r4.py prepare`。失败就停止后续模型操作并导出现有证据；不能更改参数、seed、源码或测试来让门槛通过。
4. API Key只能由用户在进程环境LLM_API_KEY或终端隐藏输入提供。不要让用户在你的聊天中贴密钥，不读.env、不把密钥放命令参数、不打印环境变量或密钥。不为处理密钥写持久化明文文件。
5. 执行且只执行 `python r4.py smoke --confirm-calls 1`。确认当前R4 smoke状态completed；如果暂停/错误/截断，立即走步骤7，不自行尝试替代model ID、思考参数、输出上限或协议。
6. 执行 `python r4.py run --confirm-calls 408`。不修改调用内容、顺序或种子；不要读private评测文件来挑题、选响应或帮模型回答。源码和模型返回的推理文本不能作为你擅自改方法的理由。
7. 正常结束或暂停后执行 `python r4.py audit`，然后 `python r4.py export`，再用 `python r4.py verify <最后生成的ZIP路径>`核对。暂停未必有全部记录，照样回传。
8. 将最后生成的 `uploads/R4_feedback_*.zip` 的实际完整路径告诉用户，让用户上传给研究端。不要只给平均分、截图或自写报告。

## 禁止行为
- 不删除锁、不执行unlock/retry、不续跑paused目录、不增加cap、不新建另一实验目录重采样。
- 不把失败修成正确后覆盖原答案；repeat只是诊断，不能best-of-two。
- 不把本地fixture响应、离线规则结果或72组数学期望写成真实LLM成绩。
- 不让所有方法以外的某一个方法获得额外工具、隐藏状态或免费预算。
- 不宣称R4是公开benchmark、方法全球首创、已证明货币节约或已满足论文录用。
- 不猜操作者动机、中断原因、后台模型版本、账单、峰谷和星期。不知道就是unknown。
- 不修改论文、不自动提交，不扩大到RepairLens。

## 反馈只需事实
最终简述：完成/暂停、模型返回名称、脚本报告调用数、是否出现错误、最后ZIP路径。计数以文件为准，不凭印象估算。对科学结果的审核与下一轮决策交给研究端。
