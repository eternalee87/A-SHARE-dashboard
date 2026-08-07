# -*- coding: utf-8 -*-
"""Step 7: 牛末熊初/熊初阶段专项分析 - 策略行为、持仓、调仓时机"""
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

tgt = pd.read_excel(os.path.join(BASE, "df_target_percent.xlsx"))
tgt["datetime"] = pd.to_datetime(tgt["datetime"])
tgt = tgt[tgt["percent"] > 1e-9].copy()

# 牛末熊初/熊初阶段定义（基于上证指数实际走势）
phases = [
    ("2018-01-29", "2018-06-30", "2018 熊初（顶部回落前6个月）"),
    ("2018-07-01", "2019-01-03", "2018 熊中后段"),
    ("2021-02-18", "2021-06-30", "2021 牛末高位震荡"),
    ("2021-07-01", "2021-12-31", "2021 震荡走弱（熊前）"),
    ("2022-01-01", "2022-04-30", "2022 熊初急跌"),
    ("2022-05-01", "2022-10-31", "2022 熊中"),
    ("2023-05-10", "2023-12-31", "2023 反弹见顶后阴跌（熊初）"),
    ("2024-01-01", "2024-02-05", "2024 微盘股危机（熊末急跌）"),
    ("2024-10-09", "2025-04-07", "2024 政策牛后高位回调（牛末/熊初疑似）"),
    ("2026-01-01", "2026-07-18", "2026 上半年（当前，待确认性质）"),
]

rows = []
for s, e, name in phases:
    sd, ed = pd.Timestamp(s), pd.Timestamp(e)
    rs, rbs = r.loc[sd:ed], rb.loc[sd:ed]
    if len(rs) == 0:
        continue
    sr = (1 + rs).prod() - 1
    br = (1 + rbs).prod() - 1
    sdd = ((1 + rs).cumprod() / (1 + rs).cumprod().cummax() - 1).min()
    bdd = ((1 + rbs).cumprod() / (1 + rbs).cumprod().cummax() - 1).min()
    # 期间持仓（平均类别占比）
    seg = tgt[(tgt["datetime"] >= sd) & (tgt["datetime"] <= ed)]
    codes = seg.groupby("code")["percent"].agg(["mean", "count"])
    top = codes.sort_values("count", ascending=False).head(5)
    hold = " ".join(f"{c}({codes.loc[c,'mean']*100:.0f}%)" for c in top.index)
    # 期间调仓次数
    n_switch = len(seg["datetime"].unique())
    rows.append({"阶段": name, "策略收益": sr, "基准收益": br, "超额": sr - br,
                 "策略回撤": sdd, "基准回撤": bdd,
                 "主要持仓": hold, "调仓期数": n_switch})

ph = pd.DataFrame(rows)
print("===== 牛末熊初/熊初阶段策略表现 =====")
print(ph.to_string(index=False))
ph.to_csv(os.path.join(OUT, "bear_phases.csv"), index=False)

# 月度收益明细（关键阶段逐月）
print("\n===== 关键阶段逐月收益 =====")
for s, e, name in [("2021-02-18", "2022-04-30", "2021-2022牛末熊初"),
                   ("2023-05-10", "2024-02-05", "2023熊初"),
                   ("2024-10-09", "2025-04-07", "2024-2025高位回调"),
                   ("2026-01-01", "2026-07-18", "2026上半年")]:
    sd, ed = pd.Timestamp(s), pd.Timestamp(e)
    seg = monthly[(monthly["ym"] >= sd) & (monthly["ym"] <= ed)]
    print(f"--- {name} ---")
    for _, row in seg.iterrows():
        print(f"{row['str_mmyy']:<14} 策略 {row['monthly_return']*100:7.2f}%  基准 {row['monthly_benchmark_return']*100:7.2f}%  超额 {row['relative_return']*100:7.2f}%")

# 调仓日分布：调仓发生在月末/月中？观察切换时点 vs 市场状态
print("\n===== 关键切换事件的背景（策略卖出时市场状态） =====")
# 2022-04-06 卖豆粕买纳指（纳指2022年崩盘期） - 说明策略的轮动有时是反的
# 2024-09-30 政策牛爆发中：持仓是豆粕+转债+黄金+2债券
# 用持仓序列看具体日期
for d in ["2020-02-04", "2020-02-19", "2020-03-05", "2022-03-18", "2022-04-06",
          "2022-04-21", "2024-09-18", "2024-09-30", "2024-10-22", "2025-01-08"]:
    td = pd.Timestamp(d)
    seg = tgt[tgt["datetime"] == td]
    if len(seg):
        holds = seg[seg["percent"] > 0]
        print(f"{d}: " + " ".join(f"{c}({p*100:.0f}%)" for c, p in zip(holds['code'], holds['percent'])))
