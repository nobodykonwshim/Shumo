%% Problem 3: surface routes and idealized seabed elevation
% Reproduces the frozen 34-line contour-parallel solution for case001.
% Run from any directory with MATLAB R2020a or later:
%   matlab -batch "run('.../plot_problem3_optimal_route.m')"

clear; close all; clc;

scriptDir = fileparts(mfilename('fullpath'));
dataFile = fullfile(scriptDir, 'problem3_optimal_route.csv');
route = readtable(dataFile);

% Frozen problem parameters (SI units).
northSouthLength = 3704;
west = -3704;
east = 3704;
south = -northSouthLength / 2;
north = northSouthLength / 2;
centerDepth = 110;
slope = deg2rad(1.5);
xLine = route.x_from_center_m;

assert(height(route) == 34, 'Expected 34 survey lines.');
assert(abs(height(route) * northSouthLength - 125936) < 1e-9, ...
    'Unexpected total route length.');

% Consistent typography and color palette.
fontName = 'Microsoft YaHei';
routeColor = [0.00, 0.32, 0.75];
boundaryColor = [0.12, 0.12, 0.12];

%% Figure 1: water-surface plan view
fig1 = figure('Color', 'w', 'Position', [80, 80, 1180, 700]);
ax1 = axes(fig1); hold(ax1, 'on'); box(ax1, 'on');
rectangle(ax1, 'Position', [west, south, east-west, north-south], ...
    'EdgeColor', boundaryColor, 'LineWidth', 1.8, 'LineStyle', '--');
for k = 1:numel(xLine)
    plot(ax1, [xLine(k), xLine(k)], [south, north], '-', ...
        'Color', routeColor, 'LineWidth', 1.35);
end
plot(ax1, xLine(1), north, 'o', 'MarkerFaceColor', [0.12, 0.65, 0.28], ...
    'MarkerEdgeColor', 'w', 'MarkerSize', 8);
plot(ax1, xLine(end), north, 'o', 'MarkerFaceColor', [0.86, 0.20, 0.18], ...
    'MarkerEdgeColor', 'w', 'MarkerSize', 8);
text(ax1, xLine(1), north+100, '第1条', 'HorizontalAlignment', 'center', ...
    'FontName', fontName, 'FontSize', 10);
text(ax1, xLine(end)-60, north+100, '第34条', 'HorizontalAlignment', 'right', ...
    'FontName', fontName, 'FontSize', 10);
xlabel(ax1, '东西向坐标 x / m', 'FontName', fontName);
ylabel(ax1, '南北向坐标 y / m', 'FontName', fontName);
title(ax1, {'问题三当前最优方案：水面航线俯视图', ...
    '34条等深线平行测线，总长度 125936 m'}, ...
    'FontName', fontName, 'FontWeight', 'bold');
axis(ax1, 'equal'); xlim(ax1, [west-250, east+250]); ylim(ax1, [south-250, north+300]);
grid(ax1, 'on'); ax1.GridAlpha = 0.18; ax1.FontName = fontName;
annotation(fig1, 'textbox', [0.71, 0.12, 0.22, 0.13], ...
    'String', sprintf('测区：7408 m × 3704 m\n线数：34\n单线长度：3704 m'), ...
    'FitBoxToText', 'on', 'BackgroundColor', 'w', 'EdgeColor', [0.6 0.6 0.6], ...
    'FontName', fontName, 'FontSize', 10);
exportgraphics(fig1, fullfile(scriptDir, 'problem3_surface_route_plan.png'), 'Resolution', 300);
exportgraphics(fig1, fullfile(scriptDir, 'problem3_surface_route_plan.pdf'), 'ContentType', 'vector');

%% Figure 2: seabed elevation and survey-line projections
x = linspace(west, east, 241);
y = linspace(south, north, 121);
[X, Y] = meshgrid(x, y);
depth = centerDepth - X .* tan(slope);
Z = -depth; % Elevation relative to the water surface (z=0).

fig2 = figure('Color', 'w', 'Position', [100, 70, 1250, 760]);
ax2 = axes(fig2); hold(ax2, 'on'); box(ax2, 'on');
surf(ax2, X, Y, Z, depth, 'EdgeColor', 'none', 'FaceAlpha', 0.96);
colormap(ax2, turbo); cb = colorbar(ax2);
cb.Label.String = '水深 / m'; cb.Label.FontName = fontName;
for k = 1:numel(xLine)
    zLine = -(centerDepth - xLine(k) * tan(slope));
    plot3(ax2, [xLine(k), xLine(k)], [south, north], [zLine, zLine] + 1.0, ...
        'Color', [1.00, 0.92, 0.12], 'LineWidth', 1.15);
end
contour3(ax2, X, Y, Z, 12, 'k-', 'LineWidth', 0.45);
xlabel(ax2, '东西向坐标 x / m', 'FontName', fontName);
ylabel(ax2, '南北向坐标 y / m', 'FontName', fontName);
zlabel(ax2, '海底高程 z / m（水面为0）', 'FontName', fontName);
title(ax2, {'问题三理想海域水下高程图', ...
    '黄色线为34条测线在海底地形上的投影，黑线为等深线'}, ...
    'FontName', fontName, 'FontWeight', 'bold');
view(ax2, 42, 27); axis(ax2, 'tight'); grid(ax2, 'on');
ax2.GridAlpha = 0.16; ax2.FontName = fontName;
exportgraphics(fig2, fullfile(scriptDir, 'problem3_seabed_elevation.png'), 'Resolution', 300);
exportgraphics(fig2, fullfile(scriptDir, 'problem3_seabed_elevation.pdf'), 'ContentType', 'vector');

fprintf('Generated Problem-3 figures in: %s\n', scriptDir);
