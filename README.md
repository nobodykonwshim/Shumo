# Shumo

A modular math-modeling competition workflow for research, solution architecture, and paper writing.

## 三层架构

Shumo 不再用一个单体 Prompt 同时完成建模和论文写作，而是把任务拆成三个职责清晰的阶段：

```text
第一层：建模与求解
    ↓ problemX.model.yaml
第二层：论文架构与全局登记
    ↓ paper_blueprint.yaml
第三层：论文写作与成稿
```

- **第一层**负责题目理解、模型建立、算法、代码、结果和验证；
- **第二层**负责章节规划、模型归属、公共符号、公式编号和跨问题引用；
- **第三层**只把已确认成果写成论文，不重新建模、求解或编号。

Innovation Explorer 作为第一层支持模块，用于比较常规路线、识别题目特有困难、形成可验证改进，而不是在论文写作阶段临时包装创新点。

## 目录

```text
skills/math_modeling/
├── SKILL.md
├── FORMULA_REUSE_PROTOCOL.md
├── config/project_config.example.yaml
├── layers/
│   ├── modeling/SKILL.md
│   ├── paper_architecture/SKILL.md
│   └── paper_writing/SKILL.md
├── support/INNOVATION_EXPLORER.md
└── checks/check_formula_reuse.py

docs/
├── ARCHITECTURE.md
└── MIGRATION.md
```

具体项目继续独立保存参数、公式、模型边界、结果和论文文件。例如：

```text
2024A/
├── registry/
│   ├── parameters.yaml
│   ├── formulas.yaml
│   └── model_contracts.yaml
├── artifacts/
│   ├── modeling/
│   └── architecture/
├── sections/
├── results/
└── figures/
```

## 使用方式

### 1. 建立项目配置

复制配置模板：

```text
skills/math_modeling/config/project_config.example.yaml
```

到项目目录并命名为：

```text
<project>/project.yaml
```

### 2. 建模与求解

调用第一层，形成：

```text
<project>/artifacts/modeling/problemX.model.yaml
```

该成果包记录模型、算法、结果、验证、创新路线和登记库更新，不是最终论文正文。

### 3. 规划论文

调用第二层，形成：

```text
<project>/artifacts/architecture/paper_blueprint.yaml
```

蓝图决定公式首次定义位置、最终标签、前文引用、图表落点和篇幅。

### 4. 写正式章节

第三层只读取已批准蓝图、当前建模成果包和必要的登记库条目，生成 LaTeX、Word 或 Markdown 正文。

## 公式复用

基础模型和核心公式只能在唯一所有者章节完整定义一次。后续问题使用式号引用、模型调用或参数替换，不得重新推导。

通用审查脚本：

```bash
python skills/math_modeling/checks/check_formula_reuse.py \
  --contract 2024A/registry/model_contracts.yaml \
  --problem problem3 \
  --tex 2024A/sections/problem3.tex
```

详细规则见 `skills/math_modeling/FORMULA_REUSE_PROTOCOL.md`。

## Token 与上下文控制

处理单个问题时只加载：

- 当前层 Skill；
- 项目配置；
- 当前问题输入；
- 项目登记库；
- 直接依赖的成果包或蓝图条目。

默认不通读整个仓库、所有历史对话或全部前序章节。跨问题复用优先依赖登记库和结构化成果包。

## 兼容性

- 保留现有 `2024A/` 项目库；
- 保留原参数库、公式库和模型合同；
- 保留 `check_formula_reuse.py` 调用方式；
- 现有 LaTeX 章节无需立即重写；
- 新架构可从后续问题开始使用，也可对旧章节反向提取成果包。

完整设计见 `docs/ARCHITECTURE.md`，迁移步骤见 `docs/MIGRATION.md`。
