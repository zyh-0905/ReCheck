# R14：一次性取得公开真实轨迹（只下载，不做模型实验）

## 你只需运行一条命令

macOS / Linux：

```bash
python3 download_public.py --download
```

Windows：

```powershell
py -3 download_public.py --download
```

需要 Python 3.9 及以上，仅用标准库。不安装依赖、不需要 GPU、不需要 API Key，不访问模型推理接口，不运行 LLM 裁判或用户模拟器。

完成后，把脚本打印的 `uploads/R14_public_data_<时间>.zip` 传回。**即使显示 INCOMPLETE，也传现有ZIP，不需要写说明报告、不修改脚本、不切换数据版本。** 若输出目录已经存在，脚本不会再次下载或覆盖；回传已有ZIP即可。

## 固定下载范围

来源：`SAP/agent-quality-inspect`，固定提交：

```text
593e686f4d0c2e9fcae5ae664c16a7687907cf97
```

六个公开目录：gpt_4_1、gpt_4o、gpt_4o_mini、gpt_5、mistral_large_2411、mistral_nemo。
每目录的 expert 与 nonexpert，trial_0 到 trial_7：计划96个**既有实验JSON文件**。另取12份aggregate_metrics_results.json和数据卡README，共109个固定源路径。

上述数字是预先定义的采集范围，不是已下载文件数、成功实验数或独立任务数；实际文件数与原始sample数以回传清单为准。所有组均按同一规则采集，不因分数高低选择文件。

只执行公开HTTPS GET；没有额外smoke、模型列表、生成请求或账号授权。109是源文件获取尝试的最多数量，HTTP重定向可能增加传输请求数，**不产生模型调用费用**。每个源文件只尝试一次，首次下载/格式异常后停止并导出已取得材料。使用操作系统TLS验证，不关闭证书检查。

每文件上限32 MiB、总数据上限512 MiB；下载耗时取决于网络。仅下载JSON/Markdown，不下载或执行pickle，不执行下载内容。现有代理设置可由Python的标准网络库使用；脚本本身不读取、索要或保存模型密钥。

## 数据与研究分开

原JSON字节原样保存，不清洗、不改写status或metrics，不生成或筛选实验结果。
SHA-256用于核对回传前后字节一致，不是服务商签名。固定版本URL与可用响应版本头保留；原始模型权重身份并未被本脚本认证。

研究端收到数据后直接完成结构检查、目标有效期分类和跨模型分析。你不需要再单独运行审核器或提交“材料接收反馈”。这次因研究容器下载失败需要一次传输协助；离线分析仍由研究端完成。

## 软件验证边界

本脚本经过16项本地测试，含完整109文件的模拟采集与打包、无覆盖、失败后部分导出、错误JSON、版本错误及篡改拒绝。测试下载内容是明确的合成软件夹具，不是真实实验数据。实际公网下载尚未成功在研究容器完成。验证日志在verification目录。

## 原始来源

数据：https://huggingface.co/datasets/SAP/agent-quality-inspect
固定版本：https://huggingface.co/datasets/SAP/agent-quality-inspect/tree/593e686f4d0c2e9fcae5ae664c16a7687907cf97
数据集声明许可证：Apache-2.0，以下载的数据卡为准。

请注意：这是TED改编的ToolSandbox轨迹。不能将它的status、progress_rates或AUC解释成原版ToolSandbox的milestone similarity。
