%% 完整一体化代码：污水厂 光伏+储能+柔性负荷 协同调度（目标：全年外购最小）
clear; clc; close all;

%% ===================== 1. 读取原始Excel数据 =====================
excel_file = "data_source.xlsx";
if ~exist(excel_file,'file')
    error('找不到文件 data_source.xlsx，请放到Matlab当前工作目录！');
end

% 读取3张工作表：一期+二期光伏叠加、负荷
tab_pv1 = readtable(excel_file,...
    "Sheet","污水处理厂8MWp光伏电站(一期)",...
    "VariableNamingRule","preserve");
tab_pv2 = readtable(excel_file,...
    "Sheet","污水处理厂8MWp光伏电站(二期)",...
    "VariableNamingRule","preserve");
tab_load = readtable(excel_file,...
    "Sheet","负荷数据",...
    "VariableNamingRule","preserve");

% 提取0~23点逐时数据：光伏表前2列(时间、日总发电量)+尾部空列，取列3:26(24列)
raw_pv1 = tab_pv1{:,3:26};
raw_pv2 = tab_pv2{:,3:26};
raw_load = tab_load{:,3:26};

% 空白NaN填充为0
raw_pv1(isnan(raw_pv1)) = 0;
raw_pv2(isnan(raw_pv2)) = 0;
raw_load(isnan(raw_load)) = 0;

% 负荷单位为MW，光伏为kW，统一为kW
raw_load = raw_load * 1000;

% 光伏表365天，负荷表396天(多出2026-07整月)，以光伏天数截齐负荷
day_num = size(raw_pv1,1);
raw_load = raw_load(1:day_num, :);

% 一期+二期光伏叠加，放大容量(光伏约23MW≈×3.8)
PV_scale = 3.8;   % 光伏容量放大系数
P_PV_all = (raw_pv1 + raw_pv2) * PV_scale;
P_PV_all = P_PV_all.';
P_PV_all = P_PV_all(:);

P_L_all = raw_load.';
P_L_all = P_L_all(:);

%% 数据合法性校验
total_h = length(P_L_all);
if total_h ~= day_num * 24
    error('时序错误！天数×24不等于总小时数，检查Excel逐时列是否齐全24列');
end
fprintf('========== 数据载入完成 ==========\n');
fprintf('总天数：%d 天，总小时数：%d h\n',day_num,total_h);
fprintf('光伏最大出力：%.2f kW，负荷峰值：%.2f kW\n',max(P_PV_all),max(P_L_all));

%% ===================== 2. 储能与柔性负荷参数（你按需修改） =====================
E_bat_max = 16000;      % 储能额定容量 kWh (16MWh)
P_bat_max = 8000;       % 储能最大充放电功率 kW (8MW, 2小时储能)
eta_ch = 0.95;          % 充电效率
eta_dis = 0.95;         % 放电效率
SOC_min = 0.2;
SOC_max = 0.9;
SOC_init = 0.5;

flex_ratio = 0.45;      % 柔性负荷占总负荷比例(曝气+提升泵)，总量守恒
flex_max   = 1.00;      % 柔性负荷调节深度上限(100%=满负荷)
flex_min   = 0.65;      % 柔性负荷调节深度下限(65%，曝气工艺下限)

%% ===================== 3. 逐日滚动优化调度主循环 =====================
% 预分配结果数组
total_days = day_num;
SOC_all = [];
Pbat_all = [];
grid_power_all = [];
curtail_all = [];
flex_all = [];

for d = 1:total_days
    idx_start = (d-1)*24 + 1;
    idx_end = d*24;
    Ppv_day = P_PV_all(idx_start:idx_end);
    PL_day = P_L_all(idx_start:idx_end);

    % 调用日内优化函数（目标：单日外购最小）
    [soc_day, pbat_day, pgrid_day, curt_day, flex_day] = daily_opt_dispatch(...
        Ppv_day, PL_day, E_bat_max, P_bat_max, eta_ch, eta_dis,...
        SOC_min, SOC_max, SOC_init, flex_ratio, flex_min, flex_max);

    SOC_all = [SOC_all; soc_day];
    Pbat_all = [Pbat_all; pbat_day];
    grid_power_all = [grid_power_all; pgrid_day];
    curtail_all = [curtail_all; curt_day];
    flex_all = [flex_all; flex_day];

    if mod(d,5) == 0
        fprintf('已完成第 %d / %d 天调度计算\n',d,total_days);
    end
end

%% ===================== 4. 结果汇总输出 =====================
grid_buy_all  = sum(grid_power_all);                      % 全年外购电量
total_load_all= sum(P_L_all);                             % 全年总用电
total_pv_used = total_load_all - grid_buy_all;            % 光伏+储能+柔性覆盖的用电
green_ratio   = total_pv_used / total_load_all * 100;     % 绿电占比%

total_curtail = sum(curtail_all);                         % 全年弃光电量
total_pv_gen  = sum(P_PV_all);                            % 全年光伏总发电
curtail_rate  = total_curtail / total_pv_gen * 100;       % 弃光率%

fprintf('\n========== 全年仿真汇总结果 ==========\n');
fprintf('全年外购电量：%.2f kWh\n', grid_buy_all);
fprintf('全年总用电量：%.2f kWh\n', total_load_all);
fprintf('绿电占比：%.2f %%\n', green_ratio);
fprintf('全年弃光电量：%.2f kWh\n', total_curtail);
fprintf('弃光率：%.2f %%\n', curtail_rate);
fprintf('光伏发电占负荷比：%.2f %%\n', total_pv_gen/total_load_all*100);

%% ===================== 5. 绘图展示（前7天示例） =====================
plot_h = 1:7*24;
figure('Color','w');
subplot(4,1,1);
plot(plot_h, P_PV_all(plot_h),'-r',plot_h,P_L_all(plot_h),'-b');
legend('光伏出力','原负荷');
ylabel('功率(kW)');title('光伏、原负荷时序曲线（前7天）');grid on;

subplot(4,1,2);
plot(plot_h, flex_all(plot_h),'-g');
ylabel('柔性负荷(kW)');title('柔性负荷实际分配（前7天）');grid on;

subplot(4,1,3);
plot(plot_h, Pbat_all(plot_h),'-k');
ylabel('储能功率(kW)');title('储能充放电功率（正放电，负充电）');grid on;

subplot(4,1,4);
plot(plot_h, SOC_all(plot_h),'-m');
ylabel('SOC');xlabel('小时序号');title('储能SOC变化曲线');grid on;

%% ===================== 子函数：单日协同优化调度（线性规划，目标=外购最小） =====================
function [soc_ts, pbat_ts, pgrid_ts, curt_ts, flex_ts] = daily_opt_dispatch(...
    Ppv, PL, Emax, Pmax, eta_ch, eta_dis, socmin, socmax, soc0, flex_ratio, flex_min, flex_max)
H = 24;
% 变量排列：pch(1:24), pdis(25:48), soc(49:72), curt(73:96), pgrid(97:120), flex(121:144)
nvar = 6*H;

% ---- 目标函数：min 当日外购电量 (min sum(pgrid)) ----
f = zeros(nvar,1);
for t = 1:H
    idx_pgrid = 4*H + t;
    f(idx_pgrid) = 1;
end

Aeq = [];
beq = [];

% ---- 上下界 ----
lb = zeros(nvar,1);
ub = inf(nvar,1);
rigid = PL * (1 - flex_ratio);   % 刚性负荷基线(不可平移)
flex_total = sum(PL) * flex_ratio;   % 全天柔性负荷总量(守恒)
for t = 1:H
    idx_pch  = t;
    idx_pdis = H + t;
    idx_soc  = 2*H + t;
    idx_curt = 3*H + t;
    idx_flex = 5*H + t;

    ub(idx_pch)  = Pmax;
    ub(idx_pdis) = Pmax;
    ub(idx_soc)  = socmax;
    lb(idx_soc)  = socmin;
    ub(idx_curt) = Ppv(t);
    % 柔性负荷上下界：调节深度 flex_min~flex_max (65%~100%) × 占比 flex_ratio
    ub(idx_flex) = flex_ratio * flex_max * PL(t);
    lb(idx_flex) = flex_ratio * flex_min * PL(t);
end

% ---- 功率平衡等式：Ppv - curt + pdis - pch + pgrid = rigid + flex ----
for t = 1:H
    row = zeros(1,nvar);
    row(t)         = -1;   % -pch
    row(H+t)       = 1;    % +pdis
    row(3*H + t)   = -1;   % -curt
    row(4*H + t)   = 1;    % +pgrid (外购为正)
    row(5*H + t)   = -1;   % -flex
    Aeq = [Aeq; row];
    beq = [beq; rigid(t) - Ppv(t)];
end

% ---- SOC递推等式：soc(t) - soc(t-1) - (eta_ch*pch - pdis/eta_dis)/Emax = 0 ----
for t = 1:H
    row = zeros(1,nvar);
    row(2*H + t)    = 1;
    row(t)          = -eta_ch/Emax;
    row(H+t)        = 1/(Emax*eta_dis);
    if t == 1
        Aeq = [Aeq; row];
        beq = [beq; soc0];
    else
        row(2*H + t-1) = -1;
        Aeq = [Aeq; row];
        beq = [beq; 0];
    end
end

% ---- 柔性负荷总量守恒：sum(flex) = flex_total ----
row = zeros(1,nvar);
for t = 1:H
    row(5*H + t) = 1;
end
Aeq = [Aeq; row];
beq = [beq; flex_total];

% ---- 求解线性规划 ----
options = optimoptions('linprog','Display','none');
[x,fval,exitflag] = linprog(f,[],[],Aeq,beq,lb,ub,options);
if exitflag ~= 1
    warning('当日优化求解失败，exitflag=%d',exitflag);
end

% ---- 提取结果 ----
pch_ts   = x(1:H);
pdis_ts  = x(H+1:2*H);
soc_ts   = x(2*H+1:3*H);
curt_ts  = x(3*H+1:4*H);
pgrid_ts = x(4*H+1:5*H);
flex_ts  = x(5*H+1:6*H);
pbat_ts  = pdis_ts - pch_ts;   % 正=放电，负=充电
end