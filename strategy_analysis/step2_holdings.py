# -*- coding: utf-8 -*-
"""Step 2: 持仓全貌 - 标的全集、资产类别、权重演变、集中度、调仓频率"""
import pandas as pd
import numpy as np
import json, os

BASE = os.path.join(os.path.dirname(__file__), "data")
OUT = os.path.join(os.path.dirname(__file__), "out")
os.makedirs(OUT, exist_ok=True)

tgt = pd.read_excel(os.path.join(BASE, "df_target_percent.xlsx"))
tgt["datetime"] = pd.to_datetime(tgt["datetime"])
tgt = tgt[tgt["percent"] > 1e-9].copy()  # 只保留实际持仓（剔除0权重行）

# 每期日期列表
dates = sorted(tgt["datetime"].unique())
print("调仓期数:", len(dates), "| 数据行数:", len(tgt))

# ---------- 标的全集统计 ----------
code_stats = tgt.groupby("code").agg(
    出现期数=("datetime", "nunique"),
    平均权重=("percent", "mean"),
    最大权重=("percent", "max"),
    首次出现=("datetime", "min"),
    最后出现=("datetime", "max"),
).sort_values("出现期数", ascending=False)
print("\n===== 标的全集（%d 个）=====" % len(code_stats))
print(code_stats.to_string())

code_stats.to_csv(os.path.join(OUT, "code_stats.csv"))

# ---------- 资产类别映射（按代码前缀 + 已知ETF） ----------
def classify(code):
    """粗分类：根据代码规则识别 ETF 类型"""
    # 债券 ETF: 511xxx 沪 / 159xxx 部分
    # 海外: 513xxx(沪跨境) / 1599xx(深跨境)
    # 商品: 518xxx(黄金) / 1599xx(商品) / 511xxx(金)
    # 货币: 511xxx(货币)
    # A股宽基/行业/主题: 510xxx/512xxx/515xxx/516xxx/517xxx/159xxx(部分)/588xxx(科创)
    # 可转债: 511380? 511180?
    # 深市 ETF: 159xxx
    # 场内 LOF/封闭: 16xxxx
    # 股票: 6xxxxx/0xxxxx
    # 港股通: 513xxx 部分 / 159920等
    num = code.split(".")[0]
    if num.startswith("5188"):  return "黄金"
    if num.startswith("513"):    return "跨境ETF(海外股)"
    if num.startswith("15992") or num.startswith("15993"): return "跨境ETF(海外股)"
    if num.startswith("511") :   return "债券/货币ETF"
    if num.startswith("510") or num.startswith("512") or num.startswith("515") or num.startswith("516") or num.startswith("517") or num.startswith("588"): return "A股ETF"
    if num.startswith("159"):    return "A股/商品ETF"
    if num.startswith("16"):     return "LOF/封闭式"
    if num.startswith("6") or num.startswith("0") or num.startswith("3"): return "个股"
    return "其他"

tgt["类别"] = tgt["code"].apply(classify)

# 各类别持有权重的时间序列（每期）
piv = tgt.pivot_table(index="datetime", columns="类别", values="percent", aggfunc="sum").fillna(0)
piv.to_csv(os.path.join(OUT, "asset_class_weight.csv"))

print("\n===== 资产类别平均权重 =====")
print(piv.mean().sort_values(ascending=False).to_string())

# 每期标的数量 & 集中度
per_date = tgt.groupby("datetime").agg(
    标数=("code", "nunique"),
    最大权重=("percent", "max"),
    前3权重=("percent", lambda x: x.nlargest(3).sum()),
)
per_date["HHI"] = tgt.groupby("datetime")["percent"].apply(lambda x: (x ** 2).sum())
per_date.to_csv(os.path.join(OUT, "per_date_holdings.csv"))
print("\n===== 每期持仓结构 =====")
print(per_date.describe().to_string())

# ---------- 调仓频率 ----------
deltas = np.diff([d.timestamp() for d in dates]) / 86400
print("\n调仓间隔(天): 均值 %.1f, 中位 %.1f, 最小 %.0f, 最大 %.0f" % (deltas.mean(), np.median(deltas), deltas.min(), deltas.max()))

# ---------- 权重演变：持有期最长的前10个标的的权重序列 ----------
top10 = code_stats.head(10).index.tolist()
w = tgt[tgt["code"].isin(top10)].pivot_table(index="datetime", columns="code", values="percent").fillna(0)
w.to_csv(os.path.join(OUT, "top10_weights.csv"))
print("\n===== 前10标的最新权重(2026-07-13) =====")
print(w.iloc[-1].sort_values(ascending=False).to_string())
