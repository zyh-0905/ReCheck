# ReCheck R16 — 完整研究工作稿与证据

先读 `author_handoff/COMPLETION_REPORT_ZH.md`。工作稿是 `paper/main.pdf`，正文源码 `paper/main.tex`。实际作者原创稿骨架另见 `paper/author_manuscript.tex`。

**工作稿不是直接上传的合规终稿。**作者核查完成按本次用户确认记录；作者身份信息和作者原创最终正文仍待提供。本包不发起任何付费模型请求，也不进行投稿或GitHub写入。

## 快速查看
- `paper/tables/`、`paper/figures/`：两张论文表及矢量图。
- `analysis/paper_results/`：论文统计数值；按模型/人设分层不是因果比较或排名。
- `analysis/reproduced_r15/`：本次从原始公开JSON复算的576条结果。
- `author_handoff/CLAIM_EVIDENCE_MAP_ZH.md`：逐主张数据来源及不能扩大的边界。
- `sources/SOURCE_REGISTER_ZH.md`：直接近邻、会议规则、模板来源。
- `verification/`：本次测试、编译、原始数据摘要、输出比较。
- `evidence_archives/`：R12、R13、R14、R15原档；其中两种原评测分数不能混合。

## 离线复现（不是新的用户任务）
1. 用现有TeX安装，在 `paper` 执行 `python build.py`；不需网络或密钥。
2. 在本包根目录运行 `python -m unittest discover -s analysis -p "test_*.py" -v`，检查论文描述统计函数。
3. `python analysis/paper_tables.py` 从保存CSV重新生成 `analysis/paper_results`（只写派生表，不改原始语料）。
4. 全量数值复算：把 `evidence_archives/R15_Public_Effect_Audit.zip` 展开到一个新目录，在其中 `R15_Effect_Coverage` 执行 `python reproduce.py --out <另一个尚不存在的目录>`。它读取包内原始public_source.zip；不调用模型、裁判或ToolSandbox原生服务。和 `analysis/reproduced_r15` 比较13个输出。
5. R12/R13原生控制需各自原档中声明的Python3.11及ToolSandbox依赖；本轮未重新运行它们，不为查看论文要求安装这些依赖。

本次没有把新分层统计算成新模型样本。原报告、开发失败、源分数与排除案例保留。外部语料及上游工具的许可证在原档内，未将它们改标为本项目原创。
