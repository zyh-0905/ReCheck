# R5：任务损失核与共享预算的离线研究
版本：r5-5.0.0；协议R5_TASK_LOSS_OFFLINE_01。
本轮所有实验已在研究端执行；你的任务是跨机器复现与记录规划成本。
**零LLM/API调用；没有模型配置、smoke、密钥或充值步骤。**
同一冻结随机带的重复运行不是新增独立样本，不能加到论文n中。

## 1. 新目录与依赖
独立解压到R5_Research_Kit。不要覆盖或操作R1—R4目录。
Python3.11+，numpy==2.3.5；不需要GPU、Docker、LaTeX。
依赖安装可能访问包索引；实验命令本身禁用网络。
macOS/Linux，在包含r5.py的目录：
```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python r5.py execute
```
Windows PowerShell：
```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe r5.py execute
```
也可以使用已安装同一NumPy版本的Python环境；不要因此改旧工程文件。

## 2. execute做什么
依次prepare → run → audit → export：
- 用64份校准目录生成损失表，32份独立验证目录只用于诊断；
- 64条新基础流、两种菜单严格配对、8种策略，共8192次规则任务执行；
- H=2/4/6/8冷启动规划时间/内存测量，计时和内存分别执行；
- 重建全部策略动作和执行记录，独立算术评分；
- 对照研究端参考的1024条科学轨迹哈希；
- 导出反馈包。
没有HTTP fixture或模型请求。训练使用的已知标签与评测真值隔离，
公开请求中的任务类别/缓存语义允许读取，当前目录和真实模式不可用于在线选择。

完整命令也可以分开运行：
```bash
.venv/bin/python r5.py prepare
.venv/bin/python r5.py run
.venv/bin/python r5.py audit
.venv/bin/python r5.py export
```
Windows替换Python路径即可，不改变其他参数。

## 3. 回传
上传终端最后输出的：
```
uploads/R5_feedback_<UTC时间>.zip
```
包含完整1024条轨迹、校准/验证材料、私有合成评测数据、
统计、计时、代码快照与清单。无需手工撰写“成功原因报告”。
代码与科学轨迹哈希只是可复现性证据，不是数字签名或学术有效性的保证。

## 4. 错误或中断
不改协议、种子、校准表、基线或SOURCE_MANIFEST，不为了匹配参考值修改结果。
如测试或execute失败，保留终端错误；可以单独运行audit/export回传诊断。
audit有机械问题会返回非零状态，但export仍可单独打包；正常的阴性科研结果不会被拒绝。
若强制终止留下.write.lock，不删除锁强行续跑，先导出已有证据。
已完成run再次执行不会产生新的轨迹或计时样本；常规重复审核是离线复算。
本轮没有付费调用，因此不存在自动重试模型的机制。
不同硬件的计时、内存与部分浮点表示可不同；科学差异交给研究审核判别，
不要自己重采样“修”到与参考一致。

## 5. 信息和成本边界
主指标=实际任务失败+.05×运行期额度；不是货币或墙钟时间。
每条策略轨迹运行期8额度、每轮4；共同启动校准等价6额度单列。
校准训练、独立验证、冷启动编译、后续查表、工具执行分别计时。
初始化理想、危险率已知、语义族有限、task输出不更新信念，仍是本轮限制。
同一R4 API的新种子和数据变化不等于跨领域公开基准。
完整核与单项核没有稳定分出胜负，不据此宣布论文达到录用要求。
R5不再给模型做字段复制付费；RepairLens本轮没有新的主算法证据。

## 6. 隐私
程序不读取API环境变量、.env或模型配置。
导出只收集登记源码和已知运行文件；不收集无关目录、虚拟环境、SSH私钥。
命中常见凭据模式会阻止打包；不要关闭检查。
标准库网络入口在实验进程内被禁用；这是执行约束，不是对任意恶意系统代码的安全证明。
科研判断始终为PENDING_RESEARCHER_REVIEW，机械PASS不会自动允许下一轮实验。
