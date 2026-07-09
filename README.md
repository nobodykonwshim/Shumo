# Shumo

A math-modeling agent skill repository.

## 当前 Skill

- `skills/math_modeling/SKILL.md`：数学建模写作与求解规范。
- `skills/math_modeling/FORMULA_REUSE_PROTOCOL.md`：公式复用与模型边界审查协议，仅定义通用流程和约束。
- `skills/math_modeling/checks/check_formula_reuse.py`：通用公式重复定义审查脚本。

## 项目库

- `2024A/`：2024 高教社杯 A 题《板凳龙》项目库。
- `2024A/registry/parameters.yaml`：问题一至问题三参数库。
- `2024A/registry/formulas.yaml`：问题一至问题三公式库。
- `2024A/registry/model_contracts.yaml`：2024A 项目专用模型边界规则。

## 核心写作要求

每一个数学建模问题均按“总—分—总”结构组织：

1. **总**：开头说明本问目标、总体思路和求解流程；
2. **分**：中间逐步展开数学模型推导，公式、变量、约束、求解逻辑不得遗漏或跳步；
3. **总**：结尾给出计算结果、结果解释、误差检验和结论。

## 公式复用与模型边界要求

通用数模 Skill 只保存规则和审查脚本，不保存具体赛题的公式库、参数库或项目模型数据。具体项目的公式、参数和模型边界应放在对应项目目录下，例如 `2024A/registry/`。

写新问题前的强制流程：

1. 先检查项目目录中的 `registry/parameters.yaml`；
2. 再检查项目目录中的 `registry/formulas.yaml`；
3. 再检查项目目录中的 `registry/model_contracts.yaml`；
4. 已有模型只能用“沿用”“调用式号”“参数替换”等方式引用；
5. 本问只新增解决当前问题所必需的变量、约束、目标函数、判定函数和算法；
6. 输出前使用 `skills/math_modeling/checks/check_formula_reuse.py` 审查是否出现重复定义。
