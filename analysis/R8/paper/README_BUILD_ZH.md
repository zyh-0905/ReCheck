# 编译说明与范围
这是R8机制诊断研究稿，不是可以直接提交的定稿。
使用pdflatex连续编译main.tex两次；图为可缩放PDF。
源样式spconf.sty为此前转录文件，非当年官方原包字节认证。
当前4页包含参考文献、AI使用披露；作者和单位待人工补齐。
旧ReCheck算法稿未覆盖。新的120条是原生脚本；84次为冻结动作的离线检查，
不是新的LLM回合。原R7C1三组14/14保持不变。
不要将TOCTOU或条件写入当作首创；已列出最接近的原始文献。

    pdflatex -interaction=nonstopmode -halt-on-error main.tex
    pdflatex -interaction=nonstopmode -halt-on-error main.tex
