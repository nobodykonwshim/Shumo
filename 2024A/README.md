# 2024A 板凳龙项目库

本目录用于存放 2024 高教社杯 A 题《板凳龙》项目专用资料。通用数模 Skill 只保留写作规则、流程约束和审查脚本；本题的公式库、参数库和模型边界规则均存放在本目录中。

## 当前文件

- `registry/parameters.yaml`：问题一至问题三参数库，包括题面参数、单位换算、编号规则和已求结果。
- `registry/formulas.yaml`：问题一至问题三公式库，包括公式标签、LaTeX 形式、含义、首次定义位置和复用规则。
- `registry/model_contracts.yaml`：2024A 项目模型边界规则，规定各问题必须引用、禁止重复定义和允许新增的模型。

## 使用流程

写或修改任意问题前，先按以下顺序检查：

```text
1. 读取 registry/parameters.yaml，确认参数、单位和编号；
2. 读取 registry/formulas.yaml，确认已有公式和标签；
3. 读取 registry/model_contracts.yaml，确认本问写作边界；
4. 已有公式只用式号引用，不重复推导；
5. 本问只新增当前问题允许新增的变量、约束、判定函数和算法；
6. 输出前用通用审查脚本检查重复定义。
```

通用审查脚本位于：

```text
skills/math_modeling/checks/check_formula_reuse.py
```

示例：

```bash
python skills/math_modeling/checks/check_formula_reuse.py \
  --contract 2024A/registry/model_contracts.yaml \
  --problem problem3 \
  --tex sections/problem3.tex
```

## 板凳龙写作边界

- 问题一：完整建立基础螺线模型、位置递推模型和速度递推模型；
- 问题二：完整建立板凳实体矩形模型和非相邻板凳碰撞判定模型；
- 问题三：只建立最小螺距可行性搜索模型，不重复问题一、问题二公式；
- 问题四：只建立 S 形调头曲线和统一路径参数化；
- 问题五：只建立速度放大系数和最大龙头速度模型。
