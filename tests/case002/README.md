# case002 — 2025 CUMCM A 逐问审核案例

本案例验证 Shumo 的“完成一问、审核一问、获批后再进入下一问”工作流。当前只实现问题一；
`review/problem1.paper-review.yaml` 保持 `pending`，因此问题二至问题五均锁定。

原始 PDF、Excel 和 Word 二进制材料位于 gitignored 的 `local/problem/`。仓库只跟踪
`problem/source_manifest.yaml` 中的结构、字节数和 SHA-256，不公开复制用户本地材料。

问题一 revision 2 采用导弹视点下的透视投影：观察平面垂直于导弹—目标中心视线，
烟幕球的切锥在像平面上形成二次曲线；只有完整目标投影被覆盖且烟幕位于每条目标射线前方时，
才计为有效遮蔽。模型建立段只使用符号，参数值与假设分别存放在登记库中。

数值结果复现命令：

```bash
python tests/case002/code/problem1_solver.py \
  --output tests/case002/results/problem1_result.json
```

LaTeX 符号与结构检查：

```bash
python skills/math_modeling/validation/symbolic_latex_validator.py \
  --analysis-tex tests/case002/paper/sections/02_problem_analysis/problem1.tex \
  --model-tex tests/case002/paper/sections/05_model_solution/problem1.tex \
  --problem-name 问题一 \
  --output tests/case002/results/problem1_symbolic_check.json

python tests/case002/code/problem1_paper_check.py \
  --analysis-tex tests/case002/paper/sections/02_problem_analysis/problem1.tex \
  --model-tex tests/case002/paper/sections/05_model_solution/problem1.tex \
  --result tests/case002/results/problem1_result.json \
  --output tests/case002/results/problem1_paper_static_check.json
```

审核门禁检查：

```bash
python skills/math_modeling/validation/problem_review_validator.py \
  --review tests/case002/review/problem1.paper-review.yaml \
  --repo-root .
```

在当前 `pending` 状态下，后一命令应返回退出码 `2`，表示记录有效且门禁按设计关闭。
