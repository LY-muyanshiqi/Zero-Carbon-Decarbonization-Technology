# -*- coding: utf-8 -*-
"""
智能调度 全局配置
所有可调参数集中在此，方便改储能/柔性/光伏规模、切换路径。
"""

import os

# ---------------- 路径 ----------------
# 智能调度目录（本文件所在）
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# 模块二目录（父级）
MODULE2_DIR = os.path.dirname(BASE_DIR)
# 项目根目录（公用/公用）
# 目录结构: 公用/公用/模块二/智能调度/config.py
# MODULE2_DIR = .../公用/模块二，PROJECT_ROOT = .../公用/公用
PROJECT_ROOT = os.path.dirname(MODULE2_DIR)

# 光伏×天气 合并数据（光伏预测训练数据）
PV_WEATHER_CSV = os.path.join(PROJECT_ROOT, "5-过程分析数据", "合并数据集_光伏×天气.csv")
# 原始调度数据（光伏一期/二期/负荷，优化层回测用）
DATA_SOURCE_XLSX = os.path.join(MODULE2_DIR, "data_source.xlsx")
# 节点电价文件（含日前/实时电价，单位元/MWh）
PRICE_XLSX = os.path.join(PROJECT_ROOT, "2-原始数据文件", "电力天气整合数据_逐小时.xlsx")

# 输出目录
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ---------------- 光伏 ---------------- 用
# 光伏容量放大系数 = 2.0，对应约 12MW（符合 30 公顷面积约束）
# 面积依据：可装面积约占厂区 25%~30% × 单位装机 0.13 kW/㎡
PV_SCALE = 2.0
# 光伏装机容量上限(kW) = 一期+二期基准(6.08MW) × PV_SCALE
PV_CAPACITY_KW = 6080.0 * PV_SCALE

# ---------------- 储能 ----------------
E_BAT_MAX = 4000.0        # 储能额定容量 kWh (4 MWh，改进版)
P_BAT_MAX = 2000.0        # 储能最大充放电功率 kW (2 MW，2小时储能)
ETA_CH = 0.95             # 充电效率
ETA_DIS = 0.95            # 放电效率
SOC_MIN = 0.2
SOC_MAX = 0.9
SOC_INIT = 0.5

# ---------------- 柔性负荷（设备功率可调） ----------------
# 曝气/泵等设备可变频调节功率。但本方案的定位：柔性负荷默认关闭（负荷刚性），
# 用于"说明储能存在的必要性"——即使曝气可调功率，也解决不了"夜间无光伏"，
# 必须靠储能把白天光伏存下来夜间用。故柔性负荷是可选概念，不追求优化收益。
FLEX_ENABLED = True       # 是否启用柔性负荷错峰（改动2打开，双模式滞回控制曝气下限）
FLEX_MIN = 0.65           # 节能模式曝气下限（常规稳定工况）
FLEX_MAX = 1.00           # 功率调节上限（满负荷）
FLEX_PENALTY = 0.30       # 柔性负荷微惩罚系数（仅 flex_enabled 时生效，抑制无脑开满）

# ---- 双模式滞回 + 安全兜底（专利1迁移，改动2）----
# 安全模式：冲击负荷 或 连续低曝气 时，上调曝气下限保微生物安全
FLEX_MIN_SAFE = 0.80      # 安全模式曝气下限（经验值，收窄调节空间）
FLEX_DOWN_CONT_H = 4      # 连续低曝气判定小时数（贴下限≥N小时 → 切安全模式）
LOAD_SHOCK_RATIO = 0.20   # 冲击负荷波动阈值：日负荷总量相对历史均值波动>20% 判定冲击
HYSTERESIS_DAYS = 3       # 连续重压曝气天数阈值（滞回，防频繁震荡）

# 压曝气成本：给"下调曝气"加正成本，建立"储能充电>下调曝气>弃光"分配优先级。
# 使优化器天然先充满储能、再压曝气、最后才弃光，避免储能闲置而曝气被压惨。
FLEX_DEV_COST = 0.20      # 压曝气偏离成本（>0 启动优先级）

# 曝气总量下调比例（专利1"降低日均曝气总量"的节能本质）：
#   节能模式下 sum(flex) 允许下调到 FLEX_ENERGY_RATIO×基准负荷（分区按需供气、消除末端过量曝气）。
#   冲击/安全模式下应传 1.0（不下调总量）。
FLEX_ENERGY_RATIO = 0.95  # 节能模式最多下调 5% 曝气总量

# ---------------- 并网模式 ----------------
# 自发自用、余电上网：光伏先自用，用不完的余电上网售出
ALLOW_GRID_EXPORT = True  # 是否允许余电上网（True=自发自用余电上网）

# ---------------- 天气/坐标 ----------------
LOCATION_NAME = "zhongshan"
# 中山市大致坐标（中嘉污水厂，中山城区西南部）
LATITUDE = 22.52
LONGITUDE = 113.39

# ---------------- 经济参数（三级电费 + 投资回报率模型） ----------------
# 三级电费：总电费 = 电度电费 + 基本电费(需量) + 力调电费(功率因数)

# ① 电度电费——用户侧分时目录电价（元/kWh）
# 峰平谷时段按附件6运行参数表：高峰10-12/14-19，低谷0-8，尖峰11-12/15-17
PRICE_SELL = 0.453     # 余电上网价：广东燃煤发电基准价 0.453 元/kWh

def tou_price(t):
    # t 为小时 0~23
    if t in [11, 15, 16]:
        return 1.310    # 尖峰 11-12、15-17
    elif t in [10, 14, 17, 18, 19] or t in [12, 13]:
        # 高峰 10-12(即10,11)、14-19(即14~18)；但11是尖峰已截
        return 1.048    # 高峰
    elif t in list(range(0, 8)):
        return 0.262    # 低谷 0-8
    else:
        return 0.655    # 平段


def load_realtime_price():
    """加载广东电力现货节点实时电价，返回 {date: np.array(24)}（元/kWh）。

    读取 PRICE_XLSX 的「节点实时电价_元MWh」列，÷1000 转元/kWh，
    负价 clip 到 0。按天组织成 24 元时长度的数组。
    文件缺失时返回 None（调用方回退到 tou_price）。
    """
    import pandas as pd
    import numpy as np

    if not os.path.exists(PRICE_XLSX):
        return None

    df = pd.read_excel(PRICE_XLSX)
    rt_col = "节点实时电价_元MWh"
    if rt_col not in df.columns:
        rt_col = df.columns[-1]

    ts = pd.to_datetime(df["日期"]) + pd.to_timedelta(df["小时"], unit="h")
    price = df[rt_col].astype(float).clip(lower=0) / 1000.0  # 元/MWh → 元/kWh

    out = {}
    for t, p in zip(ts, price.values):
        d = t.date()
        h = t.hour
        if d not in out:
            out[d] = np.zeros(24)
        out[d][h] = p
    return out


# 数据起点（负荷/光伏数据 2025-07-01 起）
DATA_START_DATE = "2025-07-01"

_realtime_price_cache = None


def price_for_day(day_idx: int):
    """返回第 day_idx 天（从 DATA_START_DATE 起）的 24h 电价数组（元/kWh）。

    优先用真实节点现货价；文件缺失或无该日数据时回退到固定 tou_price。
    结果缓存，避免重复读 Excel。
    """
    import numpy as np
    from datetime import datetime, timedelta

    global _realtime_price_cache
    if _realtime_price_cache is None:
        _realtime_price_cache = load_realtime_price()

    fallback = np.array([tou_price(t) for t in range(24)])

    if _realtime_price_cache is None:
        return fallback

    target_date = (datetime.strptime(DATA_START_DATE, "%Y-%m-%d") + timedelta(days=day_idx)).date()
    return _realtime_price_cache.get(target_date, fallback)


# ② 基本电费（需量）—— 储能削峰的真实收益来源
DEMAND_PRICE = 38.0    # 需量电价 元/kW/月

# ③ 力调电费（功率因数奖惩）—— 固定系数，不影响容量优化
PF_TARGET = 0.90       # 功率因数考核值
PF_PENALTY = 0.01      # 力调费率(奖惩比例) ±1%，对容量规划为固定项

# 多目标权重：目标 = w_cost×分时购电成本 + w_green×外购电量
# w_cost 大→偏经济套利；w_green 大→偏绿电/减碳
W_COST = 1.0    # 分时成本权重
W_GREEN = 1.0   # 绿电(外购电量)权重，可调

# 投资成本（单位：元）
PV_INVEST_PER_KW = 4000.0        # 光伏投资 4.0 元/W = 4000 元/kW = 400 万元/MW
BATTERY_E_INVEST_PER_KWH = 1200.0  # 储能能量投资 1.2 元/Wh = 1200 元/kWh
BATTERY_P_INVEST_PER_KW = 800.0   # 储能功率(PCS等) 约 800 元/kW

# 设备寿命 / 回收期基准
PV_LIFETIME_YEARS = 25      # 光伏寿命 25 年
BATTERY_LIFETIME_YEARS = 10 # 储能寿命 10 年
IRR_TARGET = 0.12           # 目标内部收益率 12%


def print_config():
    """打印关键配置，便于运行前核对。"""
    print("=" * 50)
    print("智能调度配置")
    print("=" * 50)
    print(f"光伏容量放大系数 PV_SCALE = {PV_SCALE} (装机约 {PV_CAPACITY_KW/1000:.1f} MW)")
    print(f"储能: {E_BAT_MAX/1000:.0f} MWh / {P_BAT_MAX/1000:.0f} MW")
    print(f"SOC 范围: {SOC_MIN} ~ {SOC_MAX}, 初值 {SOC_INIT}")
    print(f"柔性负荷: {'启用' if FLEX_ENABLED else '关闭(刚性负荷)'}，功率范围 {FLEX_MIN*100:.0f}%~{FLEX_MAX*100:.0f}%")
    print(f"并网模式: 自发自用 + {'余电上网' if ALLOW_GRID_EXPORT else '否'}")
    print(f"多目标: w_cost×分时成本 + w_green×外购电量 (权重 {W_COST}/{W_GREEN})")
    print("=" * 50)
