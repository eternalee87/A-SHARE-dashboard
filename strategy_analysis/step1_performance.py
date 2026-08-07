# -*- coding: utf-8 -*-
"""Step 1: 绩效全景 - 收益、回撤、夏普、滚动alpha/beta、换手率"""
import pandas as pd
import numpy as np
import json, os

BASE = os.path.join(os.path.dirname(__file__), "data")
OUT = os.path.join(os.path.dirname(__file__), "out")
os.makedirs(OUT, exist_ok=True)

# ---------- 读取 ----------
daily = pd.read_excel(os.path.join(BASE, "groupby_daily_return.xlsx"))
daily["date"] = pd.to_datetime(daily["str_date"])
daily = daily.sort_values("date").reset_index(drop=True)

monthly = pd.read_excel(os.path.join(BASE, "groupby_month_return.xlsx"))
yearly = pd.read_excel(os.path.join(BASE, "groupby_year_return.xlsx"))

portfolio = pd.read_csv(os.path.join(BASE, "portfolio.csv"))
portfolio["date"] = pd.to_datetime(portfolio["now"])
portfolio = portfolio.sort_values("date").reset_index(drop=True)

ra = pd.read_csv(os.path.join(BASE, "rolling_alpha_beta0.csv"))
ra["date"] = pd.to_datetime(ra["date"])
ra = ra.sort_values("date").reset_index(drop=True)

bench = pd.read_csv(os.path.join(BASE, "benchmark.csv"))
bench["date"] = pd.to_datetime(bench["now"])
bench = bench.sort_values("date").reset_index(drop=True)

# ---------- 基础指标 ----------
r = daily["daily_return"].values
rb = daily["daily_benchmark_return"].values
n = len(r)
cum = (1 + daily["daily_return"]).cumprod()
nav = cum / cum.iloc[0]
ann_ret = (cum.iloc[-1]) ** (252 / n) - 1
ann_vol = r.std(ddof=1) * np.sqrt(252)
sharpe = ann_ret / ann_vol
rf = 0.0
downside = r[r < 0].std(ddof=1) * np.sqrt(252) if (r < 0).any() else np.nan
sortino = ann_ret / downside

# 回撤
peak = cum.cummax()
dd = cum / peak - 1
max_dd = dd.min()
max_dd_end = daily["date"][dd.idxmin()]
# 找最大回撤起点
peak_date = daily["date"][peak.iloc[:dd.idxmin() + 1].idxmax()]

# 回撤次数（>=2%, 5%, 10%）
def dd_episodes(threshold):
    over = dd < -threshold
    cnt = 0
    in_ep = False
    for v in over:
        if v and not in_ep:
            cnt += 1
            in_ep = True
        elif not v:
            in_ep = False
    return cnt

# 月度胜率
win_month = (monthly["monthly_return"] > 0).mean()
rel_win_month = (monthly["relative_return"] > 0).mean()
win_day = (daily["daily_return"] > 0).mean()

# 基准指标
cum_b = pd.Series((1 + rb).cumprod())
ann_ret_b = (cum_b.iloc[-1]) ** (252 / n) - 1
ann_vol_b = rb.std(ddof=1) * np.sqrt(252)
sharpe_b = ann_ret_b / ann_vol_b
max_dd_b = (cum_b / cum_b.cummax() - 1).min()

# 年度表
yr = yearly.copy()
yr.columns = ["year", "strat", "bench", "rel", "win"]
yr["strat"] = yr["strat"].astype(float)
yr["bench"] = yr["bench"].astype(float)
yr["rel"] = yr["rel"].astype(float)

# 月收益热力表格
monthly["year"] = pd.to_datetime(monthly["str_mmyy"], format="%B %Y").dt.year
monthly["month"] = pd.to_datetime(monthly["str_mmyy"], format="%B %Y").dt.month
heat = monthly.pivot_table(index="year", columns="month", values="monthly_return")

# 滚动60日相关性（手动窗口计算）
corr60 = []
for i in range(60, n):
    corr60.append(np.corrcoef(r[i - 60:i], rb[i - 60:i])[0, 1])
corr60 = pd.Series(corr60, index=daily["date"][60:])

# ---------- 输出 ----------
summary = {
    "样本区间": [str(daily["date"].iloc[0].date()), str(daily["date"].iloc[-1].date())],
    "交易日数": int(n),
    "策略累计收益": float(cum.iloc[-1] - 1),
    "策略年化收益": float(ann_ret),
    "策略年化波动": float(ann_vol),
    "策略夏普(无风险=0)": float(sharpe),
    "策略索提诺": float(sortino),
    "策略最大回撤": float(max_dd),
    "最大回撤区间": [str(peak_date.date()), str(max_dd_end.date())],
    "回撤>=2%次数": int(dd_episodes(0.02)),
    "回撤>=5%次数": int(dd_episodes(0.05)),
    "回撤>=10%次数": int(dd_episodes(0.10)),
    "月度胜率": float(win_month),
    "月度跑赢基准胜率": float(rel_win_month),
    "日胜率": float(win_day),
    "基准累计收益": float(cum_b.iloc[-1] - 1),
    "基准年化收益": float(ann_ret_b),
    "基准年化波动": float(ann_vol_b),
    "基准夏普": float(sharpe_b),
    "基准最大回撤": float(max_dd_b),
    "日均收益": float(r.mean()),
    "日均基准收益": float(rb.mean()),
}

with open(os.path.join(OUT, "summary.json"), "w", encoding="utf-8") as f:
    json.dump(summary, f, ensure_ascii=False, indent=2)

yr.to_csv(os.path.join(OUT, "yearly_table.csv"), index=False)
heat.round(4).to_csv(os.path.join(OUT, "monthly_heatmap.csv"))
corr60.to_frame("corr60").to_csv(os.path.join(OUT, "corr60.csv"))
daily[["date", "daily_return", "daily_benchmark_return", "relative_return"]].to_csv(
    os.path.join(OUT, "daily_returns.csv"), index=False)
pd.DataFrame({"date": daily["date"], "nav": nav.values, "dd": dd.values}).to_csv(
    os.path.join(OUT, "nav_dd.csv"), index=False)

print(json.dumps(summary, ensure_ascii=False, indent=2))
print("\n===== 年度表 =====")
print(yr.to_string(index=False))
