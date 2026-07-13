# 问题三 MATLAB 可视化

本目录使用问题三已冻结的 `34` 条等深线平行测线数据生成两类图件。该方案在声明的“南北向等深线平行直线族”内线数最少；不主张在任意曲线或任意方向路线中全局最优。

## 数据与指标

- 测区：东西向 `7408 m`，南北向 `3704 m`；
- 测线：`34` 条，每条长 `3704 m`；
- 总测线长度：`125936 m`（`68` 海里）；
- 海底模型：中心水深 `110 m`、东西向坡度 `1.5°` 的理想平面；
- 数据来源：`tests/case001/run/problem3_independent_baseline.yaml`；
- `problem3_optimal_route.csv` 保存 34 条测线的横坐标和对应水深，便于独立复核。

## 生成文件

- `problem3_surface_route_plan.png` / `.pdf`：水面航线俯视图；
- `problem3_seabed_elevation.png` / `.pdf`：水下高程与测线海底投影图；
- `plot_problem3_optimal_route.m`：MATLAB R2023b 绘图脚本；
- `problem3_optimal_route.csv`：冻结路线数据。

## 复现方法

在 MATLAB 中运行：

```matlab
run('tests/case001/final_delivery/visualizations/problem3/plot_problem3_optimal_route.m')
```

或在仓库根目录执行：

```powershell
matlab -batch "run('tests/case001/final_delivery/visualizations/problem3/plot_problem3_optimal_route.m')"
```

脚本会核验测线数和总长度，并在当前目录覆盖生成 PNG（300 dpi）和矢量 PDF。

## 当前图件的验证说明

权威绘图源为上述 MATLAB 脚本。本次自动化工作区能够检测到 MATLAB R2023b，但其无界面启动服务返回 `ApplicationService client-v1` 错误；因此提交的 PNG/PDF 由同一 CSV、同一坐标系和同一平面高程公式进行等价渲染，以便先完成视觉检查。具备正常 MATLAB 许可与启动服务的环境运行脚本后，可直接覆盖这些图件。
