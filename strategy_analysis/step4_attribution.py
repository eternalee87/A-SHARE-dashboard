# -*- coding: utf-8 -*-
"""Step 4: 持仓归因 - 每个标的的持有期收益贡献、换手损耗"""
import pandas as pd
import numpy as np
import json, os

BASE = os.path.join(os.path.dirname(__file__), "data")
OUT = os.path.join(os.path.dirname(__file__), "out")
os.makedirs(OUT, exist_ok=True)

pos = pd.read_csv(os.path.join(BASE, "position_stockAccount0.csv"))
pos["datetime"] = pd.to_datetime(pos["datetime"])
pos = pos.sort_values("datetime").reset_index(drop=True)

# 每个标的的每日单位价格（用 market_value/quantity，剔除 quantity=0）
pos = pos[pos["quantity"] > 0].copy()
pos["unit_price"] = pos["market_value"] / pos["quantity"]
pos = pos[pos["unit_price"] > 0]

# 标的每日收益（用单位价格），忽略调仓日混入（大多数日无交易）
codes = sorted(pos["code"].unique())
price_series = {}
for code in codes:
    sub = pos[pos["code"] == code].set_index("datetime")["unit_price"].sort_index()
    price_series[code] = sub

# 读取持有段
seg = pd.read_csv(os.path.join(OUT, "hold_segments.csv"))
seg["start"] = pd.to_datetime(seg["start"])
seg["end"] = pd.to_datetime(seg["end"])

# 计算每个持有段的收益（用段首和段末价格）
rows = []
for _, s in seg.iterrows():
    code = s["code"]
    p = price_series[code]
    # 段首价格：>= start 的第一个；段末价格：<= end 的最后一个
    seg_prices = p[(p.index >= s["start"]) & (p.index <= s["end"])]
    if len(seg_prices) < 2:
        continue
    r = seg_prices.iloc[-1] / seg_prices.iloc[0] - 1
    days = (seg_prices.index[-1] - seg_prices.index[0]).days
    rows.append({"code": code, "start": s["start"], "end": s["end"],
                 "seg_return": r, "days": days,
                 "p0": seg_prices.iloc[0], "p1": seg_prices.iloc[-1]})

segr = pd.DataFrame(rows)
# 每段收益的年化
segr["ann_return"] = (1 + segr["seg_return"]) ** (365 / segr["days"].clip(lower=1)) - 1

# 每标的汇总：段数、平均段收益、年化（按天数加权）
agg = []
for code, g in segr.groupby("code"):
    total_days = g["days"].sum()
    # 组合段收益（复合）
    comp = (1 + g["seg_return"]).prod() - 1
    ann = (1 + comp) ** (365 / max(total_days, 1)) - 1
    agg.append({"code": code, "段数": len(g), "总持有天数": total_days,
                "复合收益": comp, "持有期年化": ann,
                "平均段收益": g["seg_return"].mean(),
                "正收益段数": int((g["seg_return"] > 0).sum()),
                "负收益段数": int((g["seg_return"] < 0).sum())})
aggdf = pd.DataFrame(agg).sort_values("持有期年化", ascending=False)
print("===== 各标的持有期收益（未加权，粗算） =====")
print(aggdf.to_string(index=False))
aggdf.to_csv(os.path.join(OUT, "asset_return_contribution.csv"), index=False)

# 换手统计：order_record
o = pd.read_csv(os.path.join(BASE, "order_record.csv"))
o["datetime"] = pd.to_datetime(o["datetime"])
o["side"] = o["side"].astype(int)  # 1=买? 2=卖? 需确认
print("\n===== order_record side 分布 =====")
print(o["side"].value_counts())
print("成交额(买):", (o[o["side"] == 1]["quantity"] * o[o["side"] == 1]["avg_price"]).sum())
print("成交额(卖):", (o[o["side"] == 2]["quantity"] * o[o["side"] == 2]["avg_price"]).sum())

# 每笔交易成本
o["cost"] = o["commission_cost"] + o["friction_cost"]
print("总交易成本:", o["cost"].sum())
print("交易笔数:", len(o))
