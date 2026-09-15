# 将完整ReCheck资料上传至GitHub

目标：`https://github.com/zyh-0905/ReCheck`。
本次工具读取时该仓库为public、内容为空，当前连接只有读权限；以下步骤应由拥有仓库写入权限的本地Git身份执行。脚本没有密码、token或SSH私钥输入接口。不要把凭据发给助手。

## 1. 解压后上传目录内容，不上传整个外层ZIP

完整下载包解压得到`ReCheck/`。这就是仓库根目录，里面直接有README、papers、data、analysis等，不要把它再包进远端的`ReCheck/ReCheck/`。

GitHub网页上传每文件25 MiB、通常一次最多100个文件；本资料有数千文件，且保留原始R16证据ZIP超过25 MiB。应使用本地Git命令行，不要逐文件拖入网页。

官方文件大小说明（本次核对）：https://docs.github.com/en/repositories/working-with-files/managing-large-files/about-large-files-on-github 。普通Git阻止超过100 MiB的单文件；本包每个实际入库文件均小于50 MiB，无需仅因外层ZIP很大就启用LFS。旧ZIP和公共JSON有同内容便利副本，Git可以按相同blob去重；不要删除原始证据来缩包。

### Windows路径提示

历史文件保留了原始目录层级，最长相对路径约280字符。Windows应使用支持长路径的解压/文件系统环境，并在本地仓库执行`git config core.longpaths true`；这不会自动替你打开操作系统/Python的长路径支持。不要截短原文件名、静默跳过路径或把不完整解压当作完整归档。本轮归档与暂存工具的实机验证环境是Linux，Windows/macOS未实机测试。

## 2. 先只读校验

在解压的根目录：

```bash
python tools/verify_archive.py
python tools/prepare_git_upload.py
```

两条都不会联网、创建Git仓库、运行研究或调用模型。需要Python 3.11+和后续步骤的Git。Windows可用`py -3.11`替代`python`。

## 3. 只在目标远端仍为空时使用此快捷流程

```bash
git init -b main
git remote add origin https://github.com/zyh-0905/ReCheck.git
git ls-remote --heads origin
```

**最后一条有任何分支输出就停下。**此时应克隆现有仓库，保留其历史，检查同名文件差异后再合并材料；不得force push、reset远端、删远端文件或切到另一个仓库。无法读取远端/身份无权限也停止。

确认远端为空之后：

```bash
python tools/prepare_git_upload.py --stage
python tools/prepare_git_upload.py --check-index
git diff --cached --stat
git commit -m "Archive ReCheck research, data, reviews and R16 manuscript"
git push -u origin main
```

暂存工具先校验本地字节与目标origin，然后将清单中的文件按原始字节写入Git对象与暂存区。这样不会被历史子目录的`.gitignore`漏掉`.json/.log`数据，也不会运行历史`.gitattributes`指定的clean过滤器或改变换行。它不提交、不推送、不删除现有追踪文件。索引已有部分暂存变更时会拒绝覆盖；已经完整暂存时可重复检查而不重新写入。

本工具统一采用100644普通文件Git模式，历史Python脚本使用`python script.py`运行。不要运行旧目录中的shell或Python实验以“验证上传”。

## 4. 推送后独立确认

```bash
git rev-parse HEAD
git ls-remote origin refs/heads/main
python tools/prepare_git_upload.py --check-index
```

远端main的SHA必须与本地HEAD一致。检查原始数据目录、64条记录、R16 PDF和LaTeX均在远端。只有真实`git push`成功且远端SHA一致后，才能说完成上传。

`PUBLISH_STATUS.json`描述的是**本次打包时**未推送的状态，不要为显得已完成而在推送前伪改它。真实发布记录可在上传后另建release/提交记录，并注明根清单是冻结快照；新增文件会使严格集合校验失败，需明确更新发布清单而不是覆盖原始附件哈希。

## 5. 禁止事项

不上传.env/密钥/venv，不改仓库可见性，不自动重跑LLM，不删除原始失败/更正，不把工作稿改名为已录用版本，不用当前助手的无写权限连接绕过用户GitHub权限。未经授权不将数据转存第三方网站。
