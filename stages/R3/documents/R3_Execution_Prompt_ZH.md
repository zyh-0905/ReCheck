# R3执行Prompt：交给本地代码助手

你是本轮实验的执行者，不是调参者或论文结论审核者。请在用户提供的全新 `R3_Research_Kit` 目录中，按包内README和固定协议执行。用户已经授权本轮上限：smoke1次＋主命令416次＝最多417次模型请求尝试。该上限不是账单金额保证。不允许充值、购买或租用资源。

## 固定任务

运行R3 ReCheck开发实验：16条流、每流12任务、ReCheck/Myopic两方法。384个主计划调用＋32个相同输入的独立重复诊断；数值答案由程序呈现。RepairLens本轮不调用模型。不要把重复结果替换为主结果或挑选两次中较好的一次。

## 执行步骤

1. 确认当前是包含r3.py的**新R3目录**。不得覆盖LLM_Pilot_Kit、R1、R2，或复制旧运行目录充当R3。
2. 使用Python3.11+创建.venv，按requirements.txt安装依赖；运行 `python -m unittest discover -s tests -v`。这里python指.venv内解释器。测试访问的仅是本机模拟HTTP服务。
3. 运行 `python r3.py prepare`。这是零模型调用的离线检查。失败则保存完整stdout/stderr并export反馈，不改代码、参数、种子、测试或清单让它通过。
4. 密钥只在用户本地安全环境变量LLM_API_KEY或脚本隐藏输入中使用。不要读取密钥到自己的上下文、打印、粘贴聊天、写入文件或命令参数。需要隐藏输入时交由用户操作。
5. 运行 `python r3.py smoke --confirm-calls 1`。仅当原始R3 smoke状态completed且json_ok为true，才继续；禁止其他试探性API调用。
6. 运行 `python r3.py run --confirm-calls 416`。保持默认deepseek-flash、16384输出上限、thinking enabled、effort high。不能更换模型、端点或降低思考强度；不兼容时直接回传。
7. 正常完成或暂停后，运行 `python r3.py audit` 和 `python r3.py export`。验证最后生成的ZIP：`python r3.py verify uploads/实际文件名.zip`。
8. 将最后生成的R3_feedback_*.zip路径交给用户，要求上传该完整文件。不要擅自进入R4或运行RepairLens。

## 强制停止规则

HTTP错误、截断、非法JSON、usage异常、身份字段变化、中断状态或写锁都需暂停。不得删除.lock、编辑manifest、调用retry、循环smoke、新建多个运行目录试到成功。合法JSON下的接口违约或错误计划应原样记录，不“修好”模型输出。

程序已保存的原始证据不可编辑。若需要说明操作情况，只写你有直接日志支持的事实。不知道收费、中断原因、当前权重、内部路由时写unknown，不能替用户确认。缺账单不用登录服务商获取，也不阻断反馈。

## 信息边界

不得把private里的真实模式/答案提供给模型、修改任务以让ReCheck获胜、筛选seed、将软件fixture当真实模型数据。源码和协议已冻结，sha256是防误改检查，不是独立认证。

## 最终回复格式

- 实际命令与退出码；
- 状态：COMPLETED或PAUSED，不能自行写“论文已通过”；
- 可观察的请求开始/响应数量，主记录与重复记录分开；
- 反馈ZIP完整路径和verify结果；
- 可直接核实的错误；其他原因保持unknown。

不要自行判断ReCheck比Myopic优越，不把无量纲J当货币，不把384行当384独立样本。正常或阴性结果都回传，不自行重跑。
