# 参考文献与投稿规则核查
访问日期：2026-09-15。本次使用Exa检索、原作者论文页面与官方会议网站。这里只对列出的具体事实负责，不声称穷尽所有文献。

| 标识 | 一级来源 | 核对内容 |
|---|---|---|
| toolsandbox | https://aclanthology.org/2025.findings-naacl.65/ | 12名作者、NAACL Findings 2025、1160–1183、DOI；不是ICASSP论文 |
| ted | https://arxiv.org/abs/2603.15483v1 、https://arxiv.org/html/2603.15483v1 | 作者名单及ICLR 2026接收说明；第4节改编37个基础场景；A.1承认缺失可见状态的限制；不把我们的审计称为其原始榜单重评 |
| judge | https://arxiv.org/abs/2306.05685 | 题名、作者、NeurIPS 2023 Datasets and Benchmarks；一般LLM裁判相关工作 |
| validity | https://arxiv.org/pdf/2607.02577v1 、https://arxiv.org/html/2607.02577v1 | 直接近邻已提出调用/完成/结果分离与确定性优先验证。PDF首页作者顺序为Jay Vaghasiya、Vishvesh Bhat、Muhammad Ahmed Mohsin、Asad Aali；摘要页顺序不同，本稿遵从实际PDF首页。该文是预印本，不写成已获顶会录用 |
| aba | https://arxiv.org/abs/2605.26079v2 | 自动化基准审计、作者名单与预印本版本；未复现其方法或主张超过它 |
| timebench | https://aclanthology.org/2024.acl-long.66/ | ACL 2024、1204–1228、7名作者、DOI；日历推理困难不是本稿首创 |
| sapdata | 既有R15包内 docs/SOURCE_DATA_CARD.md 与输入清单；https://huggingface.co/datasets/SAP/agent-quality-inspect | 固定版本593e686f4d0c2e9fcae5ae664c16a7687907cf97；数据卡Apache-2.0；数据年份作为该公开发布记录标签，不认证模型服务或时钟 |

## 模板与规则
- 官方Paper Kit：https://cmsworkshops.com/ICASSP2027/papers/paper_kit.php
- 官方提交说明及LLM使用政策：https://cmsworkshops.com/ICASSP2027/papers.php
- 审稿规则：https://2027.ieeeicassp.org/about/editorial-policies/
- 当届样式链接：https://cmsworkshops.com/ICASSP2027/papers/PaperFormat/spconf.sty

容器HTTP下载仍发生DNS错误，download工具亦失败。本包使用此前保留的spconf转录文件，并将实际定义与当届官方网页文本重新核对：178mm×229mm正文、6mm栏距、-6.2mm侧偏移、双栏、空页码、默认10pt及标题/节标题格式一致。它不是官方原文件逐字节下载副本，注释已在该文件中明确说明。没有调整正文宽高来强行压页。

参考文献以显式编号的references.tex编译，不需要BibTeX可执行文件；references.bib提供编辑用元数据，键与正文一致。没有伪称已下载IEEEbib.bst。下划线、长哈希和URL已处理换行。

官方规定最多4页技术内容及可选第5页规定内容，摘要约100–150词、最多5个关键词、实名作者、有效ORCID，无页码。官方对AI生成重要正文的限制仍然适用；本次完整英文文本为工作稿，不是合规提交认证。
