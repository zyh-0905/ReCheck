# 反馈 11：R7 公开运行材料下载与回传

| 项 | 内容 |
|---|---|
| 任务性质 | **一次公开材料下载与打包**（不是 LLM 实验、不是离线研究复跑） |
| 执行时间（原始 UTC） | **START 2026-09-13T06:17:55Z → END 2026-09-13T06:19:52Z** |
| 脚本 | `collect_materials.py`（`r7-materials-1.0`），源哈希已核对一致 |
| 使用的 Python | 本机系统 `python3` **3.9.6**（满足脚本「3.10+」要求） |
| **最终状态** | **`MATERIALS_COLLECTED_NOT_INSTALLED`** |
| **退出码** | **0**（一次成功，未重试） |
| **新增 LLM / API 调用** | **0**（`new_llm_calls: 0`） |
| 是否安装包 / 执行下载代码 | **否 / 否**（`packages_installed: false`、`downloaded_code_executed: false`） |
| 下载总量 | **137,757,799 字节 ≈ 131.4 MiB**（上限 450 MiB） |
| 产物数 | 55 个 artifact（1 source + 1 runtime + 53 packages） |

## 1. 实际执行的命令与退出码

| 命令 | 退出码 |
|---|---|
| `python3 collect_materials.py --allow-public-downloads` | **0** |

只执行一次，未反复重试、未修改脚本、未删除 `R7_materials_work`、未关闭哈希/tree 校验、未 `pip install`、未创建环境、未执行下载的 Linux 程序。执行前后未触碰 R1—R6 任何目录与数据。

## 2. 输出包路径

```
/Users/user/代码/DeepSeek harness/REcheck/实验反馈/反馈11_R7公开材料下载_20260913/原始记录/R7_materials_20260913T061951846901Z.zip
```

**大小 131 MiB（137,860,116 字节）**，包内 112 个条目：

| 顶层 | 数量 |
|---|---|
| `source/` | 1（ToolSandbox 源码 ZIP） |
| `runtime/` | 1（Linux x86_64 CPython 运行时） |
| `packages/` | 53（依赖分发文件） |
| `metadata/` | 53（各版本 PyPI JSON 元数据） |
| 根文件 | `COLLECTION_REPORT.json`、`DOWNLOAD_REPORT.json`、`collector_used.py`、`BUNDLE_MANIFEST.json` |

## 3. 核验结果（我独立复核，全部通过）

| 核验项 | 结果 |
|---|---|
| `BUNDLE_MANIFEST.json`（sha256-file-index-v1，111 条目） | **失配 0**（逐文件 SHA-256 与字节数均一致） |
| 源码 Git tree 重建 | **`64ccd1694a91f2029844434d5995a2c0945cd6b2`** —— 与固定值**完全一致** |
| 源码内容 | 77 文件、218,989 字节、ZIP SHA-256 `99a78061…` |
| 源码提交 | `c8571d7854316d2e1c5f288e59fe1e34e53f6dd1` |
| Linux CPython 运行时 | 31,210,076 字节，SHA-256 `e5696efed11346d8c53ec89587bbd3e4bce79cabdd67a62e7af60af62f01159c` —— **与固定值一致** |
| 目标平台 | `Linux x86_64 CPython 3.11; NOT the host operating system`（**未按本机 macOS arm64 改目标**） |
| 53 个依赖 wheel 平台标签 | **无非 Linux/通用产物**（抽检 `polars`、`numpy`、`scipy`、`pydantic_core` 均为 `manylinux_2_17_x86_64.manylinux2014_x86_64`） |
| 源码分发（sdist） | **仅 `rouge_score-0.1.2.tar.gz`** —— 与脚本 `ALLOW_SDIST` 白名单**完全一致**（未在本机构建） |
| 单文件 / 总量上限 | 未超（150 MiB / 450 MiB） |

## 4. 使用到的公开主机（脚本内置白名单，未扩大）

`github.com`、`codeload.github.com`、`release-assets.githubusercontent.com`、`objects.githubusercontent.com`、`pypi.org`、`files.pythonhosted.org` —— 全部 HTTPS，重定向仍校验主机，未传账号或鉴权头，未关闭证书校验。**未读取任何 API Key、Cookie、Authorization、环境变量或旧研究目录。**

## 5. 需要明确区分的边界（不越界表述）

- **材料下载成功 ≠ 原生实验成功。** 本轮只是把公开文件搬到可上传的 ZIP。
- `native_status` 报告原文：**`NOT_RUN; CPU local tool/evaluation dependency subset, not full provider role stack`**。
- **未安装任何包、未执行任何下载的 Linux 程序/wheel/上游代码**；依赖摘要与官方元数据随包回传，但**不声称所有依赖都已在本机实际联网下载后原生验证成功**。
- 后续的安装、原生工具测试、规则基线与统计**由研究助手在容器内完成**，不需要用户复跑离线实验。
- 未推测原生实验已通过、包已安装、论文可发表，也未推测用户操作原因。

## 6. 失败处理

**无失败。** 未生成 `INCOMPLETE_DOWNLOAD` 诊断包（该分支未触发），`DOWNLOAD_REPORT.json` 中 `failure` 字段缺失即表示无失败。终端错误需回显处也没有出现（脚本对 HTTP/URL 错误采用 `safe_error()` 脱敏，不回显代理串或查询参数）。

## 7. 隐私

包内**不含** API Key、Cookie、Authorization 头、环境变量或账号信息。包内 `collector_used.py` 是**被请求内容的证据**，不是被执行过的依赖。

## 文件

| 文件 | 说明 |
|---|---|
| `原始记录/R7_materials_20260913T061951846901Z.zip` | **回传用**。131 MiB，含公开源码、Linux 运行时、53 个依赖分发文件与元数据、脚本、摘要清单 |
| `审核/DOWNLOAD_REPORT.json` | 下载报告：状态、目标平台、55 个 artifact 的 URL/字节/SHA-256 |
| `审核/COLLECTION_REPORT.json` | 采集报告（与下载报告一致的内容副本） |
| `审核/BUNDLE_MANIFEST.json` | 包内 111 文件的 SHA-256 与字节索引 |
| `审核/collector_used.py` | 实际使用的脚本（源哈希与 `SOURCE_MANIFEST.json` 一致） |
| `审核/collect完整输出.txt` | 完整终端输出（含起止 UTC 与 53 个包逐条进度） |
