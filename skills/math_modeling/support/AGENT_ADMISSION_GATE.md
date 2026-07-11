# Agent Admission Gate：Agent 准入闸门

## 1. 默认策略

Shumo 默认使用确定性 Workflow。Agent 不是默认升级项，而是用更高成本、延迟和不确定性换取开放问题处理能力的受控组件。

任何模块准备启用 Agent 前，必须先执行本准入闸门。未形成准入记录时，只能继续使用 Workflow，不能因为任务“看起来复杂”就自动启用 Agent。

## 2. 四项强制评估

### 2.1 问题空间是否真正模糊

检查能否预先列出完整或近似完整的决策树：

- 若输入、步骤、分支和输出均可枚举，使用 Workflow；
- 若需要在未知路径中探索、比较多个假设或根据中间结果改变路线，才可能使用 Agent；
- “步骤很多”不等于“问题模糊”。长而确定的流程仍应使用 Workflow。

### 2.2 任务价值是否覆盖 Agent 成本

评估 Agent 的额外开销是否值得：

- 任务是否影响核心模型、关键创新、重大错误或最终排名；
- Agent 是否可能显著降低错误、提高方案质量或节省大量人工判断；
- 若只是格式整理、文件转换、编号、登记或常规计算，不启用 Agent。

### 2.3 关键能力是否已经可靠

Agent 行动链中的核心能力必须经过验证。例如：

- 建模 Agent 必须能正确识别变量、约束和可验证假设；
- 编码 Agent 必须能运行、调试并解释测试结果；
- 评审 Agent 必须能指出可证伪问题，而不是只给泛泛建议；
- 不能用“后面再检查”掩盖关键能力缺失。

若关键能力未经样例、测试或历史任务验证，Agent 只能运行在人工检查点之后，不能自主推进到下一阶段。

### 2.4 错误是否可发现、可阻断、可恢复

必须回答：

- 错误会通过什么残差、测试、约束、对照或人工检查暴露；
- 错误发生后能否停止，而不是继续污染后续成果；
- 是否可以回滚到上一个可信成果；
- 是否存在难以察觉但影响重大的错误。

若重大错误难以发现，禁止自主 Agent。应改用 Workflow、双重验证或人工决策。

## 3. 决策结果

准入结果只能是以下四类之一：

```text
workflow
bounded_agent
human_checkpoint
blocked
```

- `workflow`：任务可枚举，按固定步骤执行；
- `bounded_agent`：允许 Agent 在明确范围、预算和停止条件内探索；
- `human_checkpoint`：Agent 可提供候选或诊断，但必须由参赛者确认后才能行动；
- `blocked`：缺少关键能力、工具、输入或错误检测机制，暂停执行。

只有同时满足“问题模糊、价值足够、关键能力可靠、错误可发现”时，才允许 `bounded_agent`。

## 4. 标准准入记录

每次启用 Agent 前，生成：

```yaml
agent_admission:
  task_id: A-PX-01
  task: ""
  proposed_role: ""
  ambiguity:
    decision_tree_enumerable: true
    evidence: ""
  value:
    impact: low|medium|high
    expected_gain: ""
  capability:
    critical_capabilities: []
    evidence_of_reliability: []
    unresolved_bottlenecks: []
  error_control:
    detectable_failures: []
    checks: []
    rollback_point: ""
    silent_failure_risk: low|medium|high
  decision: workflow|bounded_agent|human_checkpoint|blocked
  scope:
    allowed_actions: []
    forbidden_actions: []
  budget:
    max_iterations: 0
    max_tool_calls: 0
    max_candidate_routes: 0
  stop_conditions: []
  approval_required: true|false
```

该记录进入当前问题成果包，不进入正式论文正文。

## 5. 数模任务默认映射

| 任务 | 默认执行方式 | 说明 |
|---|---|---|
| 读取题面、提取输入输出 | Workflow | 字段和步骤可枚举 |
| 单位换算、参数登记 | Workflow | 必须确定且可审计 |
| 生成候选建模路线 | Bounded Agent | 具有开放探索价值 |
| 比较路线并决定取舍 | Human checkpoint | 需要参赛者判断留痕 |
| 按已选路线推导模型 | Workflow 为主 | 关键推导按规范执行 |
| 常规代码实现与运行 | Workflow | 规格、测试和输出明确 |
| 未知原因的调试 | Bounded Agent | 仅在测试和回滚齐备时 |
| 结果验证 | Workflow | 残差、约束和敏感性可预定义 |
| 方案压力测试 | Bounded review Agent | 高价值且输出可验证 |
| 公式归属和编号 | Workflow | 必须全局确定 |
| 论文写作和格式化 | Workflow | 严格按蓝图生成 |

## 6. Agent 边界

Agent 必须满足：

1. 只操作准入记录允许的任务范围；
2. 不直接修改全局登记库，先输出候选变更；
3. 不绕过质量门槛进入下一层；
4. 不把探索性结论当成已验证事实；
5. 达到预算或停止条件后立即返回当前最佳证据；
6. 重大分支选择必须保留用户或团队决策记录。

## 7. 设计原则

- 能用 Workflow 解决的，不交给 Agent；
- 能用单次模型调用解决的，不建立循环 Agent；
- 能通过约束缩小空间的，先缩小空间再探索；
- 先设计错误检测，再授予行动权限；
- Agent 的自主程度不得高于系统发现其错误的能力。
