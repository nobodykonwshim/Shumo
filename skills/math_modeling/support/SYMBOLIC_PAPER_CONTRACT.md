# 符号化逐问正文契约

## 1. 项目开关

当项目要求参数与假设统一登记、正文按问题拆分时，配置以下字段：

    paper_writing:
      model_formula_mode: symbolic
      assumption_parameter_presentation: registry_only
      per_problem_section_contract: cumcm_analysis_and_solution

该模式下，registry/parameters.yaml 与 registry/assumptions.yaml 是参数值和假设的唯一来源。
模型规格可以引用这些登记项，LaTeX 正文不得复制参数表或假设清单。

## 2. 模型建立的符号化规则

1. 模型建立部分只写变量、参数符号、向量、算子和适用区间。
2. 题面数值和项目选择值不得直接代入轨迹方程、目标函数、约束或判据。
3. 允许出现定义数学结构所必需的常数，如零向量、区间端点 \(0,1\) 和动力学系数
   \(\tfrac12\)；这些常数不得替代应登记的题目参数。
4. 参数值只允许出现在模型求解的输入证据、计算结果、结果表和验证报告中。
5. 后续问题必须先读取参数、假设、公式和模型合同登记库，再按语义 ID 引用；不得从前序
   LaTeX 反向复制参数或假设。

例如，无人机速度、投放时刻和起爆延迟应分别写成 \(v_F,t_d,\tau_b\)，而不是在模型公式中
写入某个具体速度或时刻。

## 3. 逐问章节落点

每解决一个问题，至少生成两个可独立并入总稿的 LaTeX 片段：

    第2章 问题分析
    └─ 2.x 问题x分析

    第5章 模型的建立与求解
    └─ 5.x 问题x的模型建立与求解
       ├─ 5.x.1 问题模型建立
       ├─ 5.x.2 模型求解
       └─ 5.x.3 结果分析

问题分析说明目标、对象关系、输入输出和求解难点，不列参数值和假设。问题模型建立保持完全
符号化；模型求解读取登记库并说明算法；结果分析报告数值、原因、边界和问题答案。

## 4. 目标视轮廓与边缘视线段判别

当目标为凸体且题目要求完整遮挡时，可以用视点下的闭合视轮廓代替整个目标表面。对圆柱目标，
视轮廓由上底远侧圆弧、下底近侧圆弧及两条侧面切线母线组成。侧线端点应由“视点到圆周相切”
条件精确确定；直接取离径向平面最远点只可作为远距离近似。

对视点 \(\boldsymbol r_V(t)\)、轮廓点 \(\boldsymbol X\) 和球形遮挡物中心
\(\boldsymbol r_C(t)\)，定义

\[
\boldsymbol a=\boldsymbol X-\boldsymbol r_V(t),\qquad
\boldsymbol b=\boldsymbol r_C(t)-\boldsymbol r_V(t),
\]

并把球心投影到闭视线段：

\[
\lambda^*=\operatorname{clip}
\left(\frac{\boldsymbol a^{\mathsf T}\boldsymbol b}
{\boldsymbol a^{\mathsf T}\boldsymbol a},0,1\right),\qquad
d=\lVert\boldsymbol b-\lambda^*\boldsymbol a\rVert.
\]

若轮廓中每一点对应的距离均不超过登记的烟幕半径，则轮廓被遮挡。由于目标和球形遮挡区域均为
凸集，在适用边界成立时可由闭合轮廓推出内部视线同时被覆盖。项目必须登记轮廓构造适用条件，
并通过圆周切线残差、边缘加密和时间步长加密验证数值稳定性。若目标非凸、遮挡区域有孔洞或
视点穿过目标高度范围，则不得直接沿用该简化。

## 5. 检查

使用 validation/symbolic_latex_validator.py 检查章节结构与模型建立区中的题面数值。模型建立
片段用以下注释标记：

    % SHUMO-SYMBOLIC-MODEL-BEGIN
    ...
    % SHUMO-SYMBOLIC-MODEL-END

该检查只证明结构和符号化边界，不证明模型数学正确。
