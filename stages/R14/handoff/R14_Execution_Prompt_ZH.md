你现在只负责下载公开研究数据并回传，不运行任何LLM实验。

工程目录：用户给出的 R14_Public_Data_Download_Kit。

1. 阅读README_ZH.md。确认Python>=3.9；不安装依赖、不下载模型、不调用LLM/裁判、不读取任何模型API Key。
2. 若目录中已有R14_public_data或uploads/R14_public_data_*.zip，不再次启动，直接告诉用户已有ZIP的位置。
3. 全新目录时执行一次：
   macOS/Linux: python3 download_public.py --download
   Windows: py -3 download_public.py --download
4. 脚本固定下载SAP/agent-quality-inspect的提交593e686f4d0c2e9fcae5ae664c16a7687907cf97，范围为六模型目录、expert/nonexpert、trial0–7，以及摘要和数据卡。不得改为main，不得只留下成功样例，不得改写原JSON。
5. 无论COMPLETE还是INCOMPLETE，都回传uploads/R14_public_data_<时间>.zip。失败后不得删除目录、改脚本、自动重试、关闭TLS校验或更换镜像；研究端会查看保留的诊断。
6. 不需要执行tests、额外audit或撰写主观成功报告。只告诉用户完成状态、ZIP路径、已取得文件数。不得称下载完成为研究实验完成。

整个流程只有公开文件GET。此前R10、R12、R13都不要重跑，旧结果不修改。本任务也不涉及GitHub推送。
