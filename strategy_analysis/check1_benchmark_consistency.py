# -*- coding: utf-8 -*-
"""数据检查测试1: 基准数据一致性 - benchmark.csv close vs groupby_daily_return"""
import pandas as pd
import numpy as np
import os

BASE = os.path.join(os.path.dirname(__file__), "data")

# ---------- 数据源1: benchmark.csv（平台基准价格） ----------
bench = pd.read_csv(os.path.join(BASE, "benchmark.csv"))
bench["date"] = pd.to_datetime(bench["now"])
bench = bench.sort_values("date").reset_index(drop=True)
print("=== benchmark.csv ===")
print("范围:", bench["date"].min(), "->", bench["date"].max(), "行数:", len(bench))
print("benchmark列唯一值:", bench["benchmark"].unique())
print("close 缺失:", bench["close"].isna().sum(), "| close<=0:", (bench["close"] <= 0).sum())

# ---------- 数据源2: groupby_daily_return.xlsx（平台日收益表） ----------
daily = pd.read_excel(os.path.join(BASE, "groupby_daily_return.xlsx"))
daily["date"] = pd.to_datetime(daily["str_date"])
daily = daily.sort_values("date").reset_index(drop=True)
print("\n=== groupby_daily_return.xlsx ===")
print("范围:", daily["date"].min(), "->", daily["date"].max(), "行数:", len(daily))
print("daily_benchmark_return 非空:", daily["daily_benchmark_return"].notna().sum(),
      "| 绝对值>0.3(单日>30%?)异常:", int((daily["daily_benchmark_return"].abs() > 0.3).sum()))
print("daily_return 非空:", daily["daily_return"].notna().sum())

# ---------- 交叉验证1: 日期对齐 + 收益一致性 ----------
m = bench.merge(daily[["date", "daily_benchmark_return"]], on="date", how="inner")
print("\n=== 交叉验证: benchmark close 推算日收益 vs groupby 基准收益 ===")
print("对齐交易日:", len(m))
bench_ret = m["close"].pct_change()
# pct_change 第一个是 NaN，与 daily 收益第一行（benchmark 首日收益）无法比，跳过第一行
mask = bench_ret.notna()
diff = (bench_ret[mask] - m.loc[mask, "daily_benchmark_return"]).abs()
print("中证500推算收益 vs groupby基准收益:")
print("  相关系数: %.6f" % np.corrcoef(bench_ret[mask], m.loc[mask, "daily_benchmark_return"])[0, 1])
print("  平均绝对差异: %.6f" % diff.mean())
print("  最大绝对差异: %.6f (发生在 %s)" % (diff.max(), m.loc[diff.idxmax(), "date"].date()))
diff2 = diff.reset_index(drop=True)
m2 = m.loc[mask].reset_index(drop=True)
big = m2[diff2 > 0.001]
print("  差异>0.1% 的天数:", len(big))
if len(big):
    print(big[["date", "close", "daily_benchmark_return"]].head(10).to_string())

# ---------- 交叉验证2: 累计收益一致性 ----------
cum_bench = bench["close"].iloc[-1] / bench["close"].iloc[0] - 1
cum_daily = (1 + daily["daily_benchmark_return"]).prod() - 1
print("\n中证500 全期累计收益: benchmark价格 %.6f vs groupby收益 %.6f | 差 %.6f"
      % (cum_bench, cum_daily, cum_bench - cum_daily))

# ---------- 2024-10-09 ~ 2025-04-07 专项检查 ----------
print("\n=== 2024-10-09 ~ 2025-04-07 专项检查（用户质疑区间） ===")
sd, ed = pd.Timestamp("2024-10-09"), pd.Timestamp("2025-04-07")
seg_b = bench[(bench["date"] >= sd) & (bench["date"] <= ed)]
seg_d = daily[(daily["date"] >= sd) & (daily["date"] <= ed)]
print("benchmark 首日 %s close %.2f | 末日 %s close %.2f | 区间收益 %.4f"
      % (seg_b["date"].iloc[0].date(), seg_b["close"].iloc[0],
         seg_b["date"].iloc[-1].date(), seg_b["close"].iloc[-1],
         seg_b["close"].iloc[-1] / seg_b["close"].iloc[0] - 1))
print("groupby 区间基准收益(复合): %.4f" % ((1 + seg_d["daily_benchmark_return"]).prod() - 1))
print("groupby 区间策略收益(复合): %.4f" % ((1 + seg_d["daily_return"]).prod() - 1))

# 该区间内 benchmark close 的极值（判断是不是起点取在了高点）
print("\n该区间内中证500 close 轨迹（每20个交易日取样）:")
for i in range(0, len(seg_b), 20):
    row = seg_b.iloc[i]
    print("  %s  %.2f" % (row["date"].date(), row["close"]))
print("  区间最高: %.2f @ %s" % (seg_b["close"].max(), seg_b.loc[seg_b["close"].idxmax(), "date"].date()))
print("  区间最低: %.2f @ %s" % (seg_b["close"].min(), seg_b.loc[seg_b["close"].idxmin(), "date"].date()))

# 中证500 在 2024-09-18（起涨点）和 2024-10-08（顶）的位置
for d in ["2024-09-18", "2024-10-08", "2024-12-31", "2025-01-31", "2025-02-28", "2025-03-31", "2025-04-07"]:
    row = bench[bench["date"] == d]
    if len(row):
        print("  %s close=%.2f" % (d, row["close"].iloc[0]))
