# case001：多波束测线问题能力验证案例

## 案例定位

`case001` 是 Shumo 数学建模 Skill 的真实案例验证夹具，不是当前开发周期的最终产品。

它的作用是暴露通用能力缺口、提供最小真实证据，并验证通用模块能否在复杂题目上运行。案例本身可以保持 `partial`，只要本轮目标能力已经完成抽象、测试和记录。

## 本轮验证目标

本案例已经用于验证：

1. Workflow-first 分阶段建模；
2. Agent 准入、预算和人工决策点；
3. 参考资料隔离与证据留痕；
4. XLSX 结构化网格读取；
5. 独立覆盖、重叠和边界评估；
6. 显式直线与 Bézier 路线几何；
7. 切向连续与有限曲率验证；
8. GitHub Actions 可复现证据生成；
9. 从案例实现提炼通用 Skill 的停止与晋升规则。

通用能力清单见：

```text
skills/math_modeling/CAPABILITY_REGISTRY.yaml
```

案例转 Skill 的规则见：

```text
skills/math_modeling/support/CASE_TO_SKILL_PROMOTION.md
```

## 当前状态

```text
案例状态：partial / demonstration_complete
Skill 提炼状态：完成本轮抽象
问题 1-3：保留已有案例证据
问题 4：保留为未最终选择的案例研究
PR 状态：Draft
合并授权：否
```

问题 4 中对候选 C 的有限曲率改进已经证明以下通用能力可行：

- 原始折线失败不等于路线族失败；
- 路线需要显式、版本化的几何表达；
- 改进后的候选必须重新进行独立空间评估；
- 采样覆盖结论必须包含敏感性说明；
- 评估器不得自动作最终路线选择。

继续压缩某一个 C 变体的长度或修复局部漏测，只会提高本案例成绩，目前不会产生新的通用能力。因此这部分工作暂停，不作为本轮 Skill 建立的阻塞项。

## 本轮提炼出的 Skill 资产

```text
skills/math_modeling/
├── README.md
├── CAPABILITY_REGISTRY.yaml
├── workflows/README.md
├── orchestration/agent_gate.py
├── evaluators/
│   ├── xlsx_depth_grid.py
│   ├── spatial_coverage.py
│   └── route_feasibility.py
├── geometry/route_geometry.py
└── support/
    ├── REFERENCE_ISOLATION_PROTOCOL.md
    └── CASE_TO_SKILL_PROMOTION.md
```

通用单元测试位于：

```text
tests/evaluators/
tests/orchestration/
```

## 案例目录责任

`tests/case001/` 只保存：

- 题目和附件清单；
- 案例特有假设、参数和候选；
- 人工路线决策；
- 运行证据；
- 案例限制和失败记录。

任何能够脱离 `case001` 描述的能力，应迁移或抽象到 `skills/math_modeling/`，并增加通用测试。

## 二进制材料策略

本仓库为公开仓库，原始题面、附件和参考论文保存在本地目录，不直接提交：

```text
tests/case001/local/problem/
tests/case001/local/references/
```

`local/` 已被 `.gitignore` 排除。公开仓库仅保存哈希、结构说明和可复现命令。

## 下一开发主线

下一阶段不继续追逐问题 4 的单一最优路线，而是按能力注册表处理高优先级 Skill 缺口：

1. 建立通用 `model_spec` schema；
2. 为能力注册表和证据路径增加机器校验；
3. 建立通用敏感性测试声明与验收规则；
4. 建立论文蓝图一致性验证器。

如未来单独启动“完成 CUMCM-2023-B 最终解”的项目，应作为新的案例求解目标和独立决策，而不是隐含延长当前 Skill 开发周期。
