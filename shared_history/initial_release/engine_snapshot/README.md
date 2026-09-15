# ReCheck / RepairLens：实际执行的受控研究与 ICASSP 论文初稿

日期：2026-09-12。版本：controlled-study-0.1。

**这里有真实代码、真实执行记录、可重建图表和两篇英文 LaTeX/PDF，不是只包含计划的工程骨架。当前证据是受控有限模型研究，不是已完成的 LLM 论文验证，也不宜直接投稿。**

## 先读什么

- `papers/recheck/main.pdf`：4 页初稿。
- `papers/repairlens/main.pdf`：4 页技术正文 + 第 5 页参考文献。
- `docs/STATUS_AND_REVIEW_ZH.md`：逐项完成情况、研究价值与阻断项。
- `docs/EXECUTED_RESULTS.md`：从原始 CSV 自动生成的结果。
- `docs/TECHNICAL_NOTES.md`：数学与实验边界、数据划分、成本和统计说明。
- `results/final_audit.json`：版式、字体、源码冻结检查。
- `results/reproduction_audit.json`：同环境完整确定性复跑检查；不是独立审稿或新样本。

## 已经执行的内容

ReCheck：9,216 个主实验轨迹运行，737,280 个任务—方法求值；另有 384 个边界轨迹和 128 个 SQLite 轨迹（5,120 次真正的 SQL 任务—方法求值）。主实验统计单位是 64 个独立基础种子簇，不是 737,280 个独立样本。

RepairLens：120 个独立受控工作流，每个 11 种方法，共 1,320 次真实 NumPy/文件执行；另有 60 个实例的成对支持缺失压力测试，共 120 次运行。每种方法从同一个失败前缀开始。实验只用三个输出块；不是自然 LLM 失败。

未调用 LLM/API、未使用 GPU、未运行 AppWorld/MemoryArena/Harbor 官方任务、未获得独立人工审查。当前已知模型、精确探测、有限假设等条件不能推广成开放世界保证。

## 环境

原运行环境为 Linux、Python 3.13.5；精确包版本见 `requirements-lock.txt`。代码声明 Python >=3.10，但锁定版本的完整组合只验证于上述环境。审查 PDF 需要系统命令 `pdffonts`（Poppler）；编译需 `pdflatex`，并安装 Times/PSNFSS、amsmath、amssymb、graphicx、booktabs、url 等常见 TeX 包。字体已经嵌入 PDF，不附带字体文件。

```bash
python -m venv .venv
# Linux/macOS:
source .venv/bin/activate
# Windows PowerShell 可使用 .venv\Scripts\Activate.ps1
python -m pip install -r requirements-lock.txt
python -m pytest -q
```

安装依赖需要网络；本交付不自动连接付费模型、不读取个人账号、不提交论文。

## 重建图表与论文：不重跑实验

```bash
python scripts/make_report.py
# Linux/macOS/WSL，有 pdflatex 和 pdffonts 时：
bash scripts/build_papers.sh
```

`make_report.py` 从交付的首轮测量 CSV 生成统计、图表、论文数值宏和表格。`build_papers.sh` 复制图表、两遍编译并检查 PDF。Windows 原生可在每个 `papers/...` 目录运行 `pdflatex -interaction=nonstopmode -halt-on-error main.tex` 两次，再回到根目录运行 `python scripts/audit.py`。

单篇 LaTeX 包只需 `main.tex`、`spconf.sty`、`results.tex`、表格和 `figures/`；参考文献内置在 `main.tex`，无需 BibTeX。正文中的报告时延来自首轮测量，完整验证会保留它们，而不是覆盖成第二轮时延。

## 从头验证所有科学结果：不覆盖原记录

```bash
python scripts/verify_reproduction.py
```

程序会在临时目录重新校准基线、运行 ReCheck、SQL、边界、RepairLens 与支持缺失测试，并比较所有科学列和轨迹。机器性能不同，完整复跑可能需要数分钟或更久；不要使用过短的命令超时。只有实际计时时间允许变化，原始首轮结果不会被覆盖。验证通过后写出 `results/reproduction_audit.json`。

本次执行器的单次墙钟限制曾中止两次整批复跑，因此最终验证使用 `scripts/verify_incremental.py` 分批完成。该脚本可接续同一核验检查点，不把重复核验计为额外实验。归档不包含仅用于续跑的进度缓存；通常使用上面的完整验证命令即可。

## 修改或扩展实验

核心控制器分别位于 `src/recheck/core.py`、`src/repairlens/core.py`，环境位于相邻文件。实验主程序提供完整生成逻辑。修改前请复制整个工作目录到新的实验版本，**不要覆盖此版本冻结的结果**。新实验必须同步更新数据清单、分析协议、相关论文数字和审查结论。

当前无外部 LLM 评测适配器。接入模型需新增真实调用、token/时延计费、候选覆盖评测、完整工具隔离及独立外部任务；不能直接把现有受控数字填入 LLM 模型表。

## 主要发现与限制

- ReCheck 的“加权错误 + 指定检查价格”目标相对 myopic 下降约 19.7%，相对调参 TTL 下降约 11.1%。它不是所有准确率指标的第一名；漂移模型低估时也可能比每次刷新差。
- RepairLens 两步规划的指定操作成本比全重启下降约 23.4%，精确参考下降约 24.5%。**本地总时延反而更高**：两步约 1.84 ms、精确约 27.24 ms、全重启约 0.59 ms。不能声称实际加速或美元节约。
- RepairLens 主实验的完整恢复依赖真实行为在候选族中；故意去除真实损坏模式后，恢复率降至 38.3%。

## ICASSP 格式与模板来源

按 ICASSP 2027 官方作者页面的保守要求排版：技术内容最多 4 页，第 5 页仅参考文献；加入 AI 使用披露；未填写虚构作者。`spconf.sty` 根据官网全文转录，执行定义来自官方文件，但注释简化，**不是已下载的逐字节官方压缩包**。来源与本地 SHA-256 见 `upstream/provenance.json`。正式提交前应重新下载当年官方包核对，并补充真实作者、单位、ORCID 和人工审查。

机械版式通过并不代表创新性、完整性或会议主题契合度已经达到录用标准。两份原方案更广的研究要求见 `original_plans/`，未完成部分全部列在审查文档中。
