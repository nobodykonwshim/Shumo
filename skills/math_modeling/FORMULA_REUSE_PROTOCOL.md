# 公式复用与模型边界审查协议

本协议用于保证多问题数学建模论文中的模型、符号和公式只在正确位置定义一次。它由三层架构共同执行，但各层职责不同。

## 1. 职责分配

### 第一层：建模与求解

- 读取项目参数库、公式库和模型边界库；
- 区分“沿用模型”和“本问新增模型”；
- 对新公式分配稳定语义 ID，不分配最终论文编号；
- 在建模成果包中列出复用关系和待登记条目；
- 不因论文自洽需要而重复推导前序模型。

### 第二层：论文架构与全局登记

- 指定每个模型和公式的唯一所有者章节；
- 分配最终 LaTeX 标签和全局编号；
- 更新 `registry/formulas.yaml` 与 `registry/model_contracts.yaml`；
- 决定后续章节应完整定义、引用、放入算法、移入附录或省略哪些内容；
- 解决符号冲突和同式异写问题。

### 第三层：论文写作与成稿

- 只完整写出蓝图允许在当前章节定义的公式；
- 已有公式使用式号引用、模型调用或参数替换表达；
- 不重新推导、重新编号或更换符号；
- 输出前执行重复定义和编号检查。

## 2. 项目数据边界

通用 Skill 只保存流程、规则、模板和检查脚本，不保存具体赛题公式、参数和结果。项目专用内容必须放在：

```text
<project>/registry/parameters.yaml
<project>/registry/formulas.yaml
<project>/registry/model_contracts.yaml
```

例如：

```text
2024A/registry/parameters.yaml
2024A/registry/formulas.yaml
2024A/registry/model_contracts.yaml
```

## 3. 核心规则

1. 每个基础模型和核心公式只有一个首次定义位置；
2. 后续问题只能引用、调用、限定适用区间或进行参数替换；
3. 后续问题只新增解决当前目标所必需的变量、约束、目标函数、判定函数和算法；
4. 公共假设、公共符号表和公共基础模型不得在每一问重复；
5. 第一层语义 ID 在跨阶段保持稳定，第二层为其分配最终标签；
6. 第三层不得使用未登记公式或自行创建冲突标签；
7. “章节完整性”通过承接说明和式号引用实现，不通过复制公式实现。

## 4. 写作前强制检查

处理新问题前按顺序读取：

```text
项目配置
→ registry/parameters.yaml
→ registry/formulas.yaml
→ registry/model_contracts.yaml
→ 当前问题直接依赖的建模成果包
```

然后列出：

- 已有模型；
- 已有公式语义 ID 和论文标签；
- 当前问题必须引用的条目；
- 当前问题禁止重复定义的内容；
- 当前问题允许新增的内容。

未完成该检查，不得直接生成正式章节。

## 5. 公式库建议格式

```yaml
F-P1-HANDLE-RECURSION:
  label: eq:p1-handle-recursion
  name: "相邻把手位置递推关系"
  latex: "..."
  meaning: "..."
  owner_section: problem1.position_recursion
  first_defined_in: problem1
  reuse_rule: reference_only
  forbidden_redefine: true
  reused_by:
    - problem2
    - problem3
```

其中：

- `F-P1-HANDLE-RECURSION` 是第一层使用的稳定语义 ID；
- `label` 由第二层统一分配；
- `owner_section` 是唯一完整定义位置；
- `reused_by` 记录后续调用关系。

## 6. 参数库建议格式

```yaml
parameter_id:
  symbol: "参数符号"
  value: "数值"
  unit: "单位"
  meaning: "含义"
  source: "题面|计算结果|假设|外部数据"
  first_used_in: problem1
```

## 7. 模型边界库建议格式

```yaml
problemX:
  must_reference:
    - F-P1-HANDLE-RECURSION
  forbidden_redefine:
    - "相邻把手位置递推模型"
  allowed_new_models:
    - "本问新增判定函数"
  content_classification:
    must_show: []
    reference_only: []
    algorithm_only: []
    appendix_only: []
    omit: []
  review_before_output:
    - "检查公式标签冲突"
```

`content_classification` 用于避免把全部计算约束机械写入论文。

## 8. 推荐承接表达

```latex
本问沿用问题一建立的位置递推关系，并以式~\eqref{eq:p1-handle-recursion}计算各把手位置。在此基础上，仅新增板凳实体几何表示与碰撞判定条件。
```

```latex
将前文模型中的螺距参数替换为 $p$，其余运动学关系保持不变，因此本节不再重复推导轨迹和速度递推公式。
```

承接段应说明“沿用什么、改变什么、新增什么”，不应复制前文完整推导。

## 9. 审查脚本

通用检查脚本保持位于：

```text
skills/math_modeling/checks/check_formula_reuse.py
```

调用方式保持兼容：

```bash
python skills/math_modeling/checks/check_formula_reuse.py \
  --contract 2024A/registry/model_contracts.yaml \
  --problem problem3 \
  --tex 2024A/sections/problem3.tex
```

该脚本负责关键词与合同级检查。全局编号、模型所有权和语义冲突仍需由第二层审查。

## 10. 输出前清单

- 是否读取项目配置和三个登记库？
- 当前公式是首次定义还是复用？
- 首次定义章节是否与蓝图一致？
- 是否重复出现前文轨迹、坐标、弧长、递推、实体几何或碰撞模型？
- 是否只新增当前问题必需的模型？
- 公式标签是否冲突？
- 公共符号是否被重复定义？
- 算法容差是否被误写成题目约束？
- 计算约束是否按正文、引用、算法、附录和省略分类？
- 正文是否使用了正确的式号承接？
- 是否通过复用检查脚本？

任一关键项不满足时，不得交付正式论文。

## 11. 优先级

本协议优先于“每一节必须独立完整”的写作习惯。后续章节可以简述前文模型用途，但不得重新建立已存在的模型。数学正确性问题退回第一层，公式归属和编号问题由第二层处理，正式表达问题由第三层处理。
