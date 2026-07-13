# Reference Isolation Protocol：参考隔离与独立建模协议

## 1. 目的

本协议用于防止参考论文、公开解答、历史比赛结果或联网搜索结果在建模早期造成路线锚定、结果抄近或不可追踪的知识混入。

参考资料不是禁止使用，而是必须控制其读取时机、权限和影响范围。默认流程为：

```text
原始题面与附件核验
→ 独立建模阶段
→ 冻结独立基线
→ 人工确认开放参考资料
→ 参考对照阶段
→ 采纳决策与来源记录
```

## 2. 来源分级

### 2.1 A 类：权威输入

可以在所有阶段读取：

- 官方题面；
- 官方附件和输出模板；
- 竞赛规则；
- 用户明确提供且属于题目事实的数据；
- 已核验的单位、字段和格式要求。

A 类来源决定“题目要求是什么”，不能被参考论文覆盖。

### 2.2 B 类：项目内生证据

可以在所有阶段按依赖关系读取：

- 当前项目已验证的前序模型；
- 程序输出；
- 残差、边界、敏感性和一致性检查；
- 项目登记库和已冻结成果包。

B 类来源决定“本项目已经证明了什么”。

### 2.3 C 类：外部参考

默认在独立建模阶段不可读：

- 同题或相近题参考论文；
- 公开代码、博客、论坛答案；
- 联网搜索到的完整解题路线；
- 历史获奖论文和已知数值答案；
- 由参考资料汇总出的主流方法或结果范围。

C 类来源只能用于冻结独立基线后的比较、纠错、补充验证和来源追踪。

## 3. 阶段 R0：来源核验

Workflow 必须先完成：

1. 读取官方题面和附件；
2. 登记文件哈希、页数、工作表和数据范围；
3. 区分 A/B/C 类来源；
4. 创建 `reference_exposure_log.yaml`；
5. 明确当前运行是否已接触 C 类来源。

若在独立基线冻结前已经读取 C 类来源，必须将运行标记为：

```text
contaminated_for_blind_claim
```

该标记不代表模型无效，但禁止宣称结果是在未知参考答案的条件下独立产生。

## 4. 阶段 R1：独立建模

### 4.1 可读环境

只允许：

- A 类权威输入；
- 当前问题直接依赖的 B 类项目成果；
- 通用数学、编程和数值方法知识。

Agent 或 Workflow 的 `readable_paths` 不得包含参考论文目录、参考结果矩阵或外部解法摘要。

### 4.2 联网规则

默认禁止搜索：

- 题号、题目标题加“解答”“论文”“代码”“结果”；
- 与当前题目高度相似的完整解决方案；
- 已知获奖论文和结果数值。

只有在确实需要领域事实、标准、物理常数或官方规范时才可联网，并必须记录：

- 查询内容；
- 使用目的；
- 访问来源；
- 是否包含解题路线；
- 采用了哪些事实。

若搜索结果意外暴露同题解法，应立即记录暴露并重新评估是否还能保留 blind 状态。

### 4.3 输出

独立阶段必须形成：

```text
independent_baseline.yaml
```

至少包括：

- 问题理解；
- 候选路线；
- 选定路线及理由；
- 模型、算法和结果；
- 验证证据；
- 未解决问题；
- 成果文件哈希；
- `reference_exposure_status`。

## 5. 阶段 H-R：参考开放检查点

独立基线冻结后，由用户或团队确认是否进入参考对照阶段。

确认记录必须包含：

```yaml
reference_release:
  baseline_frozen: true
  baseline_hash: ""
  approved_by: user|team
  allowed_reference_sets: []
  allowed_purposes:
    - compare_methods
    - detect_errors
    - add_validation
  forbidden_purposes:
    - overwrite_without_evidence
    - copy_prose
    - adopt_result_as_ground_truth
```

未完成该检查点，不得把 C 类来源加入环境。

## 6. 阶段 R2：参考对照

参考资料开放后，只做结构化比较：

- 参考路线与独立路线的差异；
- 假设、目标、约束和重叠率定义差异；
- 结果分歧及其可能原因；
- 参考方案提供的新验证方法；
- 参考资料自身的矛盾、排版错误或不可复现部分。

不得因为“多数论文都这样做”而直接覆盖独立模型。任何修改必须有题意、数学或验证证据。

## 7. 阶段 R3：采纳决策

每一项从参考资料吸收的内容必须记录：

```yaml
adoption_decision:
  item_id: ""
  source: ""
  proposed_idea: ""
  baseline_before_reference: ""
  decision: adopt|adapt|reject|needs_test
  evidence: []
  implementation_change: ""
  validation_added: []
```

论文正文不得复制参考资料表述。参考资料对最终模型有实质影响时，应按竞赛规范引用。

## 8. 运行状态

允许的隔离状态：

```text
blind_clean
blind_with_domain_facts_only
contaminated_for_blind_claim
reference_released
reference_compared
```

`contaminated_for_blind_claim` 的处理方式：

1. 保留当前运行，称为 assisted 或 reference-aware baseline；或
2. 在全新会话、全新 Agent 环境或新测试题中重新运行，并确保 C 类来源不可读。

仅靠提示“忘掉参考论文”不能恢复 blind 状态。

## 9. 与 Agent 的关系

- Route Explorer 在 R1 阶段不得读取 C 类来源；
- Solution Review Agent 可在 R1 做纯内部压力测试，也可在 R2 做参考差异审查，但两种运行必须分开记录；
- Agent Prompt 必须列出参考资料是否可读；
- 工具不得在未授权时自动联网检索同题方案；
- 参考开放不能绕过人工检查点。

## 10. 质量门槛

进入论文架构层前必须能够回答：

- 当前模型是否在参考开放前冻结？
- 哪些外部资料在什么时间被读取？
- 哪些结论独立产生，哪些受外部资料影响？
- 每项采纳是否有数学或实验依据？
- 是否存在无法追踪来源的模型、公式、代码或数值？

来源不清的关键内容不得作为已验证创新或独立成果进入论文。