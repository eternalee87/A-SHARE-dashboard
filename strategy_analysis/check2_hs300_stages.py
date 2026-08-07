# -*- coding: utf-8 -*-
"""数据检查测试2: 沪深300数据质量 + 两基准对比 + 规范化阶段划分（含一致性校验）"""
import pandas as pd
import numpy as np
import os

BASE = os.path.join(os.path.dirname(__file__), "data")
OUT = os.path.join(os.path.dirname(__file__), "out")

# ---------- 读取三个数据源 ----------
bench = pd.read_csv(os.path.join(BASE, "benchmark.csv"))
bench["date"] = pd.to_datetime(bench["now"])
bench = bench.sort_values("date").reset_index(drop=True)

daily = pd.read_excel(os.path.join(BASE, "groupby_daily_return.xlsx"))
daily["date"] = pd.to_datetime(daily["str_date"])
daily = daily.sort_values("date").reset_index(drop=True)

def read_index(path, date_col="日期", close_col="收盘价(元)"):
    xl = pd.ExcelFile(path)
    df = xl.parse(xl.sheet_names[0])
    df = df[df[date_col].notna()]
    df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
    df = df.dropna(subset=[date_col, close_col])
    df = df.set_index(date_col)[close_col].astype(float).sort_index()
    df = df[~df.index.duplicated(keep="last")]
    return df

hs300 = read_index(os.path.join(BASE, "沪深300日数据.xlsx"))
print("=== 沪深300 数据质量 ===")
print("范围:", hs300.index.min(), "->", hs300.index.max(), "行数:", len(hs300))
print("回测区间内缺失交易日（2017-2026 与策略对齐）:")
alld = set(daily["date"])
hsi = set(hs300.index)
missing = sorted(alld - hsi)
print("  策略有但沪深300缺失的天数:", len(missing), missing[:10])
print("  沪深300有但策略没有（2017后）:", len([d for d in hsi if d >= pd.Timestamp('2017-01-01') and d not in alld]))
# 异常跳变检查（>15%）
hs_ret = hs300.pct_change()
big = hs_ret[(hs_ret.abs() > 0.15) & hs_ret.notna()]
print("  单日|涨跌|>15% 的事件:", [(str(i.date()), round(v, 4)) for i, v in big.items()])

# ---------- 关键点位核对（沪深300 vs 中证500） ----------
print("\n=== 关键点位核对 ===")
points = ["2017-01-03", "2018-01-29", "2019-01-04", "2020-03-19", "2021-02-18",
          "2021-12-13", "2022-04-27", "2022-10-31", "2023-05-09", "2024-02-05",
          "2024-09-18", "2024-10-08", "2024-11-11", "2024-12-31", "2025-03-31", "2025-04-07", "2026-07-18"]
for d in points:
    hs_v = hs300.get(pd.Timestamp(d), np.nan)
    b_v = bench.loc[bench["date"] == d, "close"].iloc[0] if len(bench[bench["date"] == d]) else np.nan
    print(f"  {d}: 沪深300 {hs_v:9.2f} | 中证500 {b_v:9.2f}")

# ---------- 规范化阶段定义（以沪深300为主基准，边界对齐关键点位） ----------
# 原则：阶段按市场趋势拐点划分，命名与日历一致；标注起止理由
stages = [
    ("2017-01-03", "2018-01-28", "2017 蓝筹慢牛", "沪深300从3310涨至4300附近(+30%)，结构牛"),
    ("2018-01-29", "2019-01-03", "2018 熊市", "沪深300从4300跌至2965(-31%)，去杠杆+贸易战"),
    ("2019-01-04", "2019-04-30", "2019Q1 牛初反弹", "沪深300从2965涨至3900(+32%)，政策底+春季躁动"),
    ("2019-05-01", "2020-03-19", "2019H2~2020Q1 震荡+疫情", "沪深300区间震荡，2020-03-19疫情底3500"),
    ("2020-03-20", "2021-02-18", "2020~2021Q1 流动性牛", "沪深300从3500涨至5931历史高点(+69%)"),
    ("2021-02-19", "2021-12-31", "2021 牛末高位震荡", "沪深300从5931回落至4900附近(-18%)，茅指数瓦解"),
    ("2022-01-01", "2022-10-31", "2022 熊市", "沪深300从4900跌至3500(-29%)，俄乌+加息+疫情"),
    ("2022-11-01", "2023-05-09", "2022Q4~2023Q1 反弹", "沪深300从3500反弹至4000(+15%)，放开预期"),
    ("2023-05-10", "2024-02-05", "2023~2024Q1 熊末阴跌", "沪深300从4000阴跌至3171(-21%)，经济预期弱"),
    ("2024-02-06", "2024-09-18", "2024 震荡磨底", "沪深300在3171~3600区间磨底，量能萎缩"),
    ("2024-09-19", "2024-10-08", "2024-09 政策牛爆发(两周)", "沪深300两周+30%，924行情"),
    ("2024-10-09", "2024-12-31", "2024Q4 暴涨后高位回调", "沪深300从4400回调至3900附近(-8%)，情绪退潮"),
    ("2025-01-01", "2025-03-31", "2025Q1 震荡蓄势", "沪深300区间3900~4000震荡，AI+结构性行情"),
    ("2025-04-01", "2025-06-30", "2025Q2 关税冲击后V型反转", "2025-04-07暴跌后修复，沪深300再创新高"),
    ("2025-07-01", "2026-07-18", "2025H2~2026 牛市延续", "沪深300震荡上行至4500+，科技+顺周期轮动"),
]

def stage_return(date_s, date_e, idx, name):
    """价格比口径：close[ed] / close[区间实际首日的前一交易日] - 1，与日收益复合口径一致"""
    seg = idx.loc[date_s:date_e]
    if len(seg) < 2:
        return None
    first = seg.index[0]  # 区间实际首日（date_s 可能为非交易日）
    prev = idx.loc[:first]
    prev_v = prev.iloc[-2] if len(prev) >= 2 else None  # 实际首日的前一交易日
    if prev_v is None or prev_v <= 0:
        return None
    return seg.iloc[-1] / prev_v - 1

def stage_return_compound(date_s, date_e, ret_series, name):
    seg = ret_series.loc[date_s:date_e]
    if len(seg) == 0:
        return None
    return (1 + seg).prod() - 1

r = daily.set_index("date")["daily_return"]
rb = daily.set_index("date")["daily_benchmark_return"]
hs_ret = hs300.pct_change()

rows = []
print("\n=== 规范化阶段表（沪深300主基准 + 中证500对照） ===")
print(f"{'阶段':<26}{'沪深300':>10}{'中证500':>10}{'策略':>10}{'沪深300校验':>12}")
for s, e, name, note in stages:
    sd, ed = pd.Timestamp(s), pd.Timestamp(e)
    hsr = stage_return(sd, ed, hs300, name)
    br = stage_return_compound(sd, ed, rb, name)
    sr = stage_return_compound(sd, ed, r, name)
    # 校验: 中证500 close价格比 vs 日收益复合（应一致；价格比从首日前一交易日收盘起算）
    b_close = bench[(bench["date"] >= sd) & (bench["date"] <= ed)]
    check = None
    if len(b_close) > 1:
        b_prev = bench.loc[bench["date"] < sd, "close"].iloc[-1]
        check = b_close["close"].iloc[-1] / b_prev - 1
    ok = "OK" if (check is not None and br is not None and abs(check - br) < 0.002) else "MISMATCH!"
    hsr_c = stage_return_compound(sd, ed, hs_ret, name)
    hsr_ok = "OK" if (hsr is not None and hsr_c is not None and abs(hsr - hsr_c) < 0.002) else "MISMATCH!"
    rows.append({"阶段": name, "起": s, "止": e, "说明": note,
                 "沪深300": hsr, "中证500": br, "策略": sr,
                 "沪深300校验": hsr_ok, "中证500校验": ok})
    print(f"{name:<26}{hsr*100:9.2f}%{br*100:9.2f}%{sr*100:9.2f}%  {hsr_ok}/{ok}")

st_df = pd.DataFrame(rows)
st_df.to_csv(os.path.join(OUT, "market_stages_v2.csv"), index=False)
print("\n已保存 market_stages_v2.csv")
