# -*- coding: utf-8 -*-
"""Step 9: 生成分析图表"""
import os, sys
os.environ["MPLCONFIGDIR"] = os.path.join(os.path.dirname(__file__), ".mplcache")
os.makedirs(os.environ["MPLCONFIGDIR"], exist_ok=True)
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib"))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import pandas as pd
import numpy as np

plt.rcParams["font.sans-serif"] = ["SimHei", "Microsoft YaHei"]
plt.rcParams["axes.unicode_minus"] = False

BASE = os.path.join(os.path.dirname(__file__), "data")
OUT = os.path.join(os.path.dirname(__file__), "out")
os.makedirs(OUT, exist_ok=True)

daily = pd.read_excel(os.path.join(BASE, "groupby_daily_return.xlsx"))
daily["date"] = pd.to_datetime(daily["str_date"])
daily = daily.sort_values("date").reset_index(drop=True)

# ============ 图1: 净值与回撤 ============
nav = (1 + daily["daily_return"]).cumprod()
navb = (1 + daily["daily_benchmark_return"]).cumprod()
dd = nav / nav.cummax() - 1
ddb = navb / navb.cummax() - 1

fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(13, 8), sharex=True,
                               gridspec_kw={"height_ratios": [3, 1]})
ax1.plot(daily["date"], nav, label="策略净值", color="#c0392b", lw=1.8)
ax1.plot(daily["date"], navb, label="中证500（基准）", color="#7f8c8d", lw=1.2)
ax1.axhline(1.0, color="gray", lw=0.6, ls="--")
ax1.set_title("策略净值 vs 基准（2017-01 ~ 2026-07）", fontsize=14)
ax1.legend(loc="upper left", fontsize=11)
ax1.grid(alpha=0.3)
ax1.set_ylabel("净值")

ax2.fill_between(daily["date"], dd * 100, 0, color="#c0392b", alpha=0.5, label="策略回撤")
ax2.fill_between(daily["date"], ddb * 100, 0, color="#7f8c8d", alpha=0.35, label="基准回撤")
ax2.set_ylabel("回撤 %")
ax2.legend(loc="lower left", fontsize=10)
ax2.grid(alpha=0.3)
fig.tight_layout()
fig.savefig(os.path.join(OUT, "fig1_nav_drawdown.png"), dpi=130)
plt.close(fig)

# ============ 图2: 月度收益热力图 ============
monthly = pd.read_excel(os.path.join(BASE, "groupby_month_return.xlsx"))
monthly["year"] = pd.to_datetime(monthly["str_mmyy"], format="%B %Y").dt.year
monthly["month"] = pd.to_datetime(monthly["str_mmyy"], format="%B %Y").dt.month
heat = monthly.pivot_table(index="year", columns="month", values="monthly_return")

fig, ax = plt.subplots(figsize=(13, 5.5))
im = ax.imshow(heat.values * 100, cmap="RdYlGn", vmin=-8, vmax=8, aspect="auto")
ax.set_xticks(range(12)); ax.set_xticklabels([f"{m}月" for m in range(1, 13)])
ax.set_yticks(range(len(heat))); ax.set_yticklabels(heat.index)
for i in range(heat.shape[0]):
    for j in range(heat.shape[1]):
        v = heat.values[i, j] * 100
        if not np.isnan(v):
            ax.text(j, i, f"{v:+.1f}", ha="center", va="center", fontsize=8,
                    color="white" if abs(v) > 5 else "black")
ax.set_title("策略月度收益热力图（%）", fontsize=14)
fig.colorbar(im, ax=ax, label="月收益 %")
fig.tight_layout()
fig.savefig(os.path.join(OUT, "fig2_monthly_heatmap.png"), dpi=130)
plt.close(fig)

# ============ 图3: 持仓类别权重演变 ============
tgt = pd.read_excel(os.path.join(BASE, "df_target_percent.xlsx"))
tgt["datetime"] = pd.to_datetime(tgt["datetime"])
tgt = tgt[tgt["percent"] > 1e-9].copy()

def cat(code):
    n = code.split(".")[0]
    if n in ("511010", "511220"): return "债券(国债/城投)"
    if n == "511380": return "可转债"
    if n == "518880": return "黄金"
    if n in ("513500", "513100", "513030", "513880", "513080"): return "海外股指"
    if n in ("510170", "159985"): return "商品"
    return "其他"

tgt["类别"] = tgt["code"].apply(cat)
piv = tgt.pivot_table(index="datetime", columns="类别", values="percent", aggfunc="sum").fillna(0)
order = ["债券(国债/城投)", "黄金", "海外股指", "商品", "可转债"]
piv = piv[order]
fig, ax = plt.subplots(figsize=(13, 5))
ax.stackplot(piv.index, [piv[c] * 100 for c in order], labels=order,
             colors=["#5b8ff9", "#f6bd16", "#5ad8a6", "#e8684a", "#9270ca"], alpha=0.85)
ax.set_ylim(0, 100)
ax.set_ylabel("权重 %")
ax.set_title("策略持仓类别权重演变（每期目标权重）", fontsize=14)
ax.legend(loc="upper left", ncol=5, fontsize=10)
ax.grid(alpha=0.3)
fig.tight_layout()
fig.savefig(os.path.join(OUT, "fig3_asset_mix.png"), dpi=130)
plt.close(fig)

# ============ 图4: 市场阶段收益对比 ============
stages = pd.read_csv(os.path.join(OUT, "market_stages.csv"))
fig, ax = plt.subplots(figsize=(13, 7))
y = np.arange(len(stages))
ax.barh(y + 0.2, stages["策略收益"] * 100, height=0.35, label="策略", color="#c0392b")
ax.barh(y - 0.2, stages["基准(中证500)收益"] * 100, height=0.35, label="中证500", color="#7f8c8d")
ax.set_yticks(y); ax.set_yticklabels(stages["阶段"], fontsize=9)
ax.invert_yaxis()
ax.axvline(0, color="black", lw=0.8)
for yi, v in zip(y + 0.2, stages["策略收益"] * 100):
    ax.text(v + (0.8 if v >= 0 else -0.8), yi, f"{v:+.1f}%", va="center", fontsize=8,
            ha="left" if v >= 0 else "right")
ax.set_xlabel("区间收益 %")
ax.set_title("不同市场阶段的策略 vs 基准收益", fontsize=14)
ax.legend()
ax.grid(alpha=0.3, axis="x")
fig.tight_layout()
fig.savefig(os.path.join(OUT, "fig4_stage_returns.png"), dpi=130)
plt.close(fig)

# ============ 图5: 标的持有期年化收益（归因） ============
attr = pd.read_csv(os.path.join(OUT, "asset_return_adjusted.csv")).sort_values("持有期年化")
names = {"511010.SH": "国债ETF", "511220.SH": "城投债ETF", "518880.SH": "黄金ETF",
         "513500.SH": "标普500ETF", "513100.SH": "纳指ETF", "511380.SH": "可转债ETF",
         "513030.SH": "德国DAX ETF", "159985.SZ": "豆粕ETF", "513880.SH": "日经225ETF",
         "510170.SH": "大宗商品ETF", "513080.SH": "法国CAC40 ETF"}
fig, ax = plt.subplots(figsize=(11, 5.5))
colors = ["#e8684a" if v < 0 else "#5ad8a6" for v in attr["持有期年化"]]
ax.barh(attr["code"].map(lambda c: names.get(c, c)), attr["持有期年化"] * 100, color=colors)
for i, (v, npos, nneg) in enumerate(zip(attr["持有期年化"], attr["正段"], attr["负段"])):
    ax.text(v * 100 + (0.5 if v >= 0 else -0.5), i, f"{v*100:+.1f}% (正段{npos}/负段{nneg})",
            va="center", fontsize=8.5, ha="left" if v >= 0 else "right")
ax.axvline(0, color="black", lw=0.8)
ax.set_xlabel("持有期年化收益 %")
ax.set_title("各标的在策略持有期间的年化收益（归因）", fontsize=14)
ax.grid(alpha=0.3, axis="x")
fig.tight_layout()
fig.savefig(os.path.join(OUT, "fig5_attribution.png"), dpi=130)
plt.close(fig)

print("图表已生成:", os.listdir(OUT))
