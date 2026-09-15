# 正文主张—证据定位

| 正文对象 | 原始证据入口 | 允许结论 / 边界 |
|---|---|---|
| 摘要及表1：576、349、72、64 | R15 results/reproduced/all_episodes.csv、by_task.csv；本轮analysis/paper_results | 6个重复任务模板的记录，不是576独立任务；64只计源满进展且审阅后保留 |
| 62日历错误、2未创建 | R15 REVIEW_ANNOTATIONS.json、independent_check.json、64条confirmed_cases.csv | 数值/无提交检查，不是新模型响应或修复收益 |
| 64/212=30.2% | 三类reminder记录的source_full合计212 | 子集描述比例，不是全基准误判率；不做独立episode的显著性检验 |
| 图1六个模型目录 | 本轮by_model.csv，由同一576行提取其中288行提醒 | 43/48/42/19/40/20原满进展；1/18/20/0/17/8保留冲突；非实时模型评估或重新排名 |
| 两类人设 | 本轮by_persona.csv | expert=26/116、nonexpert=38/96；描述，非人设因果效应 |
| 14/81与50/268 | 原开发/后续trial拆分及本轮by_split.csv | 后续不是未见任务或真正独立盲测；审阅发生在自动筛查后 |
| 周六误作周五 | R15 cases/weekday_mismatch_source_record.json及evidence.json | 使用实际时钟和转换回执，用户未改期；状态实际写入，不只是完成语句 |
| 两年前误作明天 | R15 cases/past_date_for_tomorrow_* | 过去epoch不可能通过时区解释成明天 |
| 8条排除 | R15 results/review_annotations.csv | 4合法改期、2时区、2仅时刻；不把后四条认定为正确 |
| 阴性覆盖802/802 | R14结果及报告；10个模板960条，945已知 | 所查局部效果，无全任务/全安全认证 |
| 8个公开任务回退反例 | R12原生45条轨迹/原分数，R12 Public Task Results | 研究者脚本，不是自然模型失效率 |
| 表2顺序修改 | R13原生5条轨迹/temporal results | 一个公共任务，区分按阶段目标与仅终态；非自动意图识别 |
| 作者核查完成 | 本轮用户明确陈述 | 记录报告状态；不编造人数、κ、外部机构或每条签名；原R15旧审计说明不覆盖 |

新稿不沿用早期“调度算法胜出”叙事，不混入RepairLens结果，也不把R15日期错误归因于R12的历史匹配机制。
