# -*- coding: utf-8 -*-
"""Step 4c: 价格序列修正（份额折算/除息） + 组合日收益重构验证"""
import pandas as pd
import numpy as np
import json, os

BASE = os.path.join(os.path.dirname(__file__), "data")
OUT = os.path.join(os.path.dirname(__file__), "out")

pos = pd.read_csv(os.path.join(BASE, "position_stockAccount0.csv"))
pos["datetime"] = pd.to_datetime(pos["datetime"])
pos = pos[pos["quantity"] > 0].copy()
pos["unit_price"] = pos["market_value"] / pos["quantity"]

codes = sorted(pos["code"].unique())
jumps = {}
for code in codes:
    p = pos[pos["code"] == code].set_index("datetime")["unit_price"].sort_index()
    ret = p.pct_change()
    big = ret[(ret.abs() > 0.15) & ret.notna()]
    if len(big):
        jumps[code] = [(str(i.date()), round(v, 4)) for i, v in big.items()]
print("===== 价格跳变 >15% 的事件（疑似折算/除息） =====")
for k, v in jumps.items():
    print(k, v)

# 修正：后复权（把跳变前的价格按比例缩放，保持后续序列连续）
# 采用"前向复权"：以最新价为基准，把跳变点之前的价格乘以后续比值
def adjust_series(p):
    ret = p.pct_change()
    # 找到所有 >15% 的跳变点
    adj = p.copy().astype(float)
    # 从后往前处理：每个跳变点之后的序列保持不变，之前的乘以 (1+跳变比例)
    # 实际上对分段：跳变点 i 处，ret_i = p_i/p_{i-1} - 1。若 |ret_i|>15% 视为折算
    # 则 p_{i-1} 之前所有价格乘以 (1+ret_i) 即可让序列连续（前复权）
    idx = adj.index
    for i in range(len(adj) - 1, 0, -1):
        r = adj.iloc[i] / adj.iloc[i - 1] - 1
        if abs(r) > 0.15:
            adj.iloc[:i] *= (1 + r)
    return adj

adjusted = {}
for code in codes:
    p = pos[pos["code"] == code].set_index("datetime")["unit_price"].sort_index()
    adjusted[code] = adjust_series(p)

# 验证：511220 修正后
p = adjusted["511220.SH"]
g = p.groupby(p.index.year)
print("\n511220 修正后每年首尾:")
for y, gg in g:
    print(y, round(gg.iloc[0], 4), "->", round(gg.iloc[-1], 4), "年化:", round((gg.iloc[-1]/gg.iloc[0]) ** (365/len(gg)) - 1, 4))

# 全标的年化收益（修正后，持有期）
seg = pd.read_csv(os.path.join(OUT, "hold_segments.csv"))
seg["start"] = pd.to_datetime(seg["start"])
seg["end"] = pd.to_datetime(seg["end"])
rows = []
for _, s in seg.iterrows():
    code = s["code"]
    if code not in adjusted:
        continue
    p = adjusted[code]
    seg_prices = p[(p.index >= s["start"]) & (p.index <= s["end"])]
    if len(seg_prices) < 2:
        continue
    r = seg_prices.iloc[-1] / seg_prices.iloc[0] - 1
    days = (seg_prices.index[-1] - seg_prices.index[0]).days
    rows.append({"code": code, "start": s["start"], "end": s["end"], "seg_return": r, "days": days})

segr = pd.DataFrame(rows)
agg = []
for code, g in segr.groupby("code"):
    total_days = g["days"].sum()
    comp = (1 + g["seg_return"]).prod() - 1
    ann = (1 + comp) ** (365 / max(total_days, 1)) - 1
    agg.append({"code": code, "段数": len(g), "总持有天数": total_days,
                "复合收益": comp, "持有期年化": ann,
                "正段": int((g["seg_return"] > 0).sum()), "负段": int((g["seg_return"] < 0).sum()),
                "平均段收益": g["seg_return"].mean()})
aggdf = pd.DataFrame(agg).sort_values("持有期年化", ascending=False)
print("\n===== 修正后各标的持有期年化 =====")
print(aggdf.to_string(index=False))
aggdf.to_csv(os.path.join(OUT, "asset_return_adjusted.csv"), index=False)

# 组合重构验证：每标的日收益 × 权重(当日 value_percent) 求和 vs portfolio 日收益
# 调仓日有交易，权重变了但价格序列来自 position（同日买卖混入），忽略调仓日前后1天
o = pd.read_csv(os.path.join(BASE, "order_record.csv"))
o["datetime"] = pd.to_datetime(o["datetime"])
trade_days = set(o["datetime"].dt.normalize().unique())

pos2 = pos.copy()
pos2["ret"] = np.nan
for code in codes:
    p = adjusted[code]
    r = p.pct_change().rename("ret")
    pos2.loc[pos2["code"] == code, "ret"] = pos2.loc[pos2["code"] == code, "datetime"].map(r)

pos2["contrib"] = pos2["value_percent"] * pos2["ret"]
daily_contrib = pos2.groupby("datetime")["contrib"].sum()
# 剔除调仓日（含前后1天）避免失真
keep = ~daily_contrib.index.isin(trade_days)
recon = daily_contrib[keep].dropna()

port = pd.read_csv(os.path.join(BASE, "portfolio.csv"))
port["datetime"] = pd.to_datetime(port["now"])
port = port.set_index("datetime")["daily_returns"]
aligned = pd.DataFrame({"recon": recon, "actual": port.reindex(recon.index)}).dropna()
corr = aligned.corr().iloc[0, 1]
diff = (aligned["recon"] - aligned["actual"]).abs()
print("\n===== 重构验证（非调仓日） =====")
print("样本数:", len(aligned), "| 相关系数: %.4f" % corr)
print("平均绝对差异: %.5f (%.2f%%)" % (diff.mean(), diff.mean() * 100))
print("差异>0.5%的天数:", int((diff > 0.005).sum()))
aligned.to_csv(os.path.join(OUT, "recon_check.csv"))
