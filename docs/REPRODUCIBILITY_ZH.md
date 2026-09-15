# 查看、校验和复现

以下区分材料校验与研究重算。本次整合只执行了归档/暂存工具检查，没有重跑科研实验。

## 1. 默认：只读归档校验

在根目录，Python 3.11及以上：

```bash
python tools/verify_archive.py
```

检查文件集合、长度与SHA-256，不联网、不读取密钥。输出建议保存到仓库之外。原始文件有字节变化会失败，不能为让检查通过而重写历史哈希。

## 2. 公开数据离线重算（可选，不是当前上传任务）

R14/R15的reproduce.py只使用标准库，读取已包含的原始JSON，要求输出目录不存在：

```bash
python analysis/R14/reproduce.py --out ../recheck_r14_reproduction_new
python analysis/R15/reproduce.py --out ../recheck_r15_reproduction_new
```

复制原输出不算重算。包内已有分析锁与原始字节摘要；用户语义解释仍须由研究者理解，不因脚本通过而自动成为完整金标准。

## 3. 论文

建议将`papers/R16/latex/`复制到仓库外的新目录，在副本中运行：

```bash
python build.py
```

需要本地TeX环境。脚本不调用模型；本次整理只保留此前编译产物，没有再次宣称本轮重新编译PDF。主稿是AI辅助研究工作稿，作者信息和后续最终文本不得由归档工具编造。

## 4. R12/R13原生工具重现

它们需要兼容的Python 3.11科学环境、NumPy/Polars/SciPy等，细节见各工程README。依赖安装分发未收入本仓库；R7材料的版本/来源/校验记录保留。不要因为目录有launch.py就盲目安装或运行整套云角色堆栈。

## 5. 历史付费模型命令

`experiments/`的run/smoke/qualify及旧执行Prompt仅为历史协议。当前没有新的调用授权。不得为了上传仓库再运行模型、删除暂停锁、换种子、覆盖runs或重新采样失败者。
