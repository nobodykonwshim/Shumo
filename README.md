# Shumo

A workflow-first math-modeling competition framework with bounded Agent support for research, numerical solution, and paper writing.

## 核心理念

Shumo 不把所有任务都做成 Agent。

- **Workflow** 负责步骤清晰、可枚举、必须稳定复现的任务；
- **Agent** 只用于高价值、真正模糊、关键能力可靠且错误可发现的任务；
- **三层架构** 把建模研究、论文规划和正式写作分开。

```text
Workflow 主流程
→ 可选 Agent 插槽
→ 第一层建模成果包
→ 第二层论文蓝图
→ 第三层正式论文
```

## Agent 准入原则

启用 Agent 前必须评估：

1. 问题空间是否真正模糊；
2. 任务价值是否覆盖成本和延迟；
3. Agent 的关键能力是否已经可靠；
4. 重大错误是否可发现、可阻断、可回滚。

若决策树可以完整或近似完整地画出，直接使用 Workflow。

详细规则见：

- `docs/AGENT_VS_WORKFLOW.md`
- `skills/math_modeling/support/AGENT_ADMISSION_GATE.md`
- `skills/math_modeling/support/AGENT_RUNTIME_CONTRACT.md`

## 标准编排

```text
W0 项目初始化
→ W1 题目解析与交付清单
→ G1 Agent 准入判断
→ A1 候选路线探索（可选）
→ H1 参赛者路线确认
→ W2 模型规格化
→ W3 代码实现与数值求解
→ W4 结果验证
→ G2 评审 Agent 准入判断
→ A2 方案压力测试（可选）
→ W5 成果包与登记库固化
→ W6 论文架构与编号蓝图
→ W7 论文写作
→ W8 一致性与交付检查
```

其中：

- `W`：确定性 Workflow；
- `G`：Agent 准入闸门；
- `A`：可选受控 Agent；
- `H`：参赛者或团队决策点。

完整流程见 `skills/math_modeling/workflows/README.md`。

## 三层架构

### 第一层：建模与求解

负责题目解析、路线选择、模型规格、代码、结果和验证，输出：

```text
<project>/artifacts/modeling/problemX.model.yaml
```

第一层不是单体 Agent。题目解析、模型规格、实现和验证默认使用 Workflow。

### 第二层：论文架构与全局登记

负责章节规划、模型归属、公共符号、公式编号和跨问题引用，输出：

```text
<project>/artifacts/architecture/paper_blueprint.yaml
```

### 第三层：论文写作与成稿

严格读取成果包和论文蓝图，生成 LaTeX、Word 或 Markdown。禁止重新建模、重新求解、重新编号和临时包装创新点。

## 默认 Agent 插槽

Shumo 只保留三个 Agent 插槽：

1. **Route Explorer**：生成有限候选建模路线和可验证创新；
2. **Diagnostic Agent**：诊断无法由固定故障树解释的代码或数值异常；
3. **Solution Review Agent**：对关键方案寻找隐藏假设、反例、风险和简化机会。

每个 Agent 必须有：

- 明确 Environment；
- 结构化 Tools；
- 目标和权限清晰的 Prompt；
- 迭代与工具预算；
- 错误检测；
- 停止条件；
- 回滚点。

## 目录

```text
skills/math_modeling/
├── SKILL.md
├── FORMULA_REUSE_PROTOCOL.md
├── config/project_config.example.yaml
├── workflows/README.md
├── layers/
│   ├── modeling/SKILL.md
│   ├── paper_architecture/SKILL.md
│   └── paper_writing/SKILL.md
├── support/
│   ├── AGENT_ADMISSION_GATE.md
│   ├── AGENT_RUNTIME_CONTRACT.md
│   ├── INNOVATION_EXPLORER.md
│   └── SOLUTION_REVIEW_AGENT.md
└── checks/check_formula_reuse.py

docs/
├── ARCHITECTURE.md
├── AGENT_VS_WORKFLOW.md
└── MIGRATION.md
```

具体项目继续独立保存：

```text
<project>/
├── project.yaml
├── registry/
│   ├── parameters.yaml
│   ├── formulas.yaml
│   └── model_contracts.yaml
├── artifacts/
│   ├── agents/
│   ├── modeling/
│   └── architecture/
├── sections/
├── results/
└── figures/
```

## 使用方式

### 1. 建立项目配置

复制：

```text
skills/math_modeling/config/project_config.example.yaml
```

到：

```text
<project>/project.yaml
```

配置默认采用 `workflow_first`，并集中管理 Agent 类型、准入规则、预算、错误检测和停止条件。

### 2. 执行 Workflow 主流程

先完成题目解析和交付清单。只有遇到开放路线选择时，才运行 Agent 准入判断。

### 3. 固化建模成果

模型、代码和验证完成后生成 `problemX.model.yaml`，其中包含路线决策、Agent 运行记录、公式语义 ID、结果和验证证据。

### 4. 规划与写作

第二层生成论文蓝图；第三层按蓝图写作。不得把第一层探索记录直接改写为论文。

## 公式复用

基础模型和核心公式只能在唯一所有者章节完整定义一次。后续问题使用式号引用、模型调用或参数替换。

```bash
python skills/math_modeling/checks/check_formula_reuse.py \
  --contract 2024A/registry/model_contracts.yaml \
  --problem problem3 \
  --tex 2024A/sections/problem3.tex
```

## Token 与上下文控制

每次只加载：

- 当前 Workflow 或 Agent 规则；
- 项目配置；
- 当前问题输入；
- 项目登记库；
- 直接依赖成果；
- Agent 显式环境清单。

默认不通读整个仓库、全部历史对话或所有前序章节。

## 兼容性

- 保留现有 `2024A/` 项目库；
- 保留原参数库、公式库和模型合同；
- 保留 `check_formula_reuse.py` 调用方式；
- 现有 LaTeX 章节无需立即重写；
- 新架构可以增量采用。

完整设计见 `docs/ARCHITECTURE.md`，迁移步骤见 `docs/MIGRATION.md`。
