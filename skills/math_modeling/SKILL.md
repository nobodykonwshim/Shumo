---
name: math-modeling-router
description: 以 Workflow 为主、受控 Agent 为辅，将数学建模任务路由到建模求解、论文架构或论文写作层，并维持项目登记库与跨问题复用。
---

# Shumo 数学建模总入口

## 1. 首要原则：Workflow first, Agent when justified

Shumo 不把所有复杂任务都包装成 Agent。默认使用确定性 Workflow；只有问题空间真正模糊、任务价值足够高、关键能力可靠且错误可发现时，才允许启用有边界的 Agent。

复杂不等于模糊。步骤多但可以枚举的任务仍应使用 Workflow。

任何 Agent 启用前必须读取：

- `support/AGENT_ADMISSION_GATE.md`；
- `support/AGENT_RUNTIME_CONTRACT.md`。

未形成 `agent_admission` 记录时，不允许进入多轮 Agent 循环。

## 2. 三层职责架构

```text
Workflow/Agent 编排入口
        │
        ▼
第一层：建模与求解
        │  problemX.model.yaml
        ▼
第二层：论文架构与全局登记
        │  paper_blueprint.yaml
        ▼
第三层：论文写作与成稿
```

三个阶段必须分离：

- 第一层以数学正确、可计算、可验证为目标；
- 第二层以全篇结构、模型归属、符号和编号统一为目标；
- 第三层以准确、紧凑、可直接提交的论文表达为目标。

论文不是建模探索过程的完整记录，而是对已验证研究成果的组织与表达。

## 3. 默认主流程

标准流程见 `workflows/README.md`：

```text
项目初始化
→ 题目解析与交付清单
→ Agent 准入判断
→ 候选路线探索（可选 Agent）
→ 参赛者路线确认
→ 模型规格化
→ 代码实现与求解
→ 结果验证
→ 方案压力测试（可选 Agent）
→ 成果包与登记库固化
→ 论文蓝图
→ 正式写作
→ 一致性与交付检查
→ 逐问人工审核（启用 sequential_review 时）
→ 获批后进入下一问
```

只有候选路线探索、未知故障诊断和方案压力测试是默认 Agent 插槽。其他步骤优先使用 Workflow。

## 4. Agent 与 Workflow 选择

### 4.1 必须使用 Workflow 的任务

- 题面字段提取和逐问交付清单；
- 单位换算、参数登记和路径检查；
- 已确定模型的规格化推导；
- 按规格实现代码、运行命令和生成结果文件；
- 残差、约束、边界、敏感性和一致性检查；
- 公式所有权、编号和跨问题引用；
- 按蓝图写 LaTeX、Word 或 Markdown；
- 最终格式、数值和附件一致性检查。

### 4.2 可申请受控 Agent 的任务

- 多条合理建模路线的开放探索；
- 题目特有结构和可验证创新的发现；
- 无法由预定义故障树解释的代码或数值异常；
- 对关键方案进行反例、隐藏假设和简化机会压力测试。

### 4.3 禁止自主 Agent 的情形

- 重大错误难以察觉；
- 缺少测试、残差、对照或回滚点；
- 关键能力尚未验证；
- Agent 将直接修改全局登记库、已验证结果或最终论文；
- 任务价值不足以覆盖成本和延迟。

此时应使用 Workflow、人工检查点或标记为 `blocked`。

## 5. 第一层：建模与求解

以下请求进入 `layers/modeling/SKILL.md`：

- 理解题目、拆解输入输出和约束；
- 生成、比较和选择建模路线；
- 建立与推导模型；
- 设计算法、实现代码和数值求解；
- 生成结果文件；
- 执行残差、敏感性、稳健性、边界和临界性验证。

该层输出结构化建模成果包，不直接输出最终论文正文。

需要创新探索时，可在准入通过后调用 `support/INNOVATION_EXPLORER.md`。需要独立压力测试时，可调用 `support/SOLUTION_REVIEW_AGENT.md`。

## 6. 第二层：论文架构与全局登记

以下请求进入 `layers/paper_architecture/SKILL.md`：

- 规划整篇论文或各问关系；
- 决定公共假设和公共符号位置；
- 统一公式、图、表和算法编号；
- 指定模型和公式首次定义章节；
- 防止后一问重复前一问公式；
- 控制页数和推导详略；
- 更新项目参数、公式和模型边界登记库。

第二层是确定性 Workflow。它只生成论文蓝图和登记库更新，不重新建模，不使用 Agent 自由改写模型。

## 7. 第三层：论文写作与成稿

以下请求进入 `layers/paper_writing/SKILL.md`：

- 将已确定模型写成论文；
- 生成单节、单章或整篇正式正文；
- 输出 LaTeX、Word、Markdown；
- 按蓝图插入公式、图表、结果和引用；
- 修改语言、格式和图表衔接；
- 对成稿执行重复、编号和一致性检查。

第三层是确定性 Workflow，禁止重新建模、重新求解、重新编号、调用探索 Agent 或临时增加创新点。

## 8. 复合请求

用户要求“完整建模与求解并写成论文”时，必须串行执行：

```text
第一层完成建模成果包
→ 第二层生成或更新论文蓝图
→ 第三层生成正式正文
```

不得跳过第二层直接把第一层探索记录改写成论文，也不得让一个 Agent 同时修改模型、代码、登记库和正文。

若用户要求逐问审核，还必须在每一问的第三层输出后执行
`support/PROBLEM_REVIEW_GATE.md`。当前问题的审核记录不是 `approved`，或任一绑定产物哈希发生变化时，
下一问题保持锁定。

## 9. 最小上下文加载

为减少 token 消耗，每次只读取：

1. 当前 Workflow 或 Agent 所需的单一规则文件；
2. 项目配置；
3. 当前问题输入和附件；
4. 项目登记库；
5. 当前任务的直接依赖成果包或蓝图条目；
6. Agent 运行时显式声明的环境清单。

默认不得通读整个仓库、全部历史对话或所有前序章节。跨问题复用优先读取登记库和结构化成果。

## 10. Environment、Tools、Prompt

Agent 只围绕三个基础组件设计：

- `environment`：可读、可写、不可变路径及已知/未知状态；
- `tools`：结构化输入、返回观察、副作用、失败信号和验证步骤；
- `prompt`：目标、成功标准、权限、禁止动作、预算和停止条件。

行为稳定前，不引入多 Agent 讨论、长期记忆、自主递归规划或无限反思循环。

设计者必须从 Agent 的受限视角完整模拟一次任务，检查哪些信息只存在于设计者脑中、哪些工具结果无法验证、哪些隐含约束没有传给 Agent。

## 11. 项目配置中心

每个项目应建立：

```text
<project>/project.yaml
```

模板见 `config/project_config.example.yaml`。配置集中管理：

- 竞赛类型、语言、单位和路径；
- Workflow 与 Agent 编排策略；
- Agent 准入、预算、权限和停止条件；
- 三层质量门槛；
- 公式、图表和章节编号；
- 创新探索与验证要求；
- 目标输出格式；
- 上下文加载范围。

各层不得分别维护相互冲突的项目规则。

## 12. 项目登记库

具体赛题的数据保存在：

```text
<project>/registry/parameters.yaml
<project>/registry/formulas.yaml
<project>/registry/model_contracts.yaml
```

已有 `2024A/registry/` 保持有效。

第一层使用稳定公式语义 ID；第二层分配最终标签和所有者；第三层只按标签引用。

## 13. 跨问题复用规则

1. 基础模型只在所有者章节完整建立一次；
2. 后续问题使用“沿用前文模型”“由式……”“将参数替换为……”承接；
3. 后续问题只新增当前目标所需内容；
4. 公共假设和公共符号统一出现一次；
5. 最终公式编号由第二层控制；
6. 输出前运行 `checks/check_formula_reuse.py`；
7. Agent 不得绕过登记库自行重新定义前序模型。

详细兼容协议见 `FORMULA_REUSE_PROTOCOL.md`。

## 14. 状态、退回与回滚

- 第一层模型、结果或验证不完整：标记 `partial` 或 `blocked`；
- Agent 达到预算或无法增加证据：标记 `partial`、`escalated` 或 `rolled_back`；
- 第二层发现符号、模型或验证冲突：退回第一层；
- 第三层发现缺失公式、结果或编号：退回对应层，不得猜测；
- 有副作用的工具动作必须具有验证步骤和回滚点。

Agent 的自主程度不得高于系统发现其错误的能力。

## 15. 创新原则

AI 不能保证某一方案对所有参赛队伍绝对唯一。创新应来自：

- 题目特有的几何、物理、统计或优化结构；
- 常规方法在本题中的具体失效点；
- 对搜索、判定、降维、复用或验证流程的针对性改造；
- 参赛者对候选路线的选择和取舍；
- 可通过证明、计算或对照实验验证的实际收益。

不得把复杂、冷门、模型堆叠或名称包装直接当作创新。

## 16. 相关文件

- `workflows/README.md`：Workflow 主流程；
- `layers/modeling/SKILL.md`：第一层；
- `layers/paper_architecture/SKILL.md`：第二层；
- `layers/paper_writing/SKILL.md`：第三层；
- `support/AGENT_ADMISSION_GATE.md`：Agent 准入；
- `support/AGENT_RUNTIME_CONTRACT.md`：环境、工具与 Prompt 契约；
- `support/INNOVATION_EXPLORER.md`：候选路线探索；
- `support/SOLUTION_REVIEW_AGENT.md`：方案压力测试；
- `support/PROBLEM_REVIEW_GATE.md`：逐问论文审核与顺序门禁；
- `config/project_config.example.yaml`：项目配置模板；
- `FORMULA_REUSE_PROTOCOL.md`：公式复用协议；
- `checks/check_formula_reuse.py`：重复定义审查脚本；
- `docs/ARCHITECTURE.md`：完整架构说明。
