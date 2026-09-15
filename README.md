# ReCheck — research archive through R16

**ReCheck: Auditing Full-Progress Scores Against Executed Effects in LLM Agents**

本仓库整理本项目从原始研究方案、实验推进、用户反馈、审核更正，到R16英文论文工作稿的完整文件沿革。目标仓库为 `zyh-0905/ReCheck`。当前是**研究资料归档**，不是已录用论文或已通过会议提交检查的声明。

## 快速入口

| 要找的内容 | 文件入口 |
|---|---|
| 最新完整英文论文 | [R16 PDF](papers/R16/ReCheck_ICASSP_Research_Draft_R16.pdf) |
| 可编辑论文源码 | [main.tex](papers/R16/latex/main.tex)、[LaTeX ZIP](papers/R16/ReCheck_ICASSP_LaTeX_R16.zip) |
| 作者定稿入口与核查记录 | [作者稿骨架](papers/R16/latex/author_manuscript.tex)、[作者核查记录](papers/R16/latex/author_handoff/AUTHOR_REVIEW_RECORD.json) |
| 原始研究方案 | [研究计划](plans/01_ReCheck_research_plan.md) |
| 实验全过程 | [时间线](RESEARCH_TIMELINE_ZH.md)、[流程与版本](docs/RESEARCH_WORKFLOW_ZH.md) |
| 当前结论与不能声称的结论 | [结果与边界](docs/RESULTS_AND_LIMITATIONS_ZH.md) |
| 主实证与逐例证据 | [R15报告](stages/R15/reports/R15_Research_Report_ZH.md)、[64条记录](stages/R15/results/R15_Confirmed_Conflicts.csv)、[案例簿](stages/R15/reports/R15_Key_Cases_ZH.md) |
| 第三方公开原始JSON | [固定版本数据](data/public/SAP_agent-quality-inspect/593e686f4d0c2e9fcae5ae664c16a7687907cf97/raw/README.md)、[数据字典](docs/DATA_DICTIONARY_ZH.md) |
| 各轮用户原始反馈 | [feedback/](feedback/)、[源附件索引](ARCHIVE_INDEX_ZH.md) |
| 只读完整性检查与研究复现 | [复现说明](docs/REPRODUCIBILITY_ZH.md) |
| 上传本仓库 | [上传说明](UPLOAD_GUIDE_ZH.md)、[本地助手Prompt](GITHUB_UPLOAD_PROMPT_ZH.md) |

## 研究结论摘要

- **主实证：**R15补查6类任务的576条既有公开记录，保守保留64条来源满进展但效果不符的记录：62条日期错误、2条未真正创建提醒。三类提醒中212条满进展记录的64条发生冲突；这仅是该固定子集的描述，不是全基准错误率。
- **阴性对照：**R14另检查10类静态目标共960条；945条局部效果可判定，其中802条来源满进展记录的所查终态条件均成立。
- **原生时序控制：**R12/R13共50条脚本轨迹区分历史达成、终态保持与合法用户修订；它们不是自然模型失败样本。
- **历史路线：**R1—R11保存原证据刷新、真实工具接口、条件写入及反事实分析；后续转向评测诊断不覆盖历史阴性结果，也不证明早期算法优越。

当前论文是回顾性经验诊断工作稿。没有将TED进展分数冒充ToolSandbox官方相似度，没有重排公开榜单，也没有证明新算法提升Agent任务成功率。用户已在对话中确认作者核查完成；该声明及未提供的审阅人数、签名等边界保存在R16作者记录中。署名占位和工作稿标记原样保留。

## 目录

```text
plans/           原始研究方案
experiments/     历史模型实验运行器与冻结配置
feedback/        用户原始回传、原始请求响应及接收资料
stages/          各阶段报告、结果表、更正、验证和原始交付ZIP
analysis/        R8/R11及R12—R16的可阅读离线分析工程
papers/          初稿、R8、R11、R16 PDF和LaTeX
data/public/    已取得的SAP公开JSON、数据卡、采集清单
shared_history/  两项目共同早期原包；不挪用RepairLens成绩
history/         同名不同版本、旧导航与原清单
provenance/      来源、摘要、完整性与敏感模式检查记录
docs/            流程、数据口径、结果边界、复现说明
tools/           只读归档校验与显式本地Git暂存工具
tests/           归档工具测试（不是科研样本）
```

原ZIP与展开副本可能包含相同数据，这是可阅读与可复现的便利副本，不增加样本数。源文件索引与逐文件摘要分别见 `ARCHIVE_INDEX_ZH.md` 和 `ARCHIVE_MANIFEST.json`。

## 默认不运行实验

```bash
python tools/verify_archive.py
```

此命令只读本地文件，不联网、不调用模型、不读取密钥。历史运行包中的 `run/smoke/qualify` 命令**不构成新的调用授权**。复现应使用新输出目录，不覆盖冻结结果。

## 许可和公开范围

原始第三方许可证、SAP数据卡、上游源码声明均保留，见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。本归档不擅自为全部代码、论文或模型输出授予统一的新许可证。公开模型轨迹含合成任务联系人、号码、时间和路径等原始字段；凭据模式扫描不等同全面隐私认证。

本归档没有独立字体文件，没有重新分发R7运行时/依赖安装包。完整对话未导出：研究过程通过原始报告、协议、反馈、日志和版本沿革保存，时间线不是逐字聊天记录。

本次只完成本地整理。`PUBLISH_STATUS.json`记录已观察到的远端状态；未生成远端提交。
