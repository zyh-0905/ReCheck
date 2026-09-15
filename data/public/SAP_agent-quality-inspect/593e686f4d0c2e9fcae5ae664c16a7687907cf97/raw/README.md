---
license: apache-2.0
language:
- en
---

# TALK, EVALUATE, DIAGNOSE (TED): USER-AWARE AGENT EVALUATION WITH AUTOMATED ERROR ANALYSIS

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/) [![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE) [![REUSE status](https://api.reuse.software/badge/github.com/SAP-samples/agent-quality-inspect)](https://api.reuse.software/info/github.com/SAP-samples/agent-quality-inspect) [![ICLR 2026](https://img.shields.io/badge/ICLR-2026-red.svg)](https://iclr.cc/Conferences/2026)


## Dataset Details

This dataset contains our evaluation logs for running tau2bench and toolsandbox scenarios with different LLMs using expert and non-expert personas based on our paper.

### Dataset Description

<!-- Provide a longer summary of what this dataset is. -->

![Two-step automated error discovery approach. Identical error colors indicate
that similar low-level errors are clustered into the same high-level category.](https://cdn-uploads.huggingface.co/production/uploads/668642835a5cdc0bae08a983/rauXgw2cVfXRqFgasXTBe.png)

The dataset is separated into folders based on the agent benchmark code (e.g Tau2Bench, ToolSandbox) evaluated using our metric package https://github.com/SAP/agent-quality-inspect.
Inside each agent framework folder contains the subfolders of the scenario, the LLM used, followed by expert and non-expert personas. Inside those folders contains
pkl files with the evaluation logs, error analysis and json files of the individual trial results.
Our evaluation logs can be used as input to be reviewed in our Error Diagnosis UI for the purpose of in-depth debugging and analysis.

- **Language(s) (NLP):** English
- **License:** apache-2.0

### Dataset Sources

<!-- Provide the basic links for the dataset. -->

- **Repository:** [Agent Quality Inspect](https://github.com/SAP/agent-quality-inspect)
- **Paper:** [Open Review Paper](https://openreview.net/pdf?id=fHsVNklKOc)

## Uses

<!-- Address questions around how the dataset is intended to be used. -->
The dataset is meant to show the results we have obtained from running our evaluation with the paper experiments and to facilitate the debugging of the evaluation logs.
For a detailed step by step on how to use the dataset with our project refer to [Our repository](https://github.com/SAP/agent-quality-inspect?tab=readme-ov-file#error-diagnosis-ui)

## Dataset Structure

<!-- This section provides a description of the dataset fields, and additional information about the dataset structure such as criteria used to create the splits, relationships between data points, etc. -->
```
<agent_benchmark_code>/
├── <domain>/
│   ├── <llm_agent_model>/
│   │   ├── <user_persona_type>/
│   │   │   └── ... (test data)
│   │   ├── <user_persona_type>/
│   │   │   └── ...
│   │   └── .../
│   ├── <llm_agent_model>/
│   │   ├── <user_persona_type>/
│   │   └── .../
│   └── .../
├── <domain>/
│   ├── <llm_agent_model>/
│   │   ├── <user_persona_type>/
│   │   └── .../
│   └── .../
└── .../
```
    
**An example folder path is:** ```<agentbenchmarkcode>/<domain>/<LLMagentmodel>/<userpersonatype>```

This folder path is used as an input argument for --output-dir as described in [our repository](https://github.com/SAP/agent-quality-inspect?tab=readme-ov-file#error-diagnosis-ui)

### Source Data

Our evaluation logs are based on the evaluation of adapted test samples from Tau2Bench and ToolSandbox [Dataset](https://github.com/SAP/agent-quality-inspect/tree/main/paper_experiments/datasets) 
 
<!-- This section describes the source data (e.g. news text and headlines, social media posts, translated sentences, ...). -->

## Citation

**BibTeX:**

```
@inproceedings{
  chong2026talk,
  title={Talk, Evaluate, Diagnose: User-aware Agent Evaluation with Automated Error Analysis},
  author={Penny Chong and Harshavardhan Abichandani and Jiyuan Shen and Atin Ghosh and Min Pyae Moe and Yifan Mai and Daniel Dahlmeier},
  booktitle={The Fourteenth International Conference on Learning Representations},
  year={2026},
  url={https://openreview.net/forum?id=fHsVNklKOc}
}
```

**APA:**

Chong, P., Abichandani, H., Ghosh, A., Moe, M. P., Mai, Y., & Dahlmeier, D. Talk, Evaluate, Diagnose: User-aware Agent Evaluation with Automated Error Analysis. In The Fourteenth International Conference on Learning Representations.

## Dataset Card Contact

[Penny Chong](mailto:penny.chong@sap.com)
