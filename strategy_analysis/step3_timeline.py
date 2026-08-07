# -*- coding: utf-8 -*-
"""Step 3: 持仓时间线 - 每个标的的持有区间、切换点、以及每日持仓市值"""
import pandas as pd
import numpy as np
import json, os

BASE = os.path.join(os.path.dirname(__file__), "data")
OUT = os.path.join(os.path.dirname(__file__), "out")
os.makedirs(OUT, exist_ok=True)

tgt = pd.read_excel(os.path.join(BASE, "df_target_percent.xlsx"))
tgt["datetime"] = pd.to_datetime(tgt["datetime"])
tgt = tgt[tgt["percent"] > 1e-9].copy()

# 权重矩阵（每期 × 标的）
wm = tgt.pivot_table(index="datetime", columns="code", values="percent").fillna(0)
wm.index = wm.index.date

# 持有区间：连续持有段
segments = []
for code in wm.columns:
    hold = wm[code] > 0
    # 找连续段
    in_seg = False
    start = None
    for d, v in hold.items():
        if v and not in_seg:
            start, in_seg = d, True
        elif not v and in_seg:
            segments.append((code, start, d))
            in_seg = False
    if in_seg:
        segments.append((code, start, wm.index[-1]))

seg = pd.DataFrame(segments, columns=["code", "start", "end"])
seg["期数"] = 1
print("===== 持有区间（连续段） =====")
for _, row in seg.iterrows():
    print(f"{row['code']:>10}  {row['start']} ~ {row['end']}")
seg.to_csv(os.path.join(OUT, "hold_segments.csv"), index=False)

# 每期持仓明细（前5）
print("\n===== 每期持仓（部分抽样） =====")
for i in range(0, len(wm), 20):
    row = wm.iloc[i]
    held = [c for c in row.index if row[c] > 0]
    print(wm.index[i], "->", " ".join(held))

# 切换点：相邻两期持仓差异
print("\n===== 调仓切换（买入→卖出） =====")
prev = set()
for i, (d, row) in enumerate(wm.iterrows()):
    cur = set(c for c in row.index if row[c] > 0)
    if i > 0:
        added = cur - prev
        removed = prev - cur
        if added or removed:
            print(f"{d}: 买入 {' '.join(sorted(added)) or '-'} | 卖出 {' '.join(sorted(removed)) or '-'}")
    prev = cur
