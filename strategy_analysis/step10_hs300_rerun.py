# -*- coding: utf-8 -*-
"""Step 10: 沪深300口径全套重算 - 月度条件收益、牛末熊初、滚动超额、情景模拟"""
import pandas as pd
import numpy as np
import json, os

BASE = os.path.join(os.path.dirname(__file__), "data")
OUT = os.path.join(os.path.dirname(__file__), "out")

daily = pd.read_excel(os.path.join(BASE, "groupby_daily_return.xlsx"))
daily["date"] = pd.to_datetime(daily["str_date"])
daily = daily.sort_values("date").reset_index(drop=True)
r = daily.set_index("date")["daily_return"]

def read_index(path, date_col="日期", close_col="收盘价(元)"):
    xl = pd.ExcelFile(path)
    df = xl.parse(xl.sheet_names[0])
    df = df[df[date_col].notna()]
    df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
    df = df.dropna(subset=[date_col, close_col])
    df = df.set_index(date_col)[close_col].astype(float).sort_index()
    return df[~df.index.duplicated(keep="last")]

hs300 = read_index(os.path.join(BASE, "沪深300日数据.xlsx"))
sh = read_index(os.path.join(BASE, "上证指数日数据.xlsx"))

# 沪深300 日收益（对齐策略交易日）
hs_ret = hs300.pct_change().reindex(r.index)

# ---------- 1. 月度条件收益（沪深300口径） ----------
monthly = pd.read_excel(os.path.join(BASE, "groupby_month_return.xlsx"))
monthly["ym"] = pd.to_datetime(monthly["str_mmyy"], format="%B %Y")
hs_monthly = (1 + hs_ret.fillna(0)).resample("ME").prod() - 1
m = pd.DataFrame({"period": hs_monthly.index.to_period("M"), "hs300": hs_monthly.values})
monthly["period"] = monthly["ym"].dt.to_period("M")
m = m.merge(monthly[["period", "monthly_return"]], on="period", how="inner")
m["bucket"] = pd.cut(m["hs300"], bins=[-1, -0.05, 0, 0.05, 1],
                     labels=["沪深300跌>5%", "跌0-5%", "涨0-5%", "涨>5%"])
grp = m.groupby("bucket", observed=True).agg(
    月数=("monthly_return", "count"),
    策略月均=("monthly_return", "mean"),
    策略胜率=("monthly_return", lambda x: (x > 0).mean()),
    沪深300月均=("hs300", "mean"),
    超额月均=("monthly_return", lambda x: (x - m.loc[x.index, "hs300"]).mean()))
print("===== 月度条件收益（沪深300口径） =====")
print(grp.to_string())
grp.to_csv(os.path.join(OUT, "conditional_monthly_hs300.csv"))

# ---------- 2. 牛末熊初/熊初阶段（沪深300口径） ----------
phases = [
    ("2018-01-29", "2018-06-30", "2018 熊初"),
    ("2018-07-01", "2019-01-03", "2018 熊中后段"),
    ("2021-02-19", "2021-06-30", "2021 牛末高位震荡"),
    ("2021-07-01", "2021-12-31", "2021 震荡走弱"),
    ("2022-01-01", "2022-04-30", "2022 熊初急跌"),
    ("2022-05-01", "2022-10-31", "2022 熊中"),
    ("2023-05-10", "2023-12-31", "2023 反弹见顶阴跌"),
    ("2024-01-01", "2024-02-05", "2024 微盘危机(熊末急跌)"),
    ("2024-10-09", "2025-04-07", "2024.10~2025.4 高位回调+关税冲击"),
    ("2026-01-01", "2026-07-18", "2026 上半年"),
]
rows = []
for s, e, name in phases:
    sd, ed = pd.Timestamp(s), pd.Timestamp(e)
    rs, hs = r.loc[sd:ed], hs_ret.loc[sd:ed]
    if len(rs) == 0:
        continue
    sr = (1 + rs).prod() - 1
    hr = (1 + hs.dropna()).prod() - 1 if hs.notna().any() else np.nan
    sdd = ((1 + rs).cumprod() / (1 + rs).cumprod().cummax() - 1).min()
    hdd = ((1 + hs.dropna()).cumprod() / (1 + hs.dropna()).cumprod().cummax() - 1).min() if hs.notna().any() else np.nan
    rows.append({"阶段": name, "策略收益": sr, "沪深300收益": hr, "超额": sr - hr,
                 "策略回撤": sdd, "沪深300回撤": hdd})
ph = pd.DataFrame(rows)
print("\n===== 牛末熊初/熊初阶段（沪深300口径） =====")
print(ph.to_string(index=False))
ph.to_csv(os.path.join(OUT, "bear_phases_hs300.csv"), index=False)

# ---------- 3. 滚动120日超额（沪深300口径） ----------
rel = (1 + r) / (1 + hs_ret.fillna(0)) - 1
roll_rel = rel.rolling(120).apply(lambda x: (1 + x).prod() - 1, raw=True).dropna()
print("\n===== 滚动120日超额（沪深300）统计 =====")
print("超额>0 天数占比: %.1f%%" % ((roll_rel > 0).mean() * 100))
print("超额均值: %.4f | 中位数: %.4f" % (roll_rel.mean(), roll_rel.median()))

def seg_stats(sig, above, min_days=30):
    out, start = [], None
    for d, v in sig.items():
        cond = (v > 0) if above else (v < 0)
        if cond and start is None:
            start = d
        elif not cond and start is not None:
            if (d - start).days >= min_days:
                seg_r = (1 + r.loc[start:d]).prod() - 1
                seg_h = (1 + hs_ret.loc[start:d].fillna(0)).prod() - 1
                out.append({"区间": f"{start.date()} ~ {d.date()}", "天数": (d - start).days,
                            "策略": seg_r, "沪深300": seg_h, "超额": seg_r - seg_h})
            start = None
    if start is not None:
        d = sig.index[-1]
        if (d - start).days >= min_days:
            seg_r = (1 + r.loc[start:d]).prod() - 1
            seg_h = (1 + hs_ret.loc[start:d].fillna(0)).prod() - 1
            out.append({"区间": f"{start.date()} ~ {d.date()}", "天数": (d - start).days,
                        "策略": seg_r, "沪深300": seg_h, "超额": seg_r - seg_h})
    return pd.DataFrame(out)

pos_df = seg_stats(roll_rel, True)
neg_df = seg_stats(roll_rel, False)
print("\n===== 顺风期（120日滚动超额>0，>=30天，沪深300口径） =====")
print(pos_df.to_string(index=False))
print("\n===== 逆风期（120日滚动超额<0，>=30天，沪深300口径） =====")
print(neg_df.to_string(index=False))
pos_df.to_csv(os.path.join(OUT, "tailwind_hs300.csv"), index=False)
neg_df.to_csv(os.path.join(OUT, "headwind_hs300.csv"), index=False)

# ---------- 4. 情景模拟（沪深300作为A股资产 + 上证MA250趋势过滤） ----------
aligned = pd.DataFrame({"strat": r, "hs300": hs_ret}).dropna()
def metrics(ret, name):
    cum = (1 + ret).cumprod()
    ann = cum.iloc[-1] ** (252 / len(ret)) - 1
    vol = ret.std(ddof=1) * np.sqrt(252)
    sharpe = ann / vol
    dd = (cum / cum.cummax() - 1).min()
    return {"情景": name, "累计收益": cum.iloc[-1] - 1, "年化": ann, "波动": vol,
            "夏普(rf=0)": sharpe, "最大回撤": dd}

ma250 = sh.rolling(250).mean()
trend = (sh > ma250).reindex(aligned.index).fillna(False)

res = {
    "原策略": metrics(aligned["strat"], "原策略"),
    "静态20%沪深300": metrics(0.8 * aligned["strat"] + 0.2 * aligned["hs300"], "静态20%沪深300"),
    "趋势过滤A股(0/20%)": metrics(aligned["strat"] * (1 - trend * 0.2) + aligned["hs300"] * trend * 0.2, "趋势过滤A股(0/20%)"),
    "熊市降仓40%": metrics(aligned["strat"] * (1 - 0.4 * (~trend).astype(float)), "熊市降仓40%"),
}
resdf = pd.DataFrame(res).T
print("\n===== 情景模拟（沪深300资产+上证MA250） =====")
print(resdf.to_string())
resdf.to_csv(os.path.join(OUT, "scenario_sim_hs300.csv"))
