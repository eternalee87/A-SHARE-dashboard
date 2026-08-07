# -*- coding: utf-8 -*-
"""Step 11: 策略 vs 纳指100 - 上/下跌相关性 + 三方案对比（纯策略/纯NDX/等权50-50）"""
import pandas as pd
import numpy as np
import os, sys, json

BASE = os.path.join(os.path.dirname(__file__), "data")
OUT = os.path.join(os.path.dirname(__file__), "out")

# ---------- 数据 ----------
daily = pd.read_excel(os.path.join(BASE, "groupby_daily_return.xlsx"))
daily["date"] = pd.to_datetime(daily["str_date"])
daily = daily.sort_values("date").reset_index(drop=True)
r = daily.set_index("date")["daily_return"]

ndx = pd.read_excel(os.path.join(os.path.dirname(os.path.dirname(__file__)),
                                 ".reasonix", "attachments",
                                 "clipboard-20260807-114307.681233-000032.xlsx"))
ndx = ndx[ndx["日期"].notna()].copy()
ndx["日期"] = pd.to_datetime(ndx["日期"], errors="coerce")
ndx = ndx.dropna(subset=["日期", "收盘价(元)"])
ndx = ndx.set_index("日期")["收盘价(元)"].astype(float).sort_index()
ndx = ndx[~ndx.index.duplicated(keep="last")]
ndx_ret = ndx.pct_change()

# 对齐到策略交易日
df = pd.DataFrame({"strat": r, "ndx": ndx_ret.reindex(r.index)}).dropna()
print("对齐交易日:", len(df))

# ---------- 1. 整体与条件相关性 ----------
def corr(a, b):
    m = pd.concat([a, b], axis=1).dropna()
    if len(m) < 10:
        return np.nan, len(m)
    return np.corrcoef(m.iloc[:, 0], m.iloc[:, 1])[0, 1], len(m)

up_ndx = df[df["ndx"] > 0]
dn_ndx = df[df["ndx"] < 0]
up_strat = df[df["strat"] > 0]
dn_strat = df[df["strat"] < 0]

all_corr, n = corr(df["strat"], df["ndx"])
up_corr, n_up = corr(up_ndx["strat"], up_ndx["ndx"])
dn_corr, n_dn = corr(dn_ndx["strat"], dn_ndx["ndx"])
up_s_corr, n_us = corr(up_strat["strat"], up_strat["ndx"])
dn_s_corr, n_ds = corr(dn_strat["strat"], dn_strat["ndx"])

print("===== 相关性分析 =====")
print("全样本相关系数: %.4f (n=%d)" % (all_corr, n))
print("NDX上涨日子 条件相关: %.4f (n=%d)" % (up_corr, n_up))
print("NDX下跌日子 条件相关: %.4f (n=%d)" % (dn_corr, n_dn))
print("策略上涨日子 条件相关: %.4f (n=%d)" % (up_s_corr, n_us))
print("策略下跌日子 条件相关: %.4f (n=%d)" % (dn_s_corr, n_ds))

# 同涨同跌 / 背离
same_up = ((df["ndx"] > 0) & (df["strat"] > 0)).mean()
same_dn = ((df["ndx"] < 0) & (df["strat"] < 0)).mean()
ndx_up_strat_dn = ((df["ndx"] > 0) & (df["strat"] < 0)).mean()
ndx_dn_strat_up = ((df["ndx"] < 0) & (df["strat"] > 0)).mean()
print("\nNDX涨且策略涨: %.1f%% | NDX跌且策略跌: %.1f%% | 同向合计 %.1f%%" % (same_up*100, same_dn*100, (same_up+same_dn)*100))
print("NDX涨但策略跌: %.1f%% | NDX跌但策略涨: %.1f%% | 背离合计 %.1f%%" % (ndx_up_strat_dn*100, ndx_dn_strat_up*100, (ndx_up_strat_dn+ndx_dn_strat_up)*100))

# 条件平均收益
print("\n===== 条件平均收益 =====")
print("NDX上涨日: 策略日均 %+.4f%% (n=%d) | NDX日均 %+.4f%%" % (df.loc[df['ndx']>0,'strat'].mean()*100, n_up, df.loc[df['ndx']>0,'ndx'].mean()*100))
print("NDX下跌日: 策略日均 %+.4f%% (n=%d) | NDX日均 %+.4f%%" % (df.loc[df['ndx']<0,'strat'].mean()*100, n_dn, df.loc[df['ndx']<0,'ndx'].mean()*100))
print("策略上涨日: NDX日均 %+.4f%% (n=%d)" % (df.loc[df['strat']>0,'ndx'].mean()*100, n_us))
print("策略下跌日: NDX日均 %+.4f%% (n=%d)" % (df.loc[df['strat']<0,'ndx'].mean()*100, n_ds))

# 分位数: NDX 涨跌最极端的日子策略表现
q = df["ndx"].quantile([0.05, 0.5, 0.95])
print("\nNDX 跌幅最大5%%的日子: 策略日均 %+.4f%%, 策略胜率 %.1f%%" %
      (df.loc[df['ndx'] <= q.iloc[0], 'strat'].mean()*100,
       (df.loc[df['ndx'] <= q.iloc[0], 'strat'] > 0).mean()*100))
print("NDX 涨幅最大5%%的日子: 策略日均 %+.4f%%, 策略胜率 %.1f%%" %
      (df.loc[df['ndx'] >= q.iloc[2], 'strat'].mean()*100,
       (df.loc[df['ndx'] >= q.iloc[2], 'strat'] > 0).mean()*100))

# ---------- 2. 三方案对比 ----------
def metrics(ret, name):
    cum = (1 + ret).cumprod()
    ann = cum.iloc[-1] ** (252 / len(ret)) - 1
    vol = ret.std(ddof=1) * np.sqrt(252)
    sharpe = ann / vol
    dd = cum / cum.cummax() - 1
    calmar = ann / abs(dd.min())
    return {"方案": name, "累计收益": cum.iloc[-1] - 1, "年化": ann, "波动": vol,
            "夏普(rf=0)": sharpe, "最大回撤": dd.min(), "Calmar": calmar,
            "月度胜率": np.nan}

schemes = {
    "100%策略": df["strat"],
    "100%纳指100": df["ndx"],
    "50%策略+50%纳指100": 0.5 * df["strat"] + 0.5 * df["ndx"],
}
res = pd.DataFrame([metrics(v, k) for k, v in schemes.items()]).set_index("方案")

# 月度胜率
for k, v in schemes.items():
    m = (1 + v).resample("ME").prod() - 1
    res.loc[k, "月度胜率"] = (m > 0).mean()

print("\n===== 三方案对比（2017-01 ~ 2026-07，每日再平衡） =====")
print(res.to_string())
res.to_csv(os.path.join(OUT, "ndx_comparison.csv"))

# 年度表
yr = {}
for k, v in schemes.items():
    m = (1 + v).resample("YE").prod() - 1
    yr[k] = m
yrt = pd.DataFrame(yr)
yrt.index = yrt.index.year
print("\n===== 年度收益对比 =====")
print((yrt * 100).round(2).to_string())
yrt.to_csv(os.path.join(OUT, "ndx_yearly_comparison.csv"))

# 月度相关性（等权组合 vs 各成分）
m_strat = (1 + df["strat"]).resample("ME").prod() - 1
m_ndx = (1 + df["ndx"]).resample("ME").prod() - 1
m_eq = (1 + (0.5 * df["strat"] + 0.5 * df["ndx"])).resample("ME").prod() - 1
print("\n月度收益相关性: 策略-NDX %.3f | 等权-策略 %.3f | 等权-NDX %.3f"
      % (m_strat.corr(m_ndx), m_eq.corr(m_strat), m_eq.corr(m_ndx)))

# 回撤对比（并排）
dd_data = {}
for k, v in schemes.items():
    cum = (1 + v).cumprod()
    dd_data[k] = (cum / cum.cummax() - 1).values
dd_df = pd.DataFrame(dd_data, index=df.index)
dd_df.to_csv(os.path.join(OUT, "ndx_drawdown_compare.csv"))
print("\n===== 最大回撤区间 =====")
for k, v in schemes.items():
    cum = (1 + v).cumprod()
    dd = cum / cum.cummax() - 1
    end = dd.idxmin()
    peak = cum.loc[:end].idxmax()
    print(f"{k}: 回撤 {dd.min()*100:.2f}% ({peak.date()} ~ {end.date()})")

# 等权组合相对纯策略/纯NDX的滚动优势
eq = 0.5 * df["strat"] + 0.5 * df["ndx"]
rel_eq_strat = eq.rolling(120).apply(lambda x: (1 + x).prod() - 1, raw=True) - \
               df["strat"].rolling(120).apply(lambda x: (1 + x).prod() - 1, raw=True)
print("\n滚动120日 等权-策略 超额: 均值 %+.2f%% | >0占比 %.1f%%" % (rel_eq_strat.mean()*100, (rel_eq_strat>0).mean()*100))

# ---------- 3. 关键阶段三方案对比 ----------
stages = [
    ("2018-01-29", "2019-01-03", "2018 熊市"),
    ("2019-01-04", "2019-04-30", "2019Q1 反弹"),
    ("2020-03-20", "2021-02-18", "2020-2021 牛市"),
    ("2022-01-01", "2022-10-31", "2022 熊市"),
    ("2023-05-10", "2024-02-05", "2023-24Q1 阴跌"),
    ("2024-09-19", "2024-10-08", "2024-09 政策牛"),
    ("2025-04-08", "2026-07-18", "2025-2026 牛市"),
]
print("\n===== 关键阶段三方案对比 =====")
print("%-18s%10s%10s%10s" % ("阶段", "100%策略", "100%纳指", "50/50等权"))
for s_, e_, name in stages:
    sd, ed = pd.Timestamp(s_), pd.Timestamp(e_)
    seg = df.loc[sd:ed]
    if len(seg) == 0:
        continue
    r1 = (1 + seg["strat"]).prod() - 1
    r2 = (1 + seg["ndx"]).prod() - 1
    r3 = (1 + (0.5 * seg["strat"] + 0.5 * seg["ndx"])).prod() - 1
    print("%-18s%9.2f%%%9.2f%%%9.2f%%" % (name, r1*100, r2*100, r3*100))
