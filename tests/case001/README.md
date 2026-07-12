# case001：多波束测线问题实战验证

## 目的

本案例用于验证 Shumo 的 `Workflow first, Agent when justified` 架构能否在真实数学建模题目上闭环运行，而不是直接追求一次性生成完整论文。

测试对象为多波束测深与测线布设问题。用户提供：

- `B题.rar`：题面、附件和题目给定结果表；
- `B477.pdf`、`B226.pdf`、`B311.pdf`：三篇参考论文。

参考论文只用于建立对照基线、识别常见路线和发现结果分歧，不作为唯一标准答案，也不允许系统复制论文表述。

## 分支

本案例位于：

```text
test/case001-multibeam-pilot
```

该分支基于三层架构 PR 的 head 创建，用于独立记录实战测试，不直接污染架构 PR。

## 当前阶段

```text
W0 项目初始化：已完成基础配置，状态 partial
W1 题目解析：已根据三篇参考论文交叉重建，等待原题面复核
G1 Agent 准入：已形成初始分题决策
W2 及以后：尚未开始
```

当前运行环境能够读取 RAR 文件目录，但缺少可用的 RAR 解压后端，因此尚未直接读取压缩包中的 `B题.pdf` 和 `附件.xlsx`。在该缺口关闭前，不进入正式建模与数值求解。

## 目录

```text
tests/case001/
├── README.md
├── project.yaml
├── .gitignore
├── problem/
│   └── source_manifest.yaml
├── expected/
│   ├── acceptance.yaml
│   └── reference_benchmarks.yaml
├── run/
│   ├── W0_project_status.yaml
│   ├── W1_problem_intake.yaml
│   └── G1_agent_admission.yaml
└── review/
    ├── defect_log.yaml
    └── run_log.md
```

## 二进制材料策略

本仓库为公开仓库。参考论文 PDF 不直接提交，只保存：

- 文件名；
- SHA-256；
- 页数；
- 标题；
- 方法摘要；
- 关键报告结果。

原始材料应在本地测试环境中放置于：

```text
tests/case001/local/problem/B题.rar
tests/case001/local/references/B477.pdf
tests/case001/local/references/B226.pdf
tests/case001/local/references/B311.pdf
```

`local/` 已被 `.gitignore` 排除。

## 本轮核心观察指标

1. Workflow 是否能在不调用 Agent 的情况下完成确定性任务；
2. Agent 准入记录是否真实阻断不合格调用；
3. 每个重要结论是否有题面、程序或验证证据；
4. 参考论文之间的分歧是否被识别，而不是被平均或任选；
5. 未读取原始附件时，系统是否会停止而不是猜测；
6. 人工路线决策是否有明确留痕；
7. 后续论文正文是否严格来自成果包和论文蓝图。

## 下一检查点

先解决 RAR 解压与附件读取，然后使用原题面复核 `W1_problem_intake.yaml`。复核通过后，逐问执行 W2-W4；问题四再根据 G1 结果决定是否调用受控路线探索 Agent。
