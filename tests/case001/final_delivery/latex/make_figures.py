from pathlib import Path
import json, math
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.ticker import MultipleLocator

ROOT = Path(__file__).resolve().parent
FIG = ROOT / 'figures'
FIG.mkdir(exist_ok=True)

plt.rcParams.update({
    'font.family': 'Noto Sans CJK JP',
    'font.size': 9,
    'axes.unicode_minus': False,
    'pdf.fonttype': 42,
    'ps.fonttype': 42,
})

# Problem 1
x = np.array([-800,-600,-400,-200,0,200,400,600,800], dtype=float)
depth = np.array([
    90.9487372553, 85.7115529415, 80.4743686277,
    75.2371843138, 70.0, 64.7628156862,
    59.5256313723, 54.2884470585, 49.0512627447,
])
width = np.array([
    315.8133282933, 297.6275605856, 279.4417928778,
    261.2560251701, 243.0702574623, 224.8844897546,
    206.6987220469, 188.5129543391, 170.3271866314,
])
overlap = np.array([
    np.nan, 35.6954425973, 31.5105719971, 26.7430921762,
    21.2622360542, 14.8949375068, 7.40722359197,
    -1.52516372897, -12.3649661151,
])

fig, ax = plt.subplots(figsize=(5.9,3.2))
ax.plot(x, depth, marker='o', linewidth=1.4, label='水深')
ax.set_xlabel('距中心位置 / m')
ax.set_ylabel('水深 / m')
ax.grid(True, linewidth=.35, alpha=.5)
ax.legend(frameon=False)
fig.tight_layout()
fig.savefig(FIG/'problem1_depth.pdf', bbox_inches='tight')
plt.close(fig)

fig, ax = plt.subplots(figsize=(5.9,3.2))
ax.plot(x, width, marker='s', linewidth=1.4, label='覆盖宽度')
ax.set_xlabel('距中心位置 / m')
ax.set_ylabel('覆盖宽度 / m')
ax.grid(True, linewidth=.35, alpha=.5)
ax.legend(frameon=False)
fig.tight_layout()
fig.savefig(FIG/'problem1_width.pdf', bbox_inches='tight')
plt.close(fig)

fig, ax = plt.subplots(figsize=(5.9,3.2))
ax.axhspan(10,20, alpha=.15, label='要求区间 10%--20%')
ax.axhline(0, linewidth=.8)
ax.plot(x[1:], overlap[1:], marker='o', linewidth=1.4, label='有向重叠率')
ax.set_xlabel('当前测线距中心位置 / m')
ax.set_ylabel('重叠率 / %')
ax.grid(True, linewidth=.35, alpha=.5)
ax.legend(frameon=False, loc='best')
fig.tight_layout()
fig.savefig(FIG/'problem1_overlap.pdf', bbox_inches='tight')
plt.close(fig)

# Problem 2
betas = np.array([0,45,90,135,180,225,270,315])
dists = np.array([0,0.3,0.6,0.9,1.2,1.5,1.8,2.1])
mat = np.array([
[415.692,466.091,516.490,566.889,617.288,667.686,718.085,768.484],
[416.192,451.872,487.552,523.232,558.912,594.592,630.273,665.953],
[416.692]*8,
[416.192,380.511,344.831,309.151,273.471,237.791,202.110,166.430],
[415.692,365.293,314.894,264.496,214.097,163.698,113.299,62.900],
[416.192,380.511,344.831,309.151,273.471,237.791,202.110,166.430],
[416.692]*8,
[416.192,451.872,487.552,523.232,558.912,594.592,630.273,665.953],
])
fig, ax = plt.subplots(figsize=(6.3,4.2))
im = ax.imshow(mat, aspect='auto', origin='upper')
ax.set_xticks(np.arange(len(dists)), [f'{v:g}' for v in dists])
ax.set_yticks(np.arange(len(betas)), [f'{v:g}' for v in betas])
ax.set_xlabel('距海域中心距离 / 海里')
ax.set_ylabel('测线方向角 β / °')
cb = fig.colorbar(im, ax=ax, shrink=.86)
cb.set_label('覆盖宽度 / m')
for i in range(mat.shape[0]):
    for j in range(mat.shape[1]):
        ax.text(j,i,f'{mat[i,j]:.0f}',ha='center',va='center',fontsize=6.8,
                color='white' if mat[i,j] < 250 or mat[i,j] > 650 else 'black')
fig.tight_layout()
fig.savefig(FIG/'problem2_heatmap.pdf', bbox_inches='tight')
plt.close(fig)

# Problem 3 layout
positions = np.array([
    -3345.478207, -2750.979520, -2203.316098, -1698.798208,
    -1234.026796, -805.870591, -411.445007, -48.092707,
    286.634296, 594.991135, 879.055280, 1140.740537,
    1381.809940, 1603.887627, 1808.469789, 1996.934741,
    2170.552215, 2330.491912, 2477.831383, 2613.563286,
    2738.602080, 2853.790179, 2959.903633, 3057.657350,
    3147.709922, 3230.668052, 3307.090648, 3377.492588,
    3442.348185, 3502.094386, 3557.133715, 3607.836985,
    3654.545795, 3697.574833,
])
fig, ax = plt.subplots(figsize=(6.3,3.2))
for q in positions:
    ax.plot([q/1852,q/1852],[0,2],linewidth=.65)
ax.set_xlim(-2,2)
ax.set_ylim(0,2)
ax.set_xlabel('东西向坐标 / 海里')
ax.set_ylabel('南北向坐标 / 海里')
ax.set_aspect('equal', adjustable='box')
ax.grid(True, linewidth=.25, alpha=.35)
fig.tight_layout()
fig.savefig(FIG/'problem3_layout.pdf', bbox_inches='tight')
plt.close(fig)

# Problem 4 route station representation
import csv
with (ROOT / 'data/problem4_route_station_matrix.csv').open(
    encoding='utf-8-sig', newline=''
) as handle:
    route_rows = list(csv.DictReader(handle))
y_stations = np.arange(0.0, 5.0 + 0.5, 0.5)
y_dense = np.linspace(0.0, 5.0, 201)
fig, ax = plt.subplots(figsize=(5.3,6.2))
for row in route_rows:
    xs = np.array([float(row[f'y_{v:.1f}_NM_x_NM']) for v in y_stations])
    x_dense = np.interp(y_dense, y_stations, xs)
    ax.plot(x_dense, y_dense, linewidth=.45)
ax.set_xlim(0,4)
ax.set_ylim(0,5)
ax.set_xlabel('东西向坐标 / 海里')
ax.set_ylabel('南北向坐标 / 海里')
ax.set_aspect('equal', adjustable='box')
ax.grid(True, linewidth=.25, alpha=.35)
fig.tight_layout()
fig.savefig(FIG/'problem4_routes.pdf', bbox_inches='tight')
plt.close(fig)

# Candidate comparison
names = ['A','B','C','C-05']
lengths = np.array([620420.0,703760.0,576755.7023466643,576726.6355123592])/1000
excess = np.array([369055.8064516127,452776.95999999956,339673.0975448946,339556.4072993089])/1000
idx=np.arange(len(names)); w=.36
fig, ax = plt.subplots(figsize=(6.1,3.5))
ax.bar(idx-w/2,lengths,w,label='测线总长度')
ax.bar(idx+w/2,excess,w,label='重叠率超过 20% 的长度')
ax.set_xticks(idx,names)
ax.set_ylabel('长度 / km')
ax.set_xlabel('候选方案')
ax.grid(axis='y', linewidth=.35, alpha=.5)
ax.legend(frameon=False)
fig.tight_layout()
fig.savefig(FIG/'problem4_comparison.pdf', bbox_inches='tight')
plt.close(fig)

# Sensitivity
n = np.array([30, 50, 70])
uncovered = np.array([0.0, 0.0, 0.04081632653061224])
multi = np.array([48.77777777777778, 48.0, 48.38775510204081])
fig, ax = plt.subplots(figsize=(5.9,3.3))
ax.plot(n,uncovered,marker='o',label='漏测面积比例')
ax.set_xlabel('评估网格规模 n×n')
ax.set_ylabel('漏测面积比例 / %')
ax.xaxis.set_major_locator(MultipleLocator(20))
ax.grid(True, linewidth=.35, alpha=.5)
ax.legend(frameon=False)
fig.tight_layout()
fig.savefig(FIG/'problem4_sensitivity.pdf', bbox_inches='tight')
plt.close(fig)

# Curvature distribution
radii=np.array([float(row['minimum_curvature_radius_m']) for row in route_rows])
fig, ax = plt.subplots(figsize=(5.9,3.3))
ax.plot(np.arange(1,len(radii)+1),radii,linewidth=1.1)
ax.axhline(radii.min(),linestyle='--',linewidth=.8,label=f'最小值 = {radii.min():.3f} m')
ax.set_xlabel('测线编号')
ax.set_ylabel('最小曲率半径 / m')
ax.grid(True, linewidth=.35, alpha=.5)
ax.legend(frameon=False)
fig.tight_layout()
fig.savefig(FIG/'problem4_curvature.pdf', bbox_inches='tight')
plt.close(fig)

print('generated', sorted(p.name for p in FIG.glob('*.pdf')))
