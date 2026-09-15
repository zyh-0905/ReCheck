# Primary sources rechecked on 2026-09-13
1. Jiarui Lu et al. ToolSandbox. arXiv:2408.04682. https://arxiv.org/abs/2408.04682
   Executed native source commit: c8571d7854316d2e1c5f288e59fe1e34e53f6dd1.
2. Xingkun Yin and Hongyang Du. GLOVE. arXiv:2601.19249. https://arxiv.org/abs/2601.19249
   Active feedback-based memory realignment is prior work. Not implemented as a baseline here.
3. Mayur Akewar and Ravi Ranjan. SafeCommit. arXiv:2608.04289v1.
   https://arxiv.org/html/2608.04289v1
   Conditional commitment with candidate worlds and targeted probes is prior work.
4. Derek Lilienthal and Sanghyun Hong. Mind the Gap: Time-of-Check to Time-of-Use
   Vulnerabilities in LLM-Enabled Agents. arXiv:2508.17155v1.
   https://arxiv.org/html/2508.17155v1
   Prior paper studies 66 AgentDojo-derived tasks and prompt/monitor/tool-fusion defenses.
   Our native extension is NOT a replication of their benchmark or implementation.
   Discovering a check/use gap and fusing tools are NOT claimed novel.
5. R. Fielding, M. Nottingham and J. Reschke. HTTP Semantics. RFC 9110, 2022.
   https://www.rfc-editor.org/rfc/rfc9110.html
   Sections 13.1.1 and 13.2: If-Match and precondition evaluation.
   A generic ETag on one resource does not automatically cover another resource's
   semantic binding or a multi-resource transaction. Our guards have explicit scopes.
6. ICASSP 2027 Author Guidelines:
   https://2027.ieeeicassp.org/author-guidelines/
   Technical content no more than four pages; optional fifth page only references;
   AI-generated contributions disclosed. No submission or PDF eXpress run here.

Formatting provenance: paper/spconf.sty is the preserved previously transcribed
layout stylesheet (see its header). It is not asserted byte-identical to the 2027
upstream package. A fresh direct download failed due to container DNS; no stylesheet
was silently replaced. PDF inspection checks actual geometry and page count.
