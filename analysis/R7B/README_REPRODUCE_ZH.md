# R7B审计材料：仅供复核，不要求用户再次执行

此包没有真实LLM运行器，没有新的用户付费任务。

## 内容
- R7B_Review_Report_ZH.md：材料、原生安装和机制结论。
- study/：原生桥接与独立评分；tests为本次新增测试。
- upstream/：固定ToolSandbox源码ZIP，内含原许可与ACKNOWLEDGEMENTS。
- results_run1/与results_run2/：两次原生执行；不是独立新增样本。
- logs/：安装、测试、失败定位与校验。
- original_material_contract.py：原下载器副本，供读取固定版本和摘要，不要求运行其下载命令。

## 仅复核已保存结果（系统Python，无新依赖）

```
python study/audit_saved_results.py results_run1 saved_audit.json
```

该命令只读结果并重新检查快照、任务目标、调用账本与同情形的输入公平性。

## 原生重建所需环境

依赖来自用户已经回传的R7材料，不重复包含在此ZIP。运行时为Linux x86_64 CPython3.11.14；53个分发版本与摘要见logs/materials_verification.json。无需模型、RapidAPI或账号。

1. 在新目录检查材料ZIP清单的每个SHA256，使用原下载器的verify_source_zip核对固定tree，运行时核对固定SHA256。
2. 将已验证的Linux运行时解压；仅从materials/packages安装，先setuptools70.3.0和wheel0.43.0，再安装53个固定分发文件，命令使用`--no-index --find-links ... --no-build-isolation`。rouge-score在本机由已验证sdist构建。
3. 将upstream源码ZIP解压到新source目录。不改源码，不升级依赖，不运行上游CLI全场景。
4. 使用下述研究脚本。R7_SOURCE为包含tool_sandbox目录的固定源码根；这不是模型密钥。

```
R7_SOURCE=/absolute/path/ToolSandbox-c8571d7854316d2e1c5f288e59fe1e34e53f6dd1 \
POLARS_MAX_THREADS=1 OPENBLAS_NUM_THREADS=1 TZ=UTC \
/path/to/python3.11 -I study/launch.py test

R7_SOURCE=/absolute/path/ToolSandbox-c8571d7854316d2e1c5f288e59fe1e34e53f6dd1 \
POLARS_MAX_THREADS=1 OPENBLAS_NUM_THREADS=1 TZ=UTC \
/path/to/python3.11 -I study/launch.py study NEW_OUTPUT
```

launch.py禁用Python标准库网络连接；只执行固定白名单工具；不是操作系统级安全沙箱。不要给研究进程提供API Key。所有消息只是模拟数据库行。

新增33项测试内有对原执行器两个已知失败的定位测试；它们不使原上游失败变成通过。60个核心上游测试通过；另6个原上游执行器测试4通过2失败，详见报告。

UUID、机器时间和计时不要求在两次执行间相同；scientific_projection.json只对明确的任务、操作、结果、计数和公共输入字段比较。不修改原始消息或历史快照。
