# 给本地代码助手的R7公开材料下载Prompt

你只负责一次**公开材料下载与回传**。研究助手负责实验执行；本任务不是把离线研究再次交给用户，也不是LLM实验。

## 目标
在本文件所在的R7_Materials_Request目录，运行已提供的collect_materials.py，把固定ToolSandbox源码、Linux x86_64 CPython3.11运行时与固定版本依赖文件下载并打包。用户即使使用macOS/Windows，也必须下载Linux x86_64文件，因为它们将用于研究助手的容器。不得按当前电脑修改目标平台。

## 允许步骤
1. 阅读README_ZH.md和collect_materials.py；确认当前目录包含这两个文件。
2. 使用用户已有Python3.10+运行：
   - macOS/Linux：`python3 collect_materials.py --allow-public-downloads`
   - Windows：`python collect_materials.py --allow-public-downloads`
3. 只下载脚本指定的公开HTTPS地址；不读取任何API Key、账号密码或用户旧研究目录。
4. 返回脚本输出的`uploads/R7_materials_<UTC时间>.zip`路径，请用户上传完整ZIP到原研究对话。

## 禁止事项
- 不运行LLM/API测试，不调用任何付费端点或用户模拟器。
- 不运行pip install、不创建或安装新环境、不执行下载的Linux Python、wheel或上游代码。
- 不clone其他仓库、不更换上游commit、不更换包版本、不关闭哈希/tree校验。
- 不执行R1—R6，不改任何已有实验数据。
- 不自行删除R7_materials_work、反复重试到下载成功或修改脚本绕过错误。
- 不推测原生实验已通过、包已安装、论文可发表或用户操作原因。
- 不把API Key、Cookie、Authorization、环境变量或用户账号信息添加进说明文件。

## 失败处理
脚本下载失败时会尽量生成INCOMPLETE_DOWNLOAD诊断ZIP。回传这个包；不要安装缺包来“修复”、不要修改原结果。若没有生成ZIP，提供终端错误类别和失败阶段，先隐藏路径中的个人信息或代理凭据。已有R7_materials_work时，不删除目录重新跑，优先交付现有ZIP。

脚本只有公开文件下载，没有研究模型调用费用。可能消耗网络流量，单文件上限150MiB、下载总量上限450MiB，最终文件大小以清单记录为准。

完成后只说明实际状态、成功/失败阶段和ZIP路径。不要写新的研究因果解释报告。
