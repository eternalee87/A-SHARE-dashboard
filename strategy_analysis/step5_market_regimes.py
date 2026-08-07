# -*- coding: utf-8 -*-
"""Step 5: 市场环境分析 - 牛熊阶段划分 + 策略顺风/逆风期识别"""
import pandas as pd
import numpy as np
import json, os

BASE = os.path.join(os.path.dirname(__file__), "data")
OUT = os.path.join(os.path.dirname(__file__), "out")
os.makedirs(OUT, exist_ok=True)

# ---------- 读取市场数据 ----------
def read_index(path, date_col="日期", close_col="收盘价(元)"):
    xl = pd.ExcelFile(path)
    df = xl.parse(xl.sheet_names[0])
    df = df[df[date_col].notna()]
    df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
    df = df.dropna(subset=[date_col, close_col])
    df = df.set_index(date_col)[close_col].astype(float).sort_index()
    df = df[~df.index.duplicated(keep="last")]
    return df

sh = read_index(os.path.join(BASE, "上证指数日数据.xlsx"))
hs300 = read_index(os.path.join(BASE, "沪深300日数据.xlsx"))
gold = read_index(os.path.join(BASE, "黄金日数据.xlsx"))

# 策略与基准日收益
daily = pd.read_excel(os.path.join(BASE, "groupby_daily_return.xlsx"))
daily["date"] = pd.to_datetime(daily["str_date"])
daily = daily.sort_values("date").reset_index(drop=True)
r = daily.set_index("date")["daily_return"]
rb = daily.set_index("date")["daily_benchmark_return"]

# ---------- 上证指数牛熊阶段划分（用回测区间 2017-2026） ----------
shp = sh.loc["2016-12-01":]
# 高低点识别：用 250 日移动平均 + 从阶段高点的回撤
sh_close = shp
ma250 = sh_close.rolling(250).mean()

# 手工划分关键阶段（基于上证指数的经典牛熊周期 + 数据验证）
# 先打印各关键日期的位置
check_dates = ["2018-01-29", "2019-01-04", "2019-04-08", "2020-03-19", "2021-02-18",
               "2021-12-13", "2022-04-27", "2022-07-05", "2022-10-31", "2023-05-09",
               "2024-02-05", "2024-09-18", "2024-10-08", "2025-04-07", "2026-07-18"]
print("===== 上证指数关键点位 =====")
for d in check_dates:
    if d in sh_close.index:
        print(d, round(sh_close.loc[d], 1))
    else:
        # 找最近
        idx = sh_close.index.searchsorted(pd.Timestamp(d))
        dd = sh_close.index[min(idx, len(sh_close) - 1)]
        print(d, "(nearest", str(dd.date()), ")", round(sh_close.loc[dd], 1))

# ---------- 阶段收益统计 ----------
# 定义阶段（基于上证指数实际走势，2017-2026）
stages = [
    ("2017-01-03", "2018-01-28", "2017 慢牛/结构市（大盘蓝筹）"),
    ("2018-01-29", "2019-01-03", "2018 熊市（去杠杆+贸易战）"),
    ("2019-01-04", "2019-04-30", "2019Q1 春季反弹（牛初）"),
    ("2019-05-01", "2020-03-19", "2019H2-2020Q1 震荡+疫情暴跌（熊末/危机）"),
    ("2020-03-20", "2021-02-18", "2020-2021Q1 牛市（流动性牛）"),
    ("2021-02-19", "2021-12-31", "2021 结构牛转弱（茅指数瓦解）"),
    ("2022-01-01", "2022-10-31", "2022 熊市（俄乌+加息+疫情）"),
    ("2022-11-01", "2023-05-09", "2022Q4-2023Q1 反弹（放开预期）"),
    ("2023-05-10", "2024-02-05", "2023-2024Q1 阴跌（熊末）"),
    ("2024-02-06", "2024-09-18", "2024 震荡磨底（熊末）"),
    ("2024-09-19", "2024-10-08", "2024-09 政策牛爆发"),
    ("2024-10-09", "2025-04-07", "2024Q4-2025Q1 高位震荡（牛市中段）"),
    ("2025-04-08", "2026-07-18", "2025-2026 牛市延续（科技牛？）"),
]

# 上证指数阶段涨跌 + 策略/基准阶段收益
rows = []
for s, e, name in stages:
    sd, ed = pd.Timestamp(s), pd.Timestamp(e)
    # 上证
    sh_seg = sh_close.loc[sd:ed]
    sh_ret = sh_seg.iloc[-1] / sh_seg.iloc[0] - 1 if len(sh_seg) > 1 else np.nan
    sh_maxdd = (sh_seg / sh_seg.cummax() - 1).min() if len(sh_seg) > 1 else np.nan
    # 策略/基准（用日收益复合）
    rs = r.loc[sd:ed]
    rbs = rb.loc[sd:ed]
    strat_ret = (1 + rs).prod() - 1 if len(rs) else np.nan
    bench_ret = (1 + rbs).prod() - 1 if len(rbs) else np.nan
    strat_dd = ((1 + rs).cumprod() / (1 + rs).cumprod().cummax() - 1).min() if len(rs) else np.nan
    bench_dd = ((1 + rbs).cumprod() / (1 + rbs).cumprod().cummax() - 1).min() if len(rbs) else np.nan
    rows.append({"阶段": name, "起": s, "止": e,
                 "上证涨跌": sh_ret, "上证最大回撤": sh_maxdd,
                 "策略收益": strat_ret, "基准(中证500)收益": bench_ret,
                 "策略回撤": strat_dd, "基准回撤": bench_dd,
                 "超额": strat_ret - bench_ret})

stage_df = pd.DataFrame(rows)
print("\n===== 市场阶段 vs 策略表现 =====")
print(stage_df.to_string(index=False))
stage_df.to_csv(os.path.join(OUT, "market_stages.csv"), index=False)

# ---------- 顺风/逆风期识别：滚动120日超额收益 ----------
rel = (1 + r) / (1 + rb) - 1  # 日相对收益（近似）
roll_rel = rel.rolling(120).apply(lambda x: (1 + x).prod() - 1, raw=True)  # 120日累计超额

# 连续顺风/逆风段
def segments_of(sig, above):
    segs = []
    start = None
    for d, v in sig.items():
        cond = v > 0 if above else v < 0
        if cond and start is None:
            start = d
        elif not cond and start is not None:
            segs.append((start, d))
            start = None
    if start is not None:
        segs.append((start, sig.index[-1]))
    return segs

tail = roll_rel.dropna()
pos_segs = segments_of(tail, True)
neg_segs = segments_of(tail, False)

def seg_stats(segs):
    out = []
    for s, e in segs:
        days = (e - s).days
        if days < 30:
            continue
        rs = r.loc[s:e]
        rbs = rb.loc[s:e]
        out.append({"区间": f"{s.date()} ~ {e.date()}", "天数": days,
                    "策略收益": (1 + rs).prod() - 1,
                    "基准收益": (1 + rbs).prod() - 1,
                    "超额": ((1 + rs).prod() / (1 + rbs).prod()) - 1})
    return pd.DataFrame(out)

pos_df = seg_stats(pos_segs)
neg_df = seg_stats(neg_segs)
print("\n===== 顺风期（120日滚动超额 > 0，持续>=30天） =====")
print(pos_df.to_string(index=False))
print("\n===== 逆风期（120日滚动超额 < 0，持续>=30天） =====")
print(neg_df.to_string(index=False))
pos_df.to_csv(os.path.join(OUT, "tailwind_periods.csv"), index=False)
neg_df.to_csv(os.path.join(OUT, "headwind_periods.csv"), index=False)
