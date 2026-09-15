# R14真实回退候选：低电量恢复与定位目标冲突

## 定位
数据版本：`593e686f4d0c2e9fcae5ae664c16a7687907cf97`。
源路径：`toolsandbox/gpt_5/expert/trial_3_results.json`。
sample数组下标31（从0计）；sample_id=`turn_on_location_low_battery_mode`。
复合标识：`gpt_5/expert/3/turn_on_location_low_battery_mode`。
同样的原始sample独立存入 `results/regression_candidate_raw_sample.json`，不改内容。

## 原始链路（不是研究者注入）
1. 用户：`Please turn on the location service.`
2. 模型调用 `set_location_service_status(on=true)`，实际回执为低电量模式限制错误。
3. 模型询问用户是否关闭低电量、开启定位，并主动提出之后可以把低电量再开启。
4. 用户：`Please go ahead and turn off Low Battery Mode, enable Location Services, and then you can turn Low Battery Mode back on afterward.`
5. `call_6xp9rzmuAoeny3qGy1pDJOeO`：关闭低电量。记录的SETTING为low_battery=false、location=false。
6. `call_jpd9ZSbvunQVXWQPxGHw1g8v`：开启定位。记录为low_battery=false、location=true。
7. `call_pip7eLyArqxwP7jdpC7ph77a`：重新开启低电量。记录为low_battery=true、location=false。
8. 模型列出“低电量已关、定位已开、低电量已重新开启”的完成说明。

第5–7项均为各自单独的模型调用批次，不存在同批次工具回执顺序歧义。

## 原评分
`progress_rates=[0.0,0.75]`，`auc_score=0.6964285714285715`，`ppt_score=0.375`。
四个原子目标中三个记为完成，未完成的是查询当前定位状态。我们不调用裁判、不改这些评分。
**它不是一个原TED满分案例，更不存在这里已验证的ToolSandbox原始similarity=1。**

## 判定
- 已确认的记录事实：定位确实false→true→false，且最后关闭。
- 必须纳入的用户信息：用户明确允许最后恢复低电量。
- 工具能力：原ToolSandbox设置实现开启低电量会关闭定位、Wi-Fi、蜂窝。记录与该机制一致。
- 因此，不能将其无条件归入“用户目标不变时，模型擅自撤销已经完成的目标”。
- 初始持续目标与后来用户许可操作存在冲突。用户是否认为两者可同时保持、是否授权放弃持续定位，需要独立语义审阅；当前归为 **USER_AUTHORIZED_DEPENDENT_EFFECT / CONFLICTING_GOAL_SCOPE**。
- 模型应解释两者不可同时维持，这可以作为后续行为研究的具体案例；但本轮不估计其发生率、不宣布已有评测错误、不据此启动新采样。

## 为什么不从0.75改成0或1
原TED评价的子目标混有工具调用与历史完成条件，本地定位终态谓词只覆盖一项必要效果。两者目标不同；发现它们不同不是自动获得“修正后的真实总分”。保留原分数与额外观测是当前有据可依的处理。
