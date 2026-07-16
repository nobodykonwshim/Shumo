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

## 4. 视点投影与完整遮挡的向量表达

若遮挡对象具有不可忽略的空间尺度，不能只检查一个目标参考点。对视点
\(\boldsymbol r_V(t)\)、目标点集 \(\mathcal T\) 及其登记参考点
\(\boldsymbol r_{T,c}\)，先定义观察平面的单位法向量

\[
\boldsymbol n(t)=
\frac{\boldsymbol r_{T,c}-\boldsymbol r_V(t)}
{\lVert\boldsymbol r_{T,c}-\boldsymbol r_V(t)\rVert}.
\]

选择不与 \(\boldsymbol n\) 平行的登记参考向量 \(\boldsymbol k\)，构造观察平面的两个正交
基向量，并以三者为行组成世界坐标到视点坐标的正交矩阵 \(\boldsymbol R(t)\)。对任意空间点
\(\boldsymbol X\)，先计算

\[
\boldsymbol x_c=\boldsymbol R(t)
[\boldsymbol X-\boldsymbol r_V(t)],
\]

再用深度归一化完成透视投影。不得把忽略深度的正交投影直接当作视点成像；只有在项目模型
给出近似条件和误差验证时才可使用该简化。

球形遮挡物在像平面上的边界由“视点—球体”切锥与像平面的交线给出，可写成齐次二次曲线
\(\widetilde{\boldsymbol y}^{\mathsf T}\boldsymbol Q
\widetilde{\boldsymbol y}=0\)。完整遮挡须同时满足：

1. 目标点集的全部透视投影均落入该二次曲线的遮挡区域；
2. 每条对应目标射线先与遮挡物相交，再到达目标点。

第二个条件用于排除“遮挡物在目标之后但二维投影重合”的伪遮挡。实现时可用视线段与球的
相交判据作为等价的数值计算器，但论文投影表述、数值等价性和验证证据必须保持一致。视点、
目标点集、参考向量、球半径和有效期均来自项目登记库，通用 Skill 不固定题目数值。

## 5. 检查

使用 validation/symbolic_latex_validator.py 检查章节结构与模型建立区中的题面数值。模型建立
片段用以下注释标记：

    % SHUMO-SYMBOLIC-MODEL-BEGIN
    ...
    % SHUMO-SYMBOLIC-MODEL-END

该检查只证明结构和符号化边界，不证明模型数学正确。
