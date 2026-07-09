# Shumo

A math-modeling agent skill repository.

## 当前 Skill

- `skills/math_modeling/SKILL.md`：数学建模写作与求解规范。
- `skills/math_modeling/FORMULA_REUSE_PROTOCOL.md`：公式库、模型边界与重复公式审查协议，是数学建模 Skill 的补充约束。
- `skills/math_modeling/registry/model_contracts.yaml`：各问题的模型边界规则库，定义必须引用、禁止重复定义和允许新增的模型。
- `skills/math_modeling/registry/formulas.yaml`：公式登记库，记录已经建立过的公式、首次出现位置和复用规则。
- `skills/math_modeling/checks/check_formula_reuse.py`：公式重复定义审查脚本。

## 核心写作要求

每一个数学建模问题均按“总—分—总”结构组织：

1. **总**：开头说明本问目标、总体思路和求解流程；
2. **分**：中间逐步展开数学模型推导，公式、变量、约束、求解逻辑不得遗漏或跳步；
3. **总**：结尾给出计算结果、结果解释、误差检验和结论。

## 公式复用与模型边界要求

为避免后续问题重复定义前文已经建立的公式，新增以下强制流程：

1. 写新问题前，先检查 `registry/formulas.yaml` 中已经登记的公式；
2. 再检查 `registry/model_contracts.yaml` 中该问题的模型边界；
3. 已有模型只能用“沿用”“调用式号”“参数替换”等方式引用；
4. 本问只新增解决当前问题所必需的变量、约束、目标函数、判定函数和算法；
5. 输出前使用 `checks/check_formula_reuse.py` 审查是否出现重复定义。

板凳龙项目中，基础螺线模型只在问题一完整建立，板凳实体与碰撞判定只在问题二完整建立，问题三以后原则上只引用前文模型并建立本问新增优化或路径模型。
