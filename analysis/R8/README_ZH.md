# R8：论文整合与执行时序边界
这是已完成的研究端离线工作包，**不是用户付费实验包，用户无需运行**。

## 文件
- `paper/main.pdf`：4页英文机制诊断稿，旧稿保留不覆盖。
- `paper/main.tex`、`spconf.sty`、`figures/`：可独立编译的源稿。
- `results/native_run1`：120条原生脚本轨迹＋独立的2条持续变化边界。
- `results/native_run2`：第二次复算，同一设计，不增加样本数。
- `results/frozen_action_exposure`：对原42个模型首写动作的84次离线转换。
- `results/paid_r7c1_recheck`：原始169个响应的复核，不是新模型调用。
- `code/`、`tests/`、`docs/`、`logs/`：执行、评分、测试、文献边界与日志。
- `native/`：R7C1原样原生桥接模块与固定ToolSandbox源码，保留上游许可。

## 研究边界
新模型请求为0。原三组14/14不改变。脚本结果、冻结动作干预、原付费轨迹分别记录。
Atomic只表示声明的单线程事件调度不在检查/写入段内插入更新，并未测试实际多线程
或远程服务原子性。Scoped/Global是增加环境能力的参照，不是同权限的新Agent算法。
用户明确号码与动态人物目标不同；评分在实际写入时刻，事后变化不追溯造成错误。
本包不读取密钥、不发真实短信、不操作私人文件，不创建外部仓库或提交论文。

## 复核方式（仅供复现，不要求用户执行）
已有R7C1依赖的Python3.11环境可直接使用；或设置R8_DEPS为此前经校验的wheel模块目录，
R8_ROUGE为rouge_score-0.1.2源码目录，再用python3.11 -S运行。

    python3.11 -m unittest discover -s tests -v
    python3.11 code/run_study.py --out /path/new_output
    python3.11 code/audit_results.py --root results

新输出目录必须不存在；旧数据不覆盖。原始轨迹中的UUID、creation_timestamp和计时
可以变化，比较范围仅为`science.json`明确列出的离散投影，不虚称整个原生快照相同。
安装依赖可能需要网络；实验导入bootstrap后阻止socket连接，不是完整恶意代码沙箱。

冻结动作复核需要原R7C1反馈解包根目录（含kit_source、runs），路径不得是只有摘要的文件夹：

    python3.11 code/frozen_actions.py --feedback /path/extracted_R7C1 --out /path/new_transitions

重新审核付费原始账本：

    python code/audit_feedback.py --feedback /path/original_user_zip --kit /path/Research_Handoff_R7C1.zip --out /path/new_audit

编译：

    cd paper
    pdflatex -interaction=nonstopmode -halt-on-error main.tex
    pdflatex -interaction=nonstopmode -halt-on-error main.tex

spconf是此前保存的转录样式，非本次重新下载并字节认证的官方原文件。
版式检查不能替代实质同行评审、真实作者与单位、官方上传验证。
