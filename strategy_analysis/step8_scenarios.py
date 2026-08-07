# -*- coding: utf-8 -*-
"""Step 8: 优化情景模拟 - 加入A股资产 + 趋势过滤的静态混合测算"""
import pandas as pd
import numpy as np
import json, os

BASE = os.path.join(os.path.dirname(__file__), "data")
OUT = os.path.join(os.path.dirname(__file__), "out")

daily = pd.read_excel(os.path.join(BASE, "groupby_daily_return.xlsx"))
daily["date"] = pd.to_datetime(daily["str_date"])
daily = daily.sort_values("date").reset_index(drop=True)
r = daily.set_index("date")["daily_return"]
rb = daily.set_index("date")["daily_benchmark_return"]

# 沪深300 日收益（用户提供数据）
xl = pd.ExcelFile(os.path.join(BASE, "沪深300日数据.xlsx"))
hs = xl.parse(xl.sheet_names[0])
hs = hs[hs["日期"].notna()].copy()
hs["日期"] = pd.to_datetime(hs["日期"], errors="coerce")
hs = hs.dropna(subset=["日期", "收盘价(元)"])
hs = hs.set_index("日期")["收盘价(元)"].astype(float).sort_index()
hs = hs[~hs.index.duplicated(keep="last")]
hs_ret = hs.pct_change().dropna()

# 对齐到策略交易日
aligned = pd.DataFrame({"strat": r, "hs300": hs_ret.reindex(r.index)}).dropna()
print("对齐交易日数:", len(aligned))

# ---------- 情景1: 静态混合 80%策略 + 20%沪深300 ----------
def metrics(ret, name):
    cum = (1 + ret).cumprod()
    ann = cum.iloc[-1] ** (252 / len(ret)) - 1
    vol = ret.std(ddof=1) * np.sqrt(252)
    sharpe = ann / vol
    dd = (cum / cum.cummax() - 1).min()
    return {"情景": name, "累计收益": cum.iloc[-1] - 1, "年化": ann, "波动": vol,
            "夏普(rf=0)": sharpe, "最大回撤": dd}

base = metrics(aligned["strat"], "原策略")
mix20 = metrics(0.8 * aligned["strat"] + 0.2 * aligned["hs300"], "80%策略+20%沪深300")
mix40 = metrics(0.6 * aligned["strat"] + 0.4 * aligned["hs300"], "60%策略+40%沪深300")

# ---------- 情景2: 趋势过滤的A股仓位（上证>MA250 时持20%沪深300，否则0） ----------
sh = pd.read_excel(os.path.join(BASE, "上证指数日数据.xlsx"))
sh = sh[sh["日期"].notna()].copy()
sh["日期"] = pd.to_datetime(sh["日期"], errors="coerce")
sh = sh.dropna(subset=["日期", "收盘价(元)"])
sh = sh.set_index("日期")["收盘价(元)"].astype(float).sort_index()
sh = sh[~sh.index.duplicated(keep="last")]
ma250 = sh.rolling(250).mean()
trend = (sh > ma250).reindex(aligned.index).fillna(False)

w = trend.astype(float) * 0.2
mix_trend = aligned["strat"] * (1 - w) + aligned["hs300"] * w
mt = metrics(mix_trend, "原策略+趋势过滤A股(0/20%)")

# ---------- 情景3: 熊市防御开关（上证<MA250时策略整体降仓至60%） ----------
# 简化：risk-off 时组合 = 0.6×策略 + 0.4×现金
mix_riskoff = aligned["strat"] * (1 - 0.4 * (~trend).astype(float))
mr = metrics(mix_riskoff, "原策略+熊市降仓40%")

print("\n===== 情景模拟 =====")
res = pd.DataFrame([base, mix20, mix40, mt, mr]).set_index("情景")
print(res.to_string())
res.to_csv(os.path.join(OUT, "scenario_sim.csv"))

# 各情景在关键阶段的表现对比
stages = [("2018-01-29", "2019-01-03", "2018熊市"), ("2019-01-04", "2019-04-30", "2019Q1反弹"),
          ("2020-03-20", "2021-02-18", "2020-2021牛市"), ("2022-01-01", "2022-10-31", "2022熊市"),
          ("2024-09-19", "2024-10-08", "2024-09政策牛"), ("2025-04-08", "2026-07-18", "2025-2026牛市")]
print("\n===== 关键阶段收益对比 =====")
for s, e, name in stages:
    sd, ed = pd.Timestamp(s), pd.Timestamp(e)
    seg = aligned.loc[sd:ed]
    if len(seg) == 0:
        continue
    sr = (1 + seg["strat"]).prod() - 1
    m20 = (1 + (0.8 * seg["strat"] + 0.2 * seg["hs300"])).prod() - 1
    w_ = trend.loc[sd:ed]
    mtr = (1 + (seg["strat"] * (1 - w_ * 0.2) + seg["hs300"] * w_ * 0.2)).prod() - 1
    print(f"{name:<12} 原策略 {sr*100:7.2f}% | 静态20%A股 {m20*100:7.2f}% | 趋势过滤A股 {mtr*100:7.2f}%")

# ---------- 交易成本影响 ----------
# 总交易成本 301万，平均净资产约 (1000万+2630万)/2 ≈ 1815万
cost = 3012547
avg_nav = (10000000 + 26296522) / 2
print("\n交易成本 301.3万 / 平均净资产 %.0f万 = %.2f%%（全期）" % (avg_nav / 10000, cost / avg_nav * 100))
print("年化成本拖累 ≈ %.2f%%/年" % (cost / avg_nav * 100 / 9.55))
