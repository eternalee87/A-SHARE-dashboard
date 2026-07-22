"""
Daily vs Weekly DCA 对比回测
Weekly: 每周末交易日定投, base=10,000/周, MA200分位值模型
"""
import sys, io, os, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import pandas as pd, numpy as np

BASE = os.path.dirname(os.path.abspath(__file__))
ndx = pd.read_csv(f'{BASE}/data/ndx_data.csv', index_col=0, parse_dates=True)['close'].dropna()
vix = pd.read_csv(f'{BASE}/data/vix_data.csv', index_col=0, parse_dates=True)['close'].dropna()

common = ndx.index.intersection(vix.index).sort_values()
ma200 = ndx.rolling(200).mean()

all_ma = []
for dt in common:
    mr = float(ndx.loc[dt] / ma200.loc[dt]) if dt in ma200.index and not np.isnan(ma200.loc[dt]) else 1.0
    all_ma.append(mr)
all_ma = np.array(all_ma)

def sc(p):
    if p < 5: return -3
    if p < 15: return -2
    if p < 30: return -1
    if p <= 70: return 0
    if p <= 85: return 1
    if p <= 95: return 2
    return 3

def mc(c):
    if c < -2.0: return 2.5
    if c < -1.0: return 2.0
    if c < -0.3: return 1.5
    if c <= 0.3: return 1.0
    if c <= 1.0: return 0.75
    if c <= 2.0: return 0.5
    return 0.25

def f500(x): return max(500, int(x // 500) * 500)

def wan(v): return f'{v/10000:.1f}万' if v else '—'
def pct(v): return f'{v:+.2f}%' if v is not None else '—'

# ==================== BACKTEST ====================
def backtest(sy, mode):
    td = common[common >= f'{sy}-01-01']
    if len(td) == 0: return None

    if mode == 'weekly':
        # Pick last trading day of each ISO week
        weekly_dates = []
        for dt in td:
            iso = dt.isocalendar()
            week_key = (iso[0], iso[1])  # (year, week_number)
            weekly_dates.append((week_key, dt))
        # Group by week, keep last day
        from collections import OrderedDict
        weeks = OrderedDict()
        for wk, dt in weekly_dates:
            weeks[wk] = dt
        td_use = pd.DatetimeIndex(list(weeks.values())).sort_values()
        base = 10000
    else:
        td_use = td
        base = 2000

    inv = 0.0; sh = 0.0; rows = []
    for dt in td_use:
        nc = ndx.loc[dt]
        mr = 1.0
        if dt in ma200.index and not np.isnan(ma200.loc[dt]):
            mr = nc / ma200.loc[dt]
        p_m = (all_ma <= mr).sum() / len(all_ma) * 100
        comp = int(sc(p_m))
        amt = f500(base * mc(comp))
        sh += amt / nc; inv += amt
        rows.append({'date': dt, 'year': dt.year, 'ndx': nc, 'invested': amt,
                     'cum_inv': inv, 'shares': sh, 'mktval': sh * nc})

    df = pd.DataFrame(rows)
    y = (df['date'].iloc[-1] - df['date'].iloc[0]).days / 365.25
    fv = df['mktval'].iloc[-1]
    cagr = ((fv / inv) ** (1 / y) - 1) * 100 if y > 0 and inv > 0 else 0
    ret = (fv / inv - 1) * 100 if inv > 0 else 0
    vals = df['mktval'].values; peak = np.maximum.accumulate(vals)
    dd = float((vals / peak - 1).min()) * 100

    # Annual
    ann = df.groupby('year').agg(
        annual_invested=('invested', 'sum'),
        year_end_ndx=('ndx', 'last'),
        cum_invested=('cum_inv', 'last'),
        cum_shares=('shares', 'last'),
    ).reset_index()
    ann['cum_value'] = ann['cum_shares'] * ann['year_end_ndx']
    ann['cum_ret'] = (ann['cum_value'] / ann['cum_invested'] - 1) * 100

    dmin = int(df['invested'].min()); dmax = int(df['invested'].max())
    # Multiplier dist
    mdist = {}
    for mk in [2.5, 2.0, 1.5, 1.0, 0.75, 0.5, 0.25]:
        mdist[mk] = int((df['invested'] == f500(base * mk)).sum())

    return {'inv': inv, 'fv': fv, 'cagr': cagr, 'ret': ret, 'dd': dd,
            'dmin': dmin, 'dmax': dmax, 'days': len(df),
            'annual': ann, 'mdist': mdist, 'base': base}


# ==================== RUN ====================
SY = [2006, 2008, 2014, 2017]
print("=" * 105)
print("  Daily vs Weekly DCA 对比回测")
print(f"  Daily: 2,000/日 × 每交易日 | Weekly: 10,000/周 × 每周最后一个交易日")
print(f"  模型: MA200分位值单因子")
print("=" * 105)

for label, mode in [("📅 Daily (日度)", "daily"), ("📅 Weekly (周度)", "weekly")]:
    print(f"\n{'─' * 105}")
    print(f"  {label}")
    print(f"{'─' * 105}")

    print(f"\n  {'起点':<6} {'投入次数':>7} {'累计投入':>10} {'最终市值':>12} {'年化CAGR':>8} {'累计收益':>10} {'最大回撤':>8} {'单次低':>7} {'单次高':>7}")
    print(f"  {'─' * 6} {'─' * 7} {'─' * 10} {'─' * 12} {'─' * 8} {'─' * 10} {'─' * 8} {'─' * 7} {'─' * 7}")
    for sy in SY:
        r = backtest(sy, mode)
        if r is None: continue
        print(f"  {sy:<6} {r['days']:>7} {wan(r['inv']):>10} {wan(r['fv']):>12} {pct(r['cagr']):>8} {pct(r['ret']):>10} {pct(r['dd']):>8} {r['dmin']:>7} {r['dmax']:>7}")

# ---- Annual detail for 2006 ----
print(f"\n\n{'=' * 105}")
print("  2006 起点逐年对比")
print(f"{'=' * 105}")
for mode, base_amt in [('daily', 2000), ('weekly', 10000)]:
    r = backtest(2006, mode)
    if r is None: continue
    ann = r['annual']
    label = 'Daily 2k/日' if mode == 'daily' else 'Weekly 1w/周'
    print(f"\n  {label}:")
    print(f"  {'年份':<6} {'年投入':>9} {'累计投入':>10} {'年末NDX':>9} {'年末市值':>10} {'累计收益':>10}")
    print(f"  {'─' * 6} {'─' * 9} {'─' * 10} {'─' * 9} {'─' * 10} {'─' * 10}")
    for _, row in ann.iterrows():
        yr = int(row['year'])
        print(f"  {yr:<6} {row['annual_invested']/10000:>9.1f} {row['cum_invested']/10000:>10.1f} {row['year_end_ndx']:>9.0f} {row['cum_value']/10000:>10.1f} {row['cum_ret']:>+9.2f}%")

# ---- Crisis years ----
print(f"\n\n{'=' * 105}")
print("  危机年份投入对比")
print(f"{'=' * 105}")
print(f"  {'年份':<6} {'Daily总投':>10} {'Daily日均':>8} {'Weekly总投':>10} {'Weekly周均':>10} {'NDX涨跌':>8}")
print(f"  {'─' * 6} {'─' * 10} {'─' * 8} {'─' * 10} {'─' * 10} {'─' * 8}")
for yr in [2008, 2022]:
    for mode, base in [('daily', 2000), ('weekly', 10000)]:
        r = backtest(yr, mode)
        if r is None: continue
        if mode == 'daily':
            d_inv = r['inv']; d_days = r['days']; d_avg = d_inv / d_days
        else:
            w_inv = r['inv']; w_weeks = r['days']; w_avg = w_inv / w_weeks
    chg = (ndx.loc[f'{yr}-12-31'] / ndx.loc[f'{yr}-01-02'] - 1) * 100
    print(f"  {yr:<6} {wan(d_inv):>10} {d_avg:>8.0f} {wan(w_inv):>10} {w_avg:>10.0f} {pct(chg):>8}")

# ---- Multiplier distribution (2006) ----
print(f"\n\n{'=' * 105}")
print("  定投倍数分布 (2006起点)")
print(f"{'=' * 105}")
labels_m = {2.5: '2.5x', 2.0: '2.0x', 1.5: '1.5x', 1.0: '1.0x', 0.75: '0.75x', 0.5: '0.5x', 0.25: '0.25x'}
for mk in [2.5, 2.0, 1.5, 1.0, 0.75, 0.5, 0.25]:
    rd = backtest(2006, 'daily'); rw = backtest(2006, 'weekly')
    cd = rd['mdist'][mk]; cw = rw['mdist'][mk]
    print(f"  {labels_m[mk]:<8} Daily: {cd:>4}次 {cd/rd['days']*100:>5.1f}%    Weekly: {cw:>3}次 {cw/rw['days']*100:>5.1f}%")

# ---- 10-year summary ----
print(f"\n\n{'=' * 105}")
print("  10年推演 (2006-2015)")
print(f"{'=' * 105}")
for mode, label in [('daily', 'Daily'), ('weekly', 'Weekly')]:
    r = backtest(2006, mode)
    ann = r['annual']
    ann10 = ann[ann['year'] <= 2015]
    inv10 = ann10['annual_invested'].sum()
    fv10 = ann10[ann10['year'] == 2015]['cum_value'].values[0]
    ret10 = (fv10 / inv10 - 1) * 100
    print(f"  {label}: 10年投入={wan(inv10)} | 10年末市值={wan(fv10)} | 收益率={pct(ret10)}")

print(f"\n✅ 完成")
