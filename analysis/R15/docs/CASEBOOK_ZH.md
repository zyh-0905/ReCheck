# R15案例簿：六条可直接定位的正反证据

所有原始记录都保存在`cases/*_source_record.json`，精简证据保存在同名`*_evidence.json`。完整原始文件可从`inputs/public_source.zip`对应路径取得。来源progress不更改，不运行新的裁判。

| 编号 | 原始记录 | 保存的事实 | 可用结论 |
|---|---|---|---|
| A | gpt_4o/expert/trial2，下周五提醒 | 时钟2025-09-16星期二；转换并写入9月20日星期六；progress=1 | 请求日历与实际写入不一致；不是达成后回退 |
| B | gpt_4o/expert/trial2，明天提醒 | 当前epoch1758017671.957964；写入1697446800（2023年）；progress=1 | 实际时间早于当前，时区不能让它成为明天 |
| C | mistral_large_2411/nonexpert/trial1，明天提醒 | 原生添加提案有回执，但SyntaxError在函数执行前发生；无新增行；progress=1 | 提案和实际提交不能混同；执行器也参与失败 |
| D | mistral_large_2411/nonexpert/trial3，指定日期提醒 | 正文有add_reminder JSON；无原生添加调用；无新增行；progress=1 | 工具样式文本不能替代原生调用 |
| E | gpt_5/expert/trial3，指定日期提醒 | 用户明确从2024改为2026；实际创建2026提醒；progress=1 | 旧目标硬检查会误判；已排除，不用于增加错误数 |
| F | gpt_4_1/expert/trial0，下周五提醒 | 实际时钟9月16日；转换9月19日17点并写入；progress=1 | 正常控制，日历检查接受其已见局部结果 |

## A的最小证据链

- `call_b8gyUASd6muvy8aW7DyzMDjY`：get_current_timestamp → 1758017684.319934。
- `call_jhWwyIEI0V3OagUvwH11M7wO`：timestamp_to_datetime_info → 2025-09-16 18:14:44、isoweekday=2。
- `call_2LBymYvEuQM9mhgT4O1a0BHN`：datetime_info_to_timestamp参数为2025-09-20 17:00 → 1758358800。
- `call_tV3bztvePh3M9f2E06enwmhD`：add_reminder用1758358800 → reminder_id=7fc9a002-e98b-4443-b169-c6d3b22717d1。
- 最后REMINDER表包含该ID与1758358800；原progress最后为1。

“next Friday”允许最近周五或下一个周五都不能将星期六变为星期五。上述日期星期由独立日历计算复核，不使用裁判解释作为真值。

## 人类作者核对项

核对A/B中用户是否另行改期；C是否应归为执行桥错误而非模型推理错误；D中是否确实没有结构化添加调用；E是否明确更新有效请求。一般礼貌感谢不应自动被当成修改原日期，但该规则应由作者对源对话作实质审阅。

本案例簿不是独立人工标注，不声称源论文的全局指标或排名已被推翻。
