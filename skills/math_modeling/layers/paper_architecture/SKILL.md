---
name: math-modeling-paper-architecture-layer
description: 负责论文蓝图、模型归属、符号与公式编号，不负责重新建模或写最终正文。
---

# 第二层：论文架构与全局登记

## 1. 职责

本层只解决“已经完成的建模成果应怎样组织成一篇统一论文”。它位于建模求解与正式写作之间，是防止公式重复、编号冲突和章节各自为政的控制层。

本层负责：

- 读取各问题建模成果包；
- 规划论文整体章节和每问的叙事边界；
- 确定模型、公式和符号的首次定义位置；
- 分配全局公式、图、表和算法编号；
- 明确后续章节应引用哪些前文模型；
- 规划公共假设、公共符号表和项目专用附录；
- 控制页数、篇幅和推导详略；
- 更新项目登记库与模型边界合同；
- 生成供第三层严格执行的论文蓝图。

本层不负责：

- 新建模型、补推公式或重新计算结果；
- 改变第一层已经验证的数学含义；
- 直接生成完整论文段落；
- 为让某一节“自洽”而重复定义前文公式；
- 把计算过程中的全部约束机械写入论文。

发现建模成果缺失或相互矛盾时，必须退回第一层，并写明缺口，不能在本层自行补齐。

## 2. 输入

必须读取：

1. 项目配置；
2. 已完成问题的 `artifacts/modeling/problemX.model.yaml`；
3. `registry/parameters.yaml`；
4. `registry/formulas.yaml`；
5. `registry/model_contracts.yaml`；
6. 题目对正文、附件、页数和格式的要求。

此外必须读取 registry/assumptions.yaml；参数和假设采用登记库唯一来源时，不得把它们复制成
当前问题的 LaTeX 清单。

## 3. 核心原则

### 3.1 首次定义权

每个基础模型、核心公式和公共符号只能有一个“所有者章节”。所有者章节负责完整定义，后续章节只允许：

- 调用式号；
- 说明参数替换；
- 说明适用区间变化；
- 在原模型上增加本问的新目标、约束或判定函数。

### 3.2 计算约束与论文表达分离

第一层为保证计算正确而使用的约束，不等于第三层必须逐条写出的正文内容。本层应把约束分为：

- `must_show`：不写就无法理解模型成立性的核心约束；
- `reference_only`：前文已定义，只需引用；
- `algorithm_only`：只属于数值实现、容差或程序保护；
- `appendix_only`：细节必要但不宜占用正文；
- `omit`：探索阶段使用、最终路线不再需要。

### 3.3 编号唯一

公式编号由本层统一分配，第一层的语义 ID 保持不变。推荐在 `registry/formulas.yaml` 中同时记录：

```yaml
F-P1-HANDLE-RECURSION:
  label: eq:p1-handle-recursion
  owner_section: problem1.position_recursion
  first_defined_in: problem1
  reuse_rule: reference_only
```

第三层不得自行创建与蓝图冲突的新标签。

### 3.4 单题可读性不等于重复推导

后续问题需要自洽时，用一至三句说明前文模型的用途和本问新增内容，不复制基础轨迹、坐标、递推或碰撞公式。完整性通过引用与承接实现，而不是通过重复实现。

## 4. 工作流程

### 4.1 建模成果一致性审查

检查：

- 不同问题是否使用同一符号表示不同含义；
- 同一模型是否出现多个等价但不同写法；
- 参数单位、编号和索引是否一致；
- 后续模型是否确实依赖前序模型；
- 结果是否与登记库和附件一致。

### 4.2 模型所有权分配

为每个模型组件指定：

- `owner_section`；
- `first_definition`；
- `reuse_sections`；
- `allowed_extensions`；
- `forbidden_redefinitions`。

### 4.3 章节蓝图设计

每一问至少明确：

- 本问核心结论；
- 承接前文的内容；
- 本问新增模型；
- 必须出现的公式、图、表和结果；
- 应放入算法或附录的细节；
- 结尾应回答的题目要求；
- 预计篇幅。

### 4.4 登记库更新

架构确定后更新：

- registry/assumptions.yaml；

- `registry/parameters.yaml`；
- `registry/formulas.yaml`；
- `registry/model_contracts.yaml`。

不得把具体项目公式写回通用 Skill 目录。

## 5. 标准输出：论文蓝图

推荐路径：

```text
<project>/artifacts/architecture/paper_blueprint.yaml
```

最低字段：

```yaml
paper:
  title: ""
  language: zh-CN
  numbering:
    equation: global
    figure: chapter
    table: chapter
common_sections:
  assumptions: []
  symbols: []
sections:
  problem1:
    thesis: "本节一句话核心结论"
    inherits: []
    new_models: []
    formula_plan:
      define: []
      reference: []
      forbidden_redefine: []
    content_plan: []
    figures: []
    tables: []
    appendices: []
    page_budget: 0
registry_updates:
  parameters: []
  formulas: []
  contracts: []
open_issues: []
status: approved|needs_modeling_revision
```

## 6. 交付给第三层的门槛

项目启用符号化逐问正文契约时，蓝图必须把当前问内容分别放入“第2章问题分析”和“第5章模型的
建立与求解”，且第5章固定包含“问题模型建立、模型求解、结果分析”。假设与参数值的正文
placement 必须设为 omit，来源转为项目登记库。

只有满足以下条件才允许进入正式写作：

- 所有基础模型均有唯一所有者章节；
- 公式标签和编号无冲突；
- 每一问明确“继承内容”和“新增内容”；
- 计算约束已按正文、算法、附录和省略分类；
- 题目要求的结果、文件和指定对象均有落点；
- 页数和章节篇幅可控；
- `open_issues` 为空或已明确允许带条件写作。

启用逐问审核时，蓝图可以只覆盖当前问题，但必须作为哈希绑定产物写入
`../../support/PROBLEM_REVIEW_GATE.md` 定义的审核记录；未获批前不规划下一问题正文。
