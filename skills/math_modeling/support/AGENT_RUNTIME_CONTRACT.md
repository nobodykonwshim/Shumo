# Agent Runtime Contract：环境、工具与提示词契约

## 1. 目的

本文件规定 Shumo 中所有受控 Agent 的最小运行结构。Agent 只依赖三个基础组件：

1. `environment`：Agent 实际能够观察和操作的系统；
2. `tools`：Agent 与环境交互的接口；
3. `prompt`：Agent 的目标、约束、权限和停止条件。

在三者未定义清楚之前，不增加长期记忆、多 Agent 协作、反思循环或复杂规划器。

## 2. Environment：环境清单

每个 Agent 运行前必须声明环境边界：

```yaml
environment:
  project_root: ""
  readable_paths: []
  writable_paths: []
  immutable_paths: []
  current_problem: ""
  available_artifacts: []
  unavailable_information: []
  external_state_assumptions: []
  rollback_point: ""
```

要求：

- 不假设 Agent 能看到未加载的文件、历史对话或工具状态；
- 不使用“项目中应该存在”“前文已经说明”等隐式信息；
- 对未读取的信息标记为未知，不得用常识补造项目事实；
- 写权限应小于读权限，且优先写入临时成果或候选变更文件。

## 3. Tools：工具接口

每个工具必须有明确契约：

```yaml
tool:
  name: ""
  purpose: ""
  required_inputs: []
  returned_observations: []
  side_effects: []
  failure_signals: []
  retry_policy: ""
  verification_after_call: []
```

工具设计要求：

1. 输入字段尽量结构化，避免让 Agent 猜路径、单位和命名；
2. 返回结果必须包含成功、失败或不完整状态；
3. 有副作用的工具必须提供验证步骤；
4. 工具失败不得被解释为任务成功；
5. 重试必须有上限，不能无限循环；
6. 文件写入、登记库更新和最终交付必须可回滚或通过 diff 审查。

## 4. Prompt：目标与权限

Agent Prompt 至少包含：

```yaml
prompt_contract:
  objective: ""
  success_criteria: []
  known_context: []
  unknowns: []
  allowed_actions: []
  forbidden_actions: []
  required_checks: []
  output_schema: ""
  budget: {}
  stop_conditions: []
  escalation_conditions: []
```

Prompt 不应只描述“做什么”，还必须描述：

- 什么结果才算完成；
- 哪些信息未知；
- 哪些动作禁止；
- 每一步如何验证；
- 何时停止、退回 Workflow 或请求人工判断。

## 5. 像 Agent 一样思考：视角模拟

设计者在启用 Agent 前，必须从 Agent 的受限视角完整模拟一次任务。

逐步回答：

1. Agent 当前能看到什么？
2. 下一步行动需要什么信息？
3. 该信息是否已在上下文或工具返回中明确提供？
4. Agent 调用工具后会得到什么可观察结果？
5. 它如何判断工具真的完成了预期动作？
6. 若结果为空、部分成功或单位错误，它能否识别？
7. 哪个状态只存在于设计者脑中、却没有传给 Agent？
8. 哪个隐含约束可能导致 Agent 做出“逻辑上合理、项目中错误”的选择？

任何无法回答的问题都属于认知缺口，应通过补充上下文、修改工具返回、增加检查点或降低自主性解决。

## 6. 最小执行循环

受控 Agent 使用以下循环：

```text
Observe
→ State the current gap
→ Choose one bounded action
→ Call one tool or produce one candidate
→ Verify the observation against expected evidence
→ Update state
→ Continue, stop, rollback or escalate
```

每轮只解决一个明确缺口。不得在同一轮同时改变模型、代码、结果和论文结构。

推荐运行记录：

```yaml
agent_run:
  run_id: ""
  admission_id: ""
  iterations:
    - observation: ""
      gap: ""
      action: ""
      expected_evidence: ""
      actual_evidence: ""
      verification: pass|fail|partial
      state_change: ""
  final_status: solved|partial|rolled_back|escalated|blocked
```

## 7. 错误可发现性

Agent 的每项关键输出必须绑定验证器：

- 数学推导：维度检查、边界条件、特殊情形、数值代回；
- 代码：单元测试、最小样例、断言、结果文件校验；
- 数值结果：残差、约束违反量、重复运行、基线对照；
- 创新方案：基线差异、可实现性和对照实验；
- 文件更新：路径、格式、schema 和 diff；
- 论文建议：与成果包、蓝图和登记库一致性。

无法绑定验证器的关键行动，默认需要人工检查点。

## 8. 停止与升级

出现以下任一条件时，Agent 必须停止：

- 达到最大迭代或工具调用次数；
- 连续两次行动没有增加有效证据；
- 关键假设无法验证；
- 工具返回与环境状态矛盾；
- 检测到可能污染全局登记库或已验证结果；
- 需要在多个高风险路线之间作价值判断；
- 错误检测能力不足以覆盖下一步行动。

停止后只能返回当前证据、未解决问题和建议的下一检查点，不得伪装成完成。

## 9. 简单优先

引入复杂机制前依次检查：

1. 能否通过更完整的 Prompt 解决；
2. 能否通过更好的工具参数或返回值解决；
3. 能否通过固定 Workflow 和验证器解决；
4. 能否通过一次受控候选生成解决；
5. 只有前四项不足时，才考虑多轮 Agent。
