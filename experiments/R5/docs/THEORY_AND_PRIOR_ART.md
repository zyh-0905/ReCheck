# R5 理论对象与先行工作边界

## 1. 核心对象：校准得到的方向敏感任务损失
q为公开任务类别；m为最近一次校准后记住的三个语义位；z为真实当前语义位。
在独立校准目录D上实际调用原R4工具工作流，得到：
    L_hat(q,m,z) = (1/N) sum_d 1[executor(D_d,q,m,z) != gold(D_d,q)]
N=64是独立目录数，不是64×5×8×8个独立样本。所有组合共享相同目录。
保留完整5×8×8表可以表示方向性和多通道交互。single_effect_exact只使用单通道翻转结果，
通过noisy-OR合成多通道失配后果；它是重要的结构简化基线，不声称联合表必然更好。

在线/测试时，策略只看到q、各证据的年龄、缓存位m、剩余额度和剩余时域。
当前目录、真实z、最终正确答案、未来任务带和任务输出均不传给策略。
因此这是“根据校准分布预测当前任务损害”，不是先看当前正确答案再选探测。
当前类别编码只保留工作流与阈值档位；具体SKU/类别没有被学习模型单独建模。
已知对称漂移率、已知任务转移、准确初始化与理想校准仍是限制。

## 2. 刷新后的记忆必须随观测更新
给定年龄a_j和已知翻转率h_j：
    p_j = [1-(1-2h_j)^(a_j)]/2
    P(z|m,a) = product_j (p_j if z_j!=m_j else 1-p_j)
一次探测覆盖C后 m'_C=z_C，其他位仍取m；更新记忆不能被当作原m不变。
    g_C(q,m,a) = sum_z P(z|m,a) L_hat(q,m^C(z),z)
    V_h(a,m,q,b) = min_{C admissible} {c(C) + g_C
                   + E_{z_C,q'} V_{h-1}(a',m^C(z),q',b-cost(C))}
实现按8种缓存位并行计算，当前观察和未来任务均按模型积分。
测试与独立两步穷举逐项核对，并确认无预算、零损失和免费探测边界。

“年龄相同就应做相同决策”在方向敏感损失下未必成立：
若页码0→1导致明确接口错误，而1→0仅可能漏掉不相关商品，缓存位本身影响风险。
一项测试固定三个年龄为3、h=.12、单项价=.1：缓存页码0时选择核验，
缓存页码1时无需核验。该构造证明所选年龄-only状态会丢失决策信息，
不是声称首次提出POMDP充分状态。

## 3. 一个基础扰动界——不是新的通用定理
假设转移/观测模型完全正确、成本相同，且所有(q,m,z)上
    |L_hat-L| <= epsilon.
对任意允许策略，其H步目标偏差至多H epsilon，因为每步期望是损失条目的凸组合。
若pi_hat在L_hat模型中与最优值差至多gamma，则
    J_L(pi_hat) - min_pi J_L(pi) <= 2H epsilon + gamma.
证明：插入并减去J_Lhat(pi_hat)和J_Lhat(pi*)，两端各用H epsilon，中间用gamma。
这只是标准有限时域模型/奖励误差论证的实例，不作为主要创新。

校准64目录的Hoeffding+union bound可以给320个条目的同时界，
但数值很宽；验证目录的max差.203125也不是总体epsilon的认证值。
数据分布变化、漂移模型失配或未建模语义会破坏保证的前提。
不能把这个界写成开放世界安全证书，也不能将经验均值优势写成已证明优势。

## 4. 直接的先行工作
1. Shisher & Sun, How Does Data Freshness Affect Real-time Supervised Learning?,
   https://arxiv.org/abs/2208.06948
   https://www.sigmobile.org/mobihoc/2022/accepted_papers.html
   https://github.com/Kamran0153/Impact-of-Data-Freshness-in-Learning
   已研究信息新鲜度与推断误差、数据驱动评价和调度；不能声称首次从误差而非年龄出发。
2. Javdani et al., Near Optimal Bayesian Active Learning for Decision Making,
   AISTATS 2014, https://proceedings.mlr.press/v33/javdani14.html
   已研究为了决策而非完全消除假设不确定性选择测试；不能把决策相关性当新概念。
3. Golovin, Krause & Ray, Near-Optimal Bayesian Active Learning with Noisy Observations,
   https://arxiv.org/abs/1010.3091
   测试成本与假设等价类已有理论；本项目不自动继承其自适应次模近似保证。

R5提供的是可检验的“任务后果核+值敏感状态+严格分离的校准/评测”原型。
它尚未形成足够发表的一般新算法定理。完整核与单项核对比不支持一味增加复杂度。
