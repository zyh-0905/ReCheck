# 给本地代码助手：只执行R9J1固定真实模型实验

你是执行者，不是研究设计者。不要调参数、删除失败、解释模型动机、寻找能获胜的种子或制作肯定性论文结论。

## 身份与文件
使用用户指定的新目录 `R9J1_Research_Kit`。核对协议 `R9J1_LIVE_CONTINUATION_DIAGNOSIS_01`、版本 `r9-1.0.1`。
先读取README_ZH.md和docs/AMENDMENT_ZH.md。旧R9数据保持paused原样，不复制旧runs/PREPARED，不修改任何源码、清单或配置。
唯一输出设置变化已固定在包内：response_format=json_object。模型仍deepseek-v4-flash，max_tokens16384，thinking enabled，reasoning effort high。不得自动换模型、地址、格式或输出上限。

## 先检查新目录运行状态
- main completed：只audit/export，不重新生成。
- smoke completed且main尚不存在：跳过smoke，run一次。
- paused/running/已有孤立请求或锁：不要恢复；确认进程不再写入后audit/export。锁不删除。
- 全新目录：复用装有R9固定依赖的Python3.11解释器绝对路径；无可用解释器时按README新建.venv安装。不要读取旧密钥文件或.env。

## 命令
全新目录先用选定的Python3.11解释器：
```bash
python r9.py prepare
python r9.py smoke --confirm-calls 1
```
这里的python必须替换为已核对的解释器路径。smoke未completed时直接audit/export，禁止用主run做试探。
smoke通过后：
```bash
python r9.py run --confirm-calls 360
```
完成或暂停后：
```bash
python r9.py audit
python r9.py export
```
只回传最后的uploads/R9J1_feedback_*.zip；终端退出码可原样保存，不补造缺失记录。

## 密钥与次数
用户只在本地环境变量LLM_API_KEY或终端隐藏输入中配置凭据。不要要求用户在聊天中粘贴密钥，不在命令行带密钥，不执行/models、curl、SDK探针、余额查询、用户模拟器、LLM裁判或额外模型调用。
新smoke最多1次，主run最多360次，新增上限361。旧R9的2次单独保留，沿革累计上限363。这不是金额保证。
无需运行全套离线单元测试或规则实验，不增加GPU/其他服务花费。

## 停止规则
HTTP/协议/截断/JSON/usage/身份异常由运行器保留后暂停。只导出，不循环smoke、不宽松抽取首JSON、不自动选择其中一个工具、不删除锁、不新建第二份目录反复重跑。
合法JSON下工具错误按原10轮继续，不在后台重新请求相同logical_id。
不复述推理文本来宣称原因，不把mechanical_pass等同研究完成。没有新增R8或RepairLens实验。
