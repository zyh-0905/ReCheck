# ReCheck — 研究、实验与审核档案

目标仓库：`zyh-0905/ReCheck`。本地归档截至R11；原始方向是隐藏工具语义漂移下的证据刷新，
后续收敛为状态化Agent的提案、前提与执行结果诊断。**当前稿不是已录用或投稿就绪版本。**

## 从这里开始

- 最新论文：[R11 PDF](papers/R11/ReCheck_Evidence_Synthesis_R11.pdf) ｜ [LaTeX](papers/R11/latex/main.tex)。
- 原研究方案：[01_ReCheck_research_plan.md](plans/01_ReCheck_research_plan.md)。
- 全过程：[研究时间线](RESEARCH_TIMELINE_ZH.md) ｜ [原始文件索引](ARCHIVE_INDEX_ZH.md)。
- 原初始算法工程：`shared_history/initial_release/engine_snapshot/src/recheck/`。
- 各轮原版运行代码：`experiments/`；各轮报告、更正与CSV：`stages/`。
- 原始用户回传：`feedback/`；R7C1、R9NT1、R10及初期pilot附有可直接查看的raw副本。
- R8与R11研究端分析：`analysis/`；其他完整离线证据/审核包在各轮`archives/`中。

## 当前研究结论（摘要，不代替各轮原协议）

R7C1静态诊断中三组各14/14；R9NT1动态续行中两组各14/16；R10四组各12/12。
这些任务、模型接口和工具能力不同，不能拼成一条方法提升曲线。R11的280个局部分支是
70个已记录提案的离线条件子集分析，不是新的LLM样本，也不是替代策略的完整成功率。
额外提示未建立稳定正确性增益；完整条件请求的正常拒绝不能自动算作模型错误。
已通过的是各阶段限定的执行审核，不是ICASSP录用门槛。

特别注意：`experiments/R7C_original_14_case/`与`experiments/R7C/`保留两次同名但不同
规模的历史发布。R7C1才是后续独立修订版本。不得混用源码、反馈或预算。

## 阅读与证据边界

这是研究过程档案，而非最终论文发布。历史报告可能有已更正的错误：应同时阅读同轮
`Review_Report` 与 `Factual_Corrections`；原稿/原始响应不因后来的审核而覆盖。
脚本模拟、接口资格、真实模型回合、离线局部分支和跨机器复现必须分开，不相加为独立样本。
文件名中的“满分”属于提交者的历史命名，不是本次归档授予的质量认证。

归档没有新模型调用，没有重新运行研究实验，没有向服务方提交数据，也没有修改远端仓库。
初始源码和古老运行说明保留是为了复现；它们不构成新的付费调用授权。
科研新颖性、作者原创写作、AI使用政策、贡献、单位与投稿信息仍需实际作者确认。

## 校验本地副本

从仓库根目录执行（Python标准库，不联网、不运行研究）：

```bash
python tools/verify_archive.py
```

只核查归档文件集合、长度和SHA-256。`ARCHIVE_MANIFEST.json`本身的摘要由交付验证记录
另存；原包内已有的清单保持不变。此检查不认证模型权重、账单、论文正确性或全面隐私安全。

## 文件组织

`ARCHIVE_INDEX_ZH.md`为原始附件到归档位置的对照；
`provenance/SOURCE_ARTIFACTS.json`给出原文件摘要；
`ARCHIVE_MANIFEST.json`为本仓库每个实际文件给出路径、长度、摘要与来源。
`shared_history`中的共同工程保留了原始两项目目录和相对导入依赖，不能将另一项目的结果
算成本项目证据。它们是共享历史快照，不是两份独立实验。

## 当前发布状态

本次GitHub连接对目标仓库返回`push: false`，实际创建文件的调用返回HTTP 403。
`PUBLISH_STATUS.json`记录本次发布失败，不表示文件已经在线。无新增远端提交。
授权修复后应先重新读取远端分支，保留已有内容，以普通提交发布，不能强制覆盖历史。
