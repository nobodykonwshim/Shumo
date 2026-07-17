# case002 — 2025 CUMCM A 逐问审核案例

本案例验证 Shumo 的“完成一问、审核一问、获批后再进入下一问”工作流。当前只实现问题一；
`review/problem1.paper-review.yaml` 保持 `pending`，因此问题二至问题五均锁定。

原始 PDF、Excel 和 Word 二进制材料位于 gitignored 的 `local/problem/`。仓库只跟踪
`problem/source_manifest.yaml` 中的结构、字节数和 SHA-256，不公开复制用户本地材料。

问题一 revision 3 仅采用圆柱视轮廓边缘线段判别法。导弹与圆柱轴线确定竖直径向平面，
目标视轮廓由上底面背向圆弧、下底面朝向圆弧以及两条精确侧切母线组成。程序对这些边缘点
计算烟幕球心到“导弹—边缘点”闭线段的最短距离，并以最大距离不超过烟幕半径作为完整遮蔽
判据。当前求解不建立投影平面，也不离散完整圆柱表面。模型建立段只使用符号，参数值与假设
分别存放在登记库中。

## 在 VS Code 中直接运行

下载并解压本分支后，用 VS Code 打开仓库根目录，并安装微软官方 Python 扩展。首次运行时执行：

1. 按 `Ctrl+Shift+P`，选择 `Tasks: Run Task`；
2. 选择 `2025A 问题一：首次安装并运行`；
3. 后续可直接按 `F5`，选择 `2025A 问题一：运行边缘线段遮蔽仿真`。

也可以打开 `tests/case002/code/problem1_solver.py`，点击 VS Code 右上角的
“Run Python File”。程序会根据自身文件位置自动定位参数库，不要求终端当前目录位于仓库根目录。

运行后自动生成：

- `tests/case002/results/problem1_result.json`：完整数值结果和验证信息；
- `tests/case002/results/problem1_simulation.csv`：烟幕有效期内按时间采样的事件函数；
- `tests/case002/figures/problem1_occlusion_simulation.png`：最大视线段距离与烟幕半径仿真图。

数值结果也会在 VS Code 终端中按小数点后六位输出。程序只离散圆柱视轮廓；对于每条
“导弹—轮廓点”闭视线线段，球心最短距离由截断正交投影解析计算，不在线段内部取点。

## 命令行复现

安装依赖：

```bash
python -m pip install -r tests/case002/code/requirements.txt
```

直接运行，无需命令行参数：

```bash
python tests/case002/code/problem1_solver.py
```

可选参数包括 `--simulation-step`、`--show-figure`、`--no-figure`、`--output`、
`--simulation-csv` 和 `--simulation-figure`。

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
  --repo-root . \
  --output tests/case002/results/problem1_paper_static_check.json
```

审核门禁检查：

```bash
python skills/math_modeling/validation/problem_review_validator.py \
  --review tests/case002/review/problem1.paper-review.yaml \
  --repo-root .
```

在当前 `pending` 状态下，后一命令应返回退出码 `2`，表示记录有效且门禁按设计关闭。
