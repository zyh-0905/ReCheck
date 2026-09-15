# R15公开效果核查

本包是已完成的研究端离线分析，**不是用户运行任务，不需要反馈“收到”，不需要API Key，不会调用模型**。

先读docs/REPORT_ZH.md、docs/CASEBOOK_ZH.md，再查看results/reproduced/by_task.csv及confirmed_cases.csv。

包含R14原始公共数据ZIP、冻结谓词代码、开发/后续输出、72条候选的审阅标签以及64条数值/无提交证据复核。所有既有来源分数不变。`effect_final`仅为初始规格局部谓词，不是完整任务真值；请同时阅读review_class和排除理由。

研究者需要复核时：

```bash
python -m unittest discover -s tests -v
python reproduce.py --out /tmp/r15_new_output
```

仅Python标准库。输出目录必须不存在。数据在临时目录解压，Python socket层禁止联网（不是OS级沙箱）。绘图另需matplotlib，但不属于结果复算的依赖。

ANALYSIS_LOCK.json记录第一次应用到trial2–7之前的主解析/谓词代码。独立检查和事后语义审阅在其后添加，不能宣称它们都是提前预注册。开发v1严格字符串误差已保留，不作为正式结果。

原始来源代码与数据按各自许可证保留；本包不重新授权第三方数据。不存在新训练权重、付费执行器或论文投稿动作。
