# Shumo 三层架构

## 1. 架构目标

Shumo 将“解题研究”和“论文成稿”拆开，避免一个 Skill 同时承担互相冲突的目标：

- 建模阶段需要充分探索、增加计算约束并验证结果；
- 论文阶段需要控制篇幅、统一编号并减少重复；
- 若两者混在同一 Prompt 中，模型容易把调试约束写入论文，也容易在每一问重新推导已有公式。

重构后的主流程为：

```text
题目与项目登记库
        │
        ▼
第一层：建模与求解
        │  输出 problemX.model.yaml
        ▼
第二层：论文架构与全局登记
        │  输出 paper_blueprint.yaml
        ▼
第三层：论文写作与成稿
        │  输出 sections/problemX.tex / Word / Markdown
        ▼
重复定义、编号和结果一致性检查
```

Innovation Explorer 是第一层的支持模块，不是独立写作层。

## 2. 目录结构

```text
Shumo/
├── README.md
├── CHANGELOG.md
├── docs/
│   ├── ARCHITECTURE.md
│   └── MIGRATION.md
├── skills/math_modeling/
│   ├── SKILL.md                       # 路由入口
│   ├── FORMULA_REUSE_PROTOCOL.md      # 兼容协议
│   ├── config/
│   │   └── project_config.example.yaml
│   ├── layers/
│   │   ├── modeling/SKILL.md
│   │   ├── paper_architecture/SKILL.md
│   │   └── paper_writing/SKILL.md
│   ├── support/
│   │   └── INNOVATION_EXPLORER.md
│   └── checks/
│       └── check_formula_reuse.py
└── <project>/
    ├── project.yaml
    ├── registry/
    │   ├── parameters.yaml
    │   ├── formulas.yaml
    │   └── model_contracts.yaml
    ├── artifacts/
    │   ├── modeling/problemX.model.yaml
    │   └── architecture/paper_blueprint.yaml
    ├── sections/
    ├── results/
    └── figures/
```

现有 `2024A/` 等项目目录继续有效，无需迁移到通用 Skill 目录。

## 3. 数据合同

### 3.1 第一层 → 第二层

第一层输出建模成果包。该文件是“研究事实源”，包括：

- 模型依赖；
- 新旧符号；
- 公式语义 ID；
- 算法；
- 结果；
- 验证；
- 创新路线；
- 论文必须体现和应省略的内容。

第二层不得越过成果包自行补模型。

### 3.2 第二层 → 第三层

第二层输出论文蓝图。该文件是“写作控制源”，包括：

- 章节核心结论；
- 模型与公式所有者；
- 最终标签和编号；
- 前文引用；
- 新增内容；
- 图表与结果落点；
- 约束的正文/算法/附录/省略分类；
- 页数预算。

第三层不得绕过蓝图自由扩写。

## 4. 路由规则

| 用户请求 | 路由 |
|---|---|
| 分析题目、给方案、建立模型、求解、计算结果 | 第一层 |
| 比较方法、寻找创新点、形成不同路线 | 第一层 + Innovation Explorer |
| 规划整篇论文、处理重复公式、统一符号和编号 | 第二层 |
| 把已有成果写成论文、LaTeX 或 Word | 第三层 |
| “完整建模并写成论文” | 串行执行一 → 二 → 三，不得跳层 |
| 审核现有论文 | 先用第二层检查架构，再用第三层检查表达；数学正确性问题退回第一层 |

## 5. 状态与退回机制

```text
modeling: partial/blocked
    └─ 不进入第二层，先补计算或验证

architecture: needs_modeling_revision
    └─ 退回第一层，禁止第二层自行推导

writing: missing_blueprint_or_result
    └─ 退回第二层或第一层，禁止猜测补全
```

## 6. 公式生命周期

1. 第一层用语义 ID 建立公式，例如 `F-P1-HANDLE-RECURSION`；
2. 第二层指定首次定义章节和 LaTeX 标签；
3. 第三层只在所有者章节完整写出；
4. 后续章节用式号引用；
5. `check_formula_reuse.py` 根据项目合同检查禁止重复内容。

这样可以同时满足：

- 建模阶段可独立追踪公式；
- 全篇编号统一；
- 后续问题不重复展开；
- 项目规则与通用 Skill 分离。

## 7. Token 与上下文控制

每次执行只加载：

- 当前层 Skill；
- 项目配置；
- 当前问题输入；
- 项目登记库；
- 直接依赖的成果包或蓝图条目。

默认禁止为处理单个问题而通读整个仓库或所有历史正文。跨问题复用优先依赖登记库和结构化成果包，而不是复制前序章节全文。

## 8. 设计原则

- 研究事实、论文结构和论文表达分别管理；
- 通用规则放在 `skills/`，项目数据放在项目目录；
- 公式以语义 ID 跨阶段传递，以最终标签进入论文；
- 创新必须从基线缺陷和题目结构中产生，并通过结果验证；
- 论文体现建模约束，但不复制全部调试与程序保护条件；
- 论文不是探索过程记录，而是经验证成果的组织表达。
