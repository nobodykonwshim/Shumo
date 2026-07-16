# case002 — 2025 CUMCM A 逐问审核案例

本案例验证 Shumo 的“完成一问、审核一问、获批后再进入下一问”工作流。当前只实现问题一；
`review/problem1.paper-review.yaml` 保持 `pending`，因此问题二至问题五均锁定。

原始 PDF、Excel 和 Word 二进制材料位于 gitignored 的 `local/problem/`。仓库只跟踪
`problem/source_manifest.yaml` 中的结构、字节数和 SHA-256，不公开复制用户本地材料。

问题一复现命令：

```bash
python tests/case002/code/problem1_solver.py \
  --output tests/case002/results/problem1_result.json
```

审核门禁检查：

```bash
python skills/math_modeling/validation/problem_review_validator.py \
  --review tests/case002/review/problem1.paper-review.yaml \
  --repo-root .
```

在当前 `pending` 状态下，后一命令应返回退出码 `2`，表示记录有效且门禁按设计关闭。
