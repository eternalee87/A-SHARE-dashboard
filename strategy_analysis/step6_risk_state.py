# -*- coding: utf-8 -*-
"""Step 6: 持仓状态 vs 市场环境交叉分析 + 月度条件收益"""
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

monthly = pd.read_excel(os.path.join(BASE, "groupby_month_return.xlsx"))
monthly["ym"] = pd.to_datetime(monthly["str_mmyy"], format="%B %Y")

# ---------- 月度条件收益：按基准涨跌分桶 ----------
m = monthly[["ym", "monthly_return", "monthly_benchmark_return"]].copy()
m["bucket"] = pd.cut(m["monthly_benchmark_return"],
                     bins=[-1, -0.05, 0, 0.05, 1],
                     labels=["基准跌>5%", "基准跌0-5%", "基准涨0-5%", "基准涨>5%"])
grp = m.groupby("bucket", observed=True).agg(
    月数=("monthly_return", "count"),
    策略月均收益=("monthly_return", "mean"),
    策略月胜率=("monthly_return", lambda x: (x > 0).mean()),
    基准月均收益=("monthly_benchmark_return", "mean"),
    超额月均=("monthly_return", lambda x: (x - m.loc[x.index, "monthly_benchmark_return"]).mean()),
)
print("===== 月度条件收益（按基准月度涨跌分组） =====")
print(grp.to_string())
grp.to_csv(os.path.join(OUT, "conditional_monthly.csv"))

# 也按波动分组：基准月度|涨跌|大小
m["abs_b"] = m["monthly_benchmark_return"].abs()
m["vol_bucket"] = pd.cut(m["abs_b"], bins=[0, 0.03, 0.06, 1],
                         labels=["基准|月涨跌|<3%", "3-6%", ">6%"])
grp2 = m.groupby("vol_bucket", observed=True).agg(
    月数=("monthly_return", "count"),
    策略月均收益=("monthly_return", "mean"),
    策略月胜率=("monthly_return", lambda x: (x > 0).mean()),
    超额月均=("monthly_return", lambda x: (x - m.loc[x.index, "monthly_benchmark_return"]).mean()),
)
print("\n===== 月度条件收益（按基准波动分组） =====")
print(grp2.to_string())

# ---------- 每期持仓的风险状态 ----------
tgt = pd.read_excel(os.path.join(BASE, "df_target_percent.xlsx"))
tgt["datetime"] = pd.to_datetime(tgt["datetime"])
tgt = tgt[tgt["percent"] > 1e-9].copy()

# 资产类别定义（含可转债：进攻型债券）
def cat(code):
    n = code.split(".")[0]
    if n in ("511010", "511220"): return "利率/信用债"   # 国债/城投债：防御
    if n == "511380": return "可转债"                      # 进攻型债券
    if n == "518880": return "黄金"
    if n in ("513500", "513100", "513030", "513880", "513080"): return "海外股指"
    if n in ("510170", "159985"): return "商品"
    return "其他"

tgt["类别"] = tgt["code"].apply(cat)
piv = tgt.pivot_table(index="datetime", columns="类别", values="percent", aggfunc="sum").fillna(0)
piv["风险资产"] = piv.get("海外股指", 0) + piv.get("商品", 0) + piv.get("黄金", 0) + piv.get("可转债", 0)
piv["防御资产"] = piv.get("利率/信用债", 0)

# 每期风险资产占比，与之后15天策略收益关系
risk = piv["风险资产"].copy()
dates = list(risk.index)
out = []
for i, d in enumerate(dates[:-1]):
    nxt = dates[i + 1]
    # 下一期（15天）策略收益
    seg_r = (1 + r.loc[d:nxt]).prod() - 1 if len(r.loc[d:nxt]) else np.nan
    seg_rb = (1 + rb.loc[d:nxt]).prod() - 1 if len(rb.loc[d:nxt]) else np.nan
    out.append({"date": d, "风险资产占比": risk.loc[d], "海外占比": piv.loc[d].get("海外股指", 0),
                "黄金占比": piv.loc[d].get("黄金", 0), "商品占比": piv.loc[d].get("商品", 0),
                "可转债占比": piv.loc[d].get("可转债", 0), "债券占比": piv.loc[d].get("利率/信用债", 0),
                "下期策略收益": seg_r, "下期基准收益": seg_rb,
                "下期超额": seg_r - seg_rb})
pos_r = pd.DataFrame(out)
pos_r.to_csv(os.path.join(OUT, "position_vs_fwd_return.csv"), index=False)

# 风险资产占比分桶 × 下期收益
pos_r["risk_bucket"] = pd.cut(pos_r["风险资产占比"], bins=[0, 0.2, 0.4, 0.6, 1],
                              labels=["0-20%", "20-40%", "40-60%", "60-100%"])
g3 = pos_r.groupby("risk_bucket", observed=True).agg(
    期数=("下期策略收益", "count"),
    下期策略均值=("下期策略收益", "mean"),
    下期基准均值=("下期基准收益", "mean"),
    下期超额均值=("下期超额", "mean"),
)
print("\n===== 风险资产占比 → 下期（15天）收益 =====")
print(g3.to_string())
g3.to_csv(os.path.join(OUT, "risk_bucket_fwd.csv"))

# ---------- 各市场阶段持仓构成 ----------
stages = pd.read_csv(os.path.join(OUT, "market_stages.csv"))
for _, st in stages.iterrows():
    sd, ed = pd.Timestamp(st["起"]), pd.Timestamp(st["止"])
    seg = piv.loc[sd:ed]
    if len(seg) == 0:
        continue
    mean_w = seg.mean()
    risk_share = mean_w.get("风险资产", 0)
    print(f"{st['阶段']:<24} 风险资产{risk_share*100:5.1f}% | 债券{mean_w.get('利率/信用债',0)*100:5.1f}% "
          f"黄金{mean_w.get('黄金',0)*100:4.1f}% 海外{mean_w.get('海外股指',0)*100:5.1f}% "
          f"商品{mean_w.get('商品',0)*100:4.1f}% 转债{mean_w.get('可转债',0)*100:4.1f}%")
