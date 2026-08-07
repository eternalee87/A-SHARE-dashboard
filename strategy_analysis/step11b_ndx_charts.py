# -*- coding: utf-8 -*-
"""Step 11b: 策略 vs 纳指100 对比图"""
import os, sys
os.environ["MPLCONFIGDIR"] = os.path.join(os.path.dirname(__file__), ".mplcache")
os.makedirs(os.environ["MPLCONFIGDIR"], exist_ok=True)
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
plt.rcParams["font.sans-serif"] = ["SimHei", "Microsoft YaHei"]
plt.rcParams["axes.unicode_minus"] = False
import pandas as pd
import numpy as np

BASE = os.path.join(os.path.dirname(__file__), "data")
OUT = os.path.join(os.path.dirname(__file__), "out")

daily = pd.read_excel(os.path.join(BASE, "groupby_daily_return.xlsx"))
daily["date"] = pd.to_datetime(daily["str_date"])
daily = daily.sort_values("date").reset_index(drop=True)
r = daily.set_index("date")["daily_return"]

ndx = pd.read_excel(os.path.join(os.path.dirname(os.path.dirname(__file__)),
                                 ".reasonix", "attachments",
                                 "clipboard-20260807-114307.681233-000032.xlsx"))
ndx = ndx[ndx["日期"].notna()].copy()
ndx["日期"] = pd.to_datetime(ndx["日期"], errors="coerce")
ndx = ndx.dropna(subset=["日期", "收盘价(元)"])
ndx = ndx.set_index("日期")["收盘价(元)"].astype(float).sort_index()
ndx = ndx[~ndx.index.duplicated(keep="last")]
ndx_ret = ndx.pct_change()

df = pd.DataFrame({"strat": r, "ndx": ndx_ret.reindex(r.index)}).dropna()
eq = 0.5 * df["strat"] + 0.5 * df["ndx"]

# ---- 图6: 三方案净值与回撤 ----
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(13, 8), sharex=True, gridspec_kw={"height_ratios": [3, 1]})
for k, v, c in [("100%策略", df["strat"], "#c0392b"), ("100%纳指100", df["ndx"], "#2980b9"), ("50/50等权", eq, "#27ae60")]:
    nav = (1 + v).cumprod()
    ax1.plot(df.index, nav, label=k, color=c, lw=1.5)
    dd = nav / nav.cummax() - 1
    ax2.plot(df.index, dd * 100, color=c, lw=1.0, alpha=0.8)
ax1.set_title("三方案净值对比（2017-01 ~ 2026-07，每日再平衡）", fontsize=14)
ax1.legend(fontsize=11); ax1.grid(alpha=0.3); ax1.set_yscale("log")
ax2.set_ylabel("回撤 %"); ax2.grid(alpha=0.3)
ax2.axhline(0, color="black", lw=0.5)
fig.tight_layout()
fig.savefig(os.path.join(OUT, "fig6_ndx_compare.png"), dpi=130)
plt.close(fig)

# ---- 图7: 日收益散点 + 条件标注 ----
fig, ax = plt.subplots(figsize=(8, 7))
ax.scatter(df["ndx"] * 100, df["strat"] * 100, s=6, alpha=0.35, c="#7f8c8d")
# 标注极端区域
ext = df[(df["ndx"] <= df["ndx"].quantile(0.05)) | (df["ndx"] >= df["ndx"].quantile(0.95))]
ax.scatter(ext["ndx"] * 100, ext["strat"] * 100, s=12, alpha=0.8, c="#c0392b", label="NDX 极端涨跌日")
ax.axhline(0, color="gray", lw=0.8); ax.axvline(0, color="gray", lw=0.8)
ax.set_xlabel("纳指100 日收益 %")
ax.set_ylabel("策略 日收益 %")
ax.set_title("策略 vs 纳指100 日收益散点（相关系数 0.059）", fontsize=13)
ax.legend(fontsize=10)
ax.grid(alpha=0.3)
fig.tight_layout()
fig.savefig(os.path.join(OUT, "fig7_ndx_scatter.png"), dpi=130)
plt.close(fig)
print("fig6/fig7 saved")
