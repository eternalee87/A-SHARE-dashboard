# -*- coding: utf-8 -*-
"""10个产品净值指标：2026以来最大回撤 / VaR / 历史最大回撤 / 最长回撤期(天/期间) / 2025收益率 / 2025波动率"""
import pandas as pd, glob, sys, math
sys.stdout.reconfigure(encoding='utf-8')
pd.set_option('display.max_colwidth', 30)

files = sorted(glob.glob(r'.reasonix/attachments/clipboard-20260806-161338.*.*'))

def load_nav(path):
    df = pd.ExcelFile(path).parse(pd.ExcelFile(path).sheet_names[0], header=None)
    # 找表头行并定位列
    hdr = None; cols = {}
    for i in range(min(3, len(df))):
        row = [str(x) for x in df.iloc[i].tolist()]
        if any('净值日期' in x for x in row):
            hdr = i
            for j, x in enumerate(row):
                if '产品名称' in x: cols['name'] = j
                elif '产品代码' in x: cols['code'] = j
                elif '净值日期' in x: cols['date'] = j
                elif '累计' in x and '单位净值' in x: cols['cum'] = j
                elif '累计净值' in x: cols['cum'] = j
                elif '单位净值' in x and '累计' not in x: cols['nav'] = j
            break
    d = df.iloc[hdr+1:].copy()
    keep = [cols['name'], cols['code'], cols['date'], cols['nav'], cols['cum']]
    d = d.iloc[:, keep]
    d.columns = ['name', 'code', 'date', 'nav', 'cum']
    d = d.dropna(subset=['date'])
    d['date'] = pd.to_datetime(d['date'], errors='coerce')
    d['nav'] = pd.to_numeric(d['nav'], errors='coerce')
    d['cum'] = pd.to_numeric(d['cum'], errors='coerce')
    d = d.dropna(subset=['date', 'cum']).sort_values('date').drop_duplicates('date').reset_index(drop=True)
    return str(d['name'].iloc[0]).strip(), str(d['code'].iloc[0]).strip(), d

def max_drawdown(cum):
    dd = cum / cum.cummax() - 1
    return dd.min(), dd

def longest_drawdown_period(dates, cum):
    """最长回撤期：峰值日->恢复日(净值>=峰值)的自然日差；未恢复则算到期末并标记"""
    peak_val = cum.iloc[0]; peak_date = dates.iloc[0]
    best = (0, None, None, False)   # (days, start, end, unrecovered)
    for dt, v in zip(dates, cum):
        if v >= peak_val:
            if v > peak_val or dt == dates.iloc[0]:
                peak_val = v; peak_date = dt
        else:
            pass
    # 标准做法：遍历找回撤区间
    peak_val = cum.iloc[0]; peak_date = dates.iloc[0]
    cur_start = None
    for dt, v in zip(dates, cum):
        if v >= peak_val:
            if cur_start is not None:
                days = (dt - cur_start).days
                if days > best[0]:
                    best = (days, cur_start, dt, False)
                cur_start = None
            peak_val = v; peak_date = dt
        else:
            if cur_start is None:
                cur_start = peak_date
    if cur_start is not None:
        days = (dates.iloc[-1] - cur_start).days
        if days > best[0]:
            best = (days, cur_start, dates.iloc[-1], True)
    return best

def var_hist(ret, alpha=0.05):
    return -ret.quantile(alpha)

rows = []
for f in files:
    name, code, d = load_nav(f)
    cum = d['cum']
    dates = d['date']
    ret = cum.pct_change().dropna()
    # 1) 2026以来最大回撤
    m26 = d[d['date'] >= '2026-01-01']
    dd26, _ = max_drawdown(m26['cum'])
    # 3) 历史最大回撤
    dd_all, _ = max_drawdown(cum)
    # 2) VaR(99%, 周度, 历史模拟)
    var99 = var_hist(ret, 0.01)
    var95 = var_hist(ret, 0.05)
    # 4/5) 最长回撤期
    days, start, end, unrecovered = longest_drawdown_period(dates, cum)
    # 8) 2025收益率：起点=2024年末最后净值（成立晚于2025则用首期），终点=2025年末
    d25_end = d[d['date'] <= '2025-12-31']
    d24_end = d[d['date'] <= '2024-12-31']
    start_nav = d24_end.iloc[-1] if len(d24_end) >= 1 else d.iloc[0]
    if len(d25_end) >= 1 and d25_end['date'].iloc[-1] > start_nav['date']:
        y25_ret = d25_end['cum'].iloc[-1] / start_nav['cum'] - 1
    else:
        y25_ret = float('nan')
    # 9) 2025波动率：2025年内周收益率年化（起点=2024年末或成立日，跨年首周收益计入）
    y25w = d[(d['date'] >= start_nav['date']) & (d['date'] <= '2025-12-31')]
    y25r = y25w['cum'].pct_change().dropna()
    y25_vol = y25r.std() * math.sqrt(52) if len(y25r) > 1 else float('nan')
    rows.append(dict(产品=name.replace('私募证券投资基金', ''), code=code,
                     成立=dates.iloc[0].strftime('%Y-%m-%d'), 期末=dates.iloc[-1].strftime('%Y-%m-%d'),
                     dd2026=dd26, var99=var99, var95=var95, dd_hist=dd_all,
                     dd_days=days, dd_period=f"{start.strftime('%Y-%m-%d')} ~ {end.strftime('%Y-%m-%d')}{'（未恢复）' if unrecovered else ''}",
                     y25_ret=y25_ret, y25_vol=y25_vol))

res = pd.DataFrame(rows)
print("指标口径：累计净值；周度；最大回撤=净值回撤峰值；VaR=历史模拟法99%置信周度VaR（正数=损失）；2025波动率=2025年内周收益率年化(×√52)")
print()
cols = ['产品', '成立', '2026以来最大回撤', 'VaR99%周度', 'VaR95%周度(参考)', '历史最大回撤', '最长回撤期(天)', '最长回撤期间', '2025收益率', '2025波动率']
out = pd.DataFrame({
    '产品': res['产品'],
    '成立': res['成立'],
    '2026以来最大回撤': res['dd2026'].map(lambda x: f"{x*100:.2f}%"),
    'VaR99%周度': res['var99'].map(lambda x: f"{x*100:.2f}%"),
    'VaR95%周度(参考)': res['var95'].map(lambda x: f"{x*100:.2f}%"),
    '历史最大回撤': res['dd_hist'].map(lambda x: f"{x*100:.2f}%"),
    '最长回撤期(天)': res['dd_days'],
    '最长回撤期间': res['dd_period'],
    '2025收益率': res['y25_ret'].map(lambda x: f"{x*100:.2f}%" if pd.notna(x) else '成立不足'),
    '2025波动率': res['y25_vol'].map(lambda x: f"{x*100:.2f}%" if pd.notna(x) else '成立不足'),
})
print(out.to_string(index=False))
out.to_csv('10只产品指标表_20260630.csv', index=False, encoding='utf-8-sig')
print('\n已导出 10只产品指标表_20260630.csv')
