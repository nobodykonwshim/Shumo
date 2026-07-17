# 逐问论文审核门禁

## 1. 适用场景

当用户要求“完成一问、审核一问、通过后再进入下一问”时，项目必须启用
`question_delivery.mode: sequential_review`。该门禁位于当前问题的 W8 交付检查与下一问题的 W0
之间，不替代建模、验证或论文蓝图门槛。

## 2. 核心约束

1. 问题顺序由项目配置中的 `question_delivery.problem_order` 唯一确定。
2. 当前问题必须形成模型规格、论文蓝图、论文稿和结果证据；这些产物均以仓库相对路径和
   SHA-256 写入审核记录。
3. 审核状态只有 `pending`、`changes_requested`、`approved` 三种。
4. `pending` 与 `changes_requested` 必须停止，不得创建或修改下一问题的建模、结果或论文产物。
5. `approved` 仅对记录中绑定的 revision 和产物哈希有效；任一产物变化后，必须增加 revision、
   更新哈希并将状态重置为 `pending`。
6. 第 \(k\) 问获批前，第 \(k+1\) 问不得获批；验证器会检查前序审核记录。
7. 审核者的数学判断和表达取舍属于人工权力，验证器只证明顺序、状态、路径与哈希一致。

## 3. 最小记录

记录应通过 `specs/problem_review.schema.json`，推荐路径为：

```text
<project>/review/problemX.paper-review.yaml
```

示例见 `specs/problem_review.example.yaml`。机器检查命令：

```bash
python skills/math_modeling/validation/problem_review_validator.py \
  --review <project>/review/problemX.paper-review.yaml \
  --repo-root .
```

退出码约定：

- `0`：记录有效且门禁已打开；
- `2`：记录有效但仍待审核或要求修改，门禁正常关闭；
- `1`：记录、顺序、路径或哈希无效。

## 4. 工作流动作

```text
当前问题建模与验证
→ 冻结 model spec 与结果
→ 冻结 paper blueprint 与 LaTeX
→ 写入哈希并设为 pending
→ 用户审核
   ├─ changes_requested：修改产物、revision + 1、重置 pending
   └─ approved：验证哈希与前序状态，通过后才进入下一问
```

审核稿可以是单节 LaTeX，不要求在每一轮生成整篇论文。项目最终交付时仍须执行完整论文的
格式、编号、引用与附件一致性检查。
