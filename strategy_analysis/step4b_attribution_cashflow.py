# -*- coding: utf-8 -*-
"""Step 4b: 精确归因 - 资金流法（期初期末市值 + 买卖金额）"""
import pandas as pd
import numpy as np
import json, os

BASE = os.path.join(os.path.dirname(__file__), "data")
OUT = os.path.join(os.path.dirname(__file__), "out")

pos = pd.read_csv(os.path.join(BASE, "position_stockAccount0.csv"))
pos["datetime"] = pd.to_datetime(pos["datetime"])
o = pd.read_csv(os.path.join(BASE, "order_record.csv"))
o["datetime"] = pd.to_datetime(o["datetime"])

# 期初（2016-12-31）与期末（2026-07-18）市值
first_day = pos["datetime"].min()
last_day = pos["datetime"].max()
print("position 范围:", first_day, "->", last_day)

codes = sorted(pos["code"].unique())
rows = []
for code in codes:
    p = pos[pos["code"] == code].sort_values("datetime")
    p0 = p[p["datetime"] == first_day]
    p1 = p[p["datetime"] == last_day]
    mv0 = p0["market_value"].sum() if len(p0) else 0.0
    mv1 = p1["market_value"].sum() if len(p1) else 0.0
    oo = o[o["code"] == code]
    buy = oo[oo["side"] == 1]
    sell = oo[oo["side"] == -1]
    buy_amt = (buy["quantity"] * buy["avg_price"]).sum()
    sell_amt = (sell["quantity"] * sell["avg_price"]).sum()
    # 总盈亏 = 期末市值 + 卖出 - 买入 - 期初市值
    pnl = mv1 + sell_amt - buy_amt - mv0
    unreal = mv1 - (p1["quantity"].iloc[-1] * p1["avg_price"].iloc[-1]) if len(p1) else 0.0
    rows.append({"code": code, "期初市值": mv0, "期末市值": mv1,
                 "累计买入": buy_amt, "累计卖出": sell_amt,
                 "全期盈亏": pnl, "未实现盈亏": unreal,
                 "买入笔数": len(buy), "卖出笔数": len(sell)})

df = pd.DataFrame(rows).sort_values("全期盈亏", ascending=False)
print("\n===== 资金流法归因（元） =====")
print(df.to_string(index=False))
df.to_csv(os.path.join(OUT, "attribution_cashflow.csv"), index=False)

# 组合层面核对
total_pnl = df["全期盈亏"].sum()
print("\n标的合计盈亏: %.0f 元" % total_pnl)
port = pd.read_csv(os.path.join(BASE, "portfolio.csv"))
port["datetime"] = pd.to_datetime(port["now"])
last = port[port["datetime"] == last_day]
print("组合期末 total_value:", last["total_value"].iloc[0], "| 初始 10000000 | 组合总盈亏:", last["total_value"].iloc[0] - 10000000)
