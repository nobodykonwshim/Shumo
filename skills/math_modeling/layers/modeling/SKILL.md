---
name: math-modeling-research-layer
description: 以确定性 Workflow 完成题目解析、模型规格、代码求解和验证，并在通过准入闸门后有限调用路线探索、故障诊断或方案评审 Agent。
---

# 第一层：建模与求解

## 1. 职责

本层只解决“题目怎样被正确、可复现地算出来”。本层不再被视为一个持续自主的大 Agent，而是由固定 Workflow 和少量受控 Agent 插槽组成。

本层负责：

- 题目与附件解析；
- 逐问输入、输出、约束和验收标准；
- 数据清洗、单位统一和参数来源核验；
- 候选路线探索与参赛者决策留痕；
- 模型规格、公式推导和算法设计；
- 代码实现、数值求解和结果文件生成；
- 残差、敏感性、稳健性、边界与临界性验证；
- 形成结构化建模成果包。

本层不负责：

- 决定论文最终章节顺序；
- 分配最终公式编号；
- 将探索过程原样写入论文；
- 为了论文篇幅删改计算事实；
- 使用“本文”“本问”口吻生成最终正文。

## 2. 执行模式

默认模式为 `workflow`。允许的 Agent 类型只有：

```text
route_explorer
 diagnostic_agent
solution_reviewer
```

启用任何 Agent 前必须生成 `agent_admission`，并读取：

- `../../support/AGENT_ADMISSION_GATE.md`；
- `../../support/AGENT_RUNTIME_CONTRACT.md`。

若问题可以通过固定分支、规则、测试或单次候选生成解决，不启用多轮 Agent。

## 3. 强制输入

执行前只读取：

1. 项目配置文件；
2. 题面与当前问题附件；
3. 项目参数库；
4. 项目公式库；
5. 项目模型边界库；
6. 当前问题直接依赖的前序成果包；
7. 当前 Workflow 或 Agent 所需的单一规则文件。

不得默认通读全部历史对话、项目文件或已完成章节。

## 4. Workflow M0：题目解析与交付清单

本步骤必须确定性执行，不使用 Agent。

逐问输出：

- 必须回答的目标；
- 必须输出的数值、图表、证明和附件；
- 已知量、未知量、状态量和决策变量；
- 题面显式约束和隐含物理约束；
- 文件字段、单位、顺序和精度；
- 与前序问题的继承关系；
- 可验收标准；
- 仍缺失的信息。

本步骤只做问题定义，不提前把某一方案当成既定路线。

## 5. Gate G1：是否需要路线探索 Agent

执行准入闸门，重点判断：

- 是否存在多个合理路线；
- 决策树是否能预先枚举；
- 路线选择是否影响核心结果或创新价值；
- 是否可以通过基线、测试和后续验证发现错误；
- 参赛者是否需要保留最终选择权。

若不满足准入条件，直接采用成熟 Workflow 路线或进入人工检查点。

## 6. Agent A1：候选路线探索（可选）

通过准入后，可调用 `../../support/INNOVATION_EXPLORER.md`。

Agent 只生成有限候选，必须遵守：

- 明确候选数量上限；
- 每条路线给出基线、题目摩擦点、改造、代价、风险和验证方式；
- 不直接决定最终路线；
- 不修改登记库；
- 不宣称绝对独创；
- 达到预算或证据不再增加时停止。

## 7. Human checkpoint H1：路线确认

进入模型规格化前，必须记录：

```yaml
route_decision:
  selected_route: ""
  accepted_reasons: []
  rejected_routes: []
  rejected_reasons: []
  accepted_risks: []
  additional_validation_required: []
  decided_by: user|team|workflow
```

开放路线的最终取舍属于参赛者判断，不应由 Agent 静默决定。

## 8. Workflow M1：模型规格化

路线确定后，停止继续发散，按以下顺序建立可执行模型规格：

```text
对象与状态定义
→ 参数、单位和来源
→ 假设与适用边界
→ 基本几何/物理/统计关系
→ 局部约束或判据
→ 全局目标或判据
→ 可计算形式
→ 边界与异常情况
→ 验证计划
```

关键数学动作不得跳过，包括积分、求导、投影、代入、递推、取极值、离散化、线性化和可行域构造。

公式使用稳定语义 ID，例如：

```text
F-P1-HEAD-POSITION
F-P1-HANDLE-RECURSION
F-P2-COLLISION-MARGIN
```

最终论文式号由第二层分配。

模型规格至少包含：

- 输入输出；
- 变量和参数；
- 公式语义 ID；
- 约束和可行域；
- 算法步骤；
- 边界与失败模式；
- 预期验证器。

## 9. Workflow M2：代码实现与数值求解

按规格确定性执行：

1. 建立最小可运行样例；
2. 实现核心模型；
3. 添加断言、日志和输入检查；
4. 运行小规模测试；
5. 执行完整求解；
6. 保存代码、命令、依赖、随机种子和结果文件；
7. 分类失败类型。

算法记录至少包含：

- 输入与输出；
- 初值或粗估来源；
- 搜索区间或可行域；
- 迭代、扫描、优化或判定步骤；
- 停止准则与精度；
- 多解筛选和异常处理；
- 复杂度和主要计算瓶颈；
- 可复现命令。

### 9.1 已知失败

若失败原因在故障树中，例如文件缺失、单位错误、搜索区间为空、求解器不收敛或 schema 不匹配，按预定义修复分支处理。

### 9.2 未知失败

只有无法由预定义故障树解释、且已经具备测试和回滚点时，才可重新通过准入闸门调用 `diagnostic_agent`。

诊断 Agent 只能定位原因和提出最小修复，不得同时重构模型、修改论文和登记库。

## 10. Workflow M3：结果验证

任何结果必须追溯到程序输出或明确计算。验证规则应尽量在看到最终结果前定义。

至少执行与问题匹配的检查：

- 单位与维度；
- 方程残差和约束违反量；
- 极值、边界、零值和退化情形；
- 可手算小样例；
- 多步长、多初值或多算法一致性；
- 参数敏感性和稳健性；
- 物理量级、单调性和边界合理性；
- 结果文件 schema、行列和精度完整性；
- 附件与关键数值一致性。

不得仅以“软件求得”或“结果合理”作为验证。

## 11. Gate G2 与 Agent A2：方案压力测试（可选）

对高价值关键方案，可在基础验证完成后通过准入闸门调用 `../../support/SOLUTION_REVIEW_AGENT.md`。

评审 Agent 只输出：

- 隐藏假设；
- 反例和边界测试；
- 重大风险；
- 简化机会；
- 追加验证；
- 接受、修改或退回建议。

它不直接改成果包和登记库。`revise` 或 `reject` 必须退回对应 Workflow。

## 12. Workflow M4：成果固化

模型与结果通过门槛后：

1. 生成 `problemX.model.yaml`；
2. 提交参数、公式和模型合同候选变更；
3. 检查语义 ID 冲突；
4. 记录验证证据；
5. 记录未解决限制和风险；
6. 区分计算约束与论文必须体现内容；
7. 设置状态。

推荐路径：

```text
<project>/artifacts/modeling/problemX.model.yaml
```

## 13. 标准成果包

```yaml
problem_id: problemX
objective: ""
dependencies:
  models_reused: []
  formulas_reused: []
inputs: []
outputs_required: []
assumptions: []
symbols:
  reused: []
  new: []
route_decision:
  selected_route: ""
  accepted_reasons: []
  rejected_routes: []
agent_admissions: []
agent_runs: []
model_components:
  - id: M-PX-01
    purpose: ""
    derivation: ""
    formulas: []
algorithms: []
results: []
validation: []
solution_review: null
innovation:
  baseline: ""
  modification: ""
  evidence: ""
  limitations: ""
new_registry_entries:
  parameters: []
  formulas: []
  model_contracts: []
writing_notes:
  essential_claims: []
  omit_from_paper: []
status: solved|partial|blocked
```

`writing_notes` 只标记哪些内容应进入论文，不得在本层写最终论文段落。

## 14. 完成门槛

只有同时满足以下条件，成果包才能交给第二层：

- 输出目标完整覆盖题目要求；
- 路线选择有记录；
- 关键公式和算法可复现；
- 参数来源、单位和索引明确；
- 结果通过定量验证；
- Agent 行动均有准入、预算、证据和停止记录；
- 已更新待登记的公式、参数和模型边界；
- 已区分计算约束和论文内容；
- 创新点有基线、改造和验证依据；
- 没有未处理的 critical 评审问题。
