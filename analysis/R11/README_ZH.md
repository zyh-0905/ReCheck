# R11：提案、条件与结果的研究证据整合

日期：2026-09-14。**这是已在研究端执行的离线分析与论文源码包，不是新的付费模型运行包。用户无需复跑。**

## 本轮产物

- `paper/main.pdf`、`main.tex`：整合R9NT1、R10和本轮局部重放的4页英文开发稿；作者信息与正式投稿验证未完成。
- `docs/RESEARCH_REPORT_ZH.md`：结果、语义修正和研究决定。
- `docs/CLAIM_EVIDENCE_MATRIX_ZH.md`：支持/不支持的结论。
- `docs/SOURCES_AND_NEXT_GATE_ZH.md`：近邻工作与下一阶段放行条件。
- `results/run2/`：最终源码运行的70份提案及280个分支；每条保存原始前态、参数和后态。
- `scripts/proposal_audit.py`、`tests/`：纯标准库复核程序和37项测试。
- `inputs/`：冻结的R10原包、反馈内层ZIP及既有报告，不改写输入。
- `logs/`、`DELIVERY_VERIFICATION.json`：开发红灯、完成验证与范围说明。

## 关键边界

完整动作是“在前提成立时执行业务修改”。合法条件请求被拒绝，不自动等于模型犯错。本包只删除某些**原本已经提交**的前提来检查局部业务后果，不加入新前提，不修改业务参数，不串接为新的Agent轨迹。

70份提案包括48份首提案与22份由原始冲突反馈引出的后续提案。280次本地转移不是280次模型调用，也不是280个独立任务。原48/48安全成绩不变。R9NT1与R10的任务、提示及工具能力不同，不能把二者分数差归因于单一机制。

## 可复核命令（仅供审阅，不要求用户执行）

需要Python 3.11或更新版本；无pip依赖、无API Key、无smoke。

```bash
python3 -m unittest discover -s tests -v
python3 scripts/proposal_audit.py \
  --feedback inputs/R10_feedback_inner.zip \
  --source inputs/R10_handoff.zip \
  --out results/local_recheck
```

Windows可将`python3`替换为`py -3.11`。输出目录必须尚不存在；程序不会覆盖旧结果。它在临时文件中使用原R10 SQLite工具，阻止Python socket连接，不读取密钥；不声称操作系统级安全隔离。

对照`results/run2/`的六个科学输出。脚本刻意绑定输入摘要，只服务此次固定队列，不是接受任意文件或任意自然语言任务的通用评测器。两次本机运行及最终新解压运行均执行过；机器计时不用于性能结论。

## 论文编译

```bash
cd paper
pdflatex -interaction=nonstopmode -halt-on-error main.tex
pdflatex -interaction=nonstopmode -halt-on-error main.tex
```

使用继承的`spconf.sty`转录版本，保留原说明；未认证与当年官方原包逐字节相同。该稿并非正式投稿成稿，且没有修改早期R8 PDF或原ReCheck方法稿。
