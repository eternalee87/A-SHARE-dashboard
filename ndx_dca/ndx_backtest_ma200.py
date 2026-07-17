"""
Median (3-factor consensus) vs MA200-only (single factor)
"""
import sys, io, os, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import pandas as pd, numpy as np

BASE = os.path.dirname(os.path.abspath(__file__))
ndx = pd.read_csv(f'{BASE}/data/ndx_data.csv', index_col=0, parse_dates=True)['close'].dropna()
vix = pd.read_csv(f'{BASE}/data/vix_data.csv', index_col=0, parse_dates=True)['close'].dropna()
with open(f'{BASE}/data/cnn_fng.json', 'r') as f: cnn = json.load(f)
cnn_lookup = {h['date']: h['score'] for h in cnn.get('history', [])}

common = ndx.index.intersection(vix.index).sort_values()
ma200 = ndx.rolling(200).mean()

def proxy_cnn(v):
    if v is None or np.isnan(v): return 50
    if v > 40: return 5
    if v > 35: return 15
    if v > 30: return 22
    if v > 28: return 28
    if v > 25: return 35
    if v > 22: return 42
    if v > 20: return 48
    if v > 18: return 55
    if v > 16: return 62
    if v > 14: return 70
    if v > 12: return 78
    return 88

# Pre-compute all baselines
all_v = []; all_m = []; all_c = []
for dt in common:
    vv = float(vix.loc[dt]) if dt in vix.index else 20.0
    mr = float(ndx.loc[dt] / ma200.loc[dt]) if dt in ma200.index and not np.isnan(ma200.loc[dt]) else 1.0
    cc = cnn_lookup.get(dt.strftime('%Y-%m-%d'))
    if cc is None: cc = proxy_cnn(vv)
    all_v.append(vv); all_m.append(mr); all_c.append(float(cc))
all_v = np.array(all_v); all_m = np.array(all_m); all_c = np.array(all_c)

def sc(p):
    if p < 5: return -3
    if p < 15: return -2
    if p < 30: return -1
    if p <= 70: return 0
    if p <= 85: return 1
    if p <= 95: return 2
    return 3

def mult(c):
    if c < -2.0: return 2.5
    if c < -1.0: return 2.0
    if c < -0.3: return 1.5
    if c <= 0.3: return 1.0
    if c <= 1.0: return 0.75
    if c <= 2.0: return 0.5
    return 0.25

B = 2000; U = 500
def f500(x): return max(U, int(x // U) * U)
def wan(v): return f'{v/10000:.1f}万' if v else '—'
def pct(v): return f'{v:+.2f}%' if v is not None else '—'

def backtest(sy, mode):
    td = common[common >= f'{sy}-01-01']
    if len(td) == 0: return None
    inv = 0.0; sh = 0.0; rows = []
    for dt in td:
        nc = ndx.loc[dt]; vc = vix.loc[dt] if dt in vix.index else None
        mr = 1.0
        if dt in ma200.index and not np.isnan(ma200.loc[dt]):
            mr = nc / ma200.loc[dt]
        ds = dt.strftime('%Y-%m-%d')
        fng = cnn_lookup.get(ds)
        if fng is None: fng = proxy_cnn(vc)

        if mode == 'ma200':
            p_m = (all_m <= mr).sum() / len(all_m) * 100
            comp = float(sc(p_m))
        else:  # median
            p_v = (all_v <= vc).sum() / len(all_v) * 100 if vc else 50
            p_m = (all_m <= mr).sum() / len(all_m) * 100
            p_c = (all_c <= fng).sum() / len(all_c) * 100
            s1 = sc(100 - p_v)
            s2 = sc(p_m)
            s3 = sc(p_c)
            comp = float(np.median([s1, s2, s3]))

        amt = f500(B * mult(comp))
        sh += amt / nc; inv += amt
        rows.append({
            'date': dt, 'ndx': nc, 'invested': amt,
            'cum_inv': inv, 'shares': sh, 'mktval': sh * nc,
        })
    df = pd.DataFrame(rows)
    y = (df['date'].iloc[-1] - df['date'].iloc[0]).days / 365.25
    fv = df['mktval'].iloc[-1]
    cagr = ((fv / inv) ** (1 / y) - 1) * 100 if y > 0 and inv > 0 else 0
    ret = (fv / inv - 1) * 100 if inv > 0 else 0
    vals = df['mktval'].values; peak = np.maximum.accumulate(vals)
    dd = float((vals / peak - 1).min()) * 100

    cutoff = df['date'].iloc[0] + pd.DateOffset(years=10)
    d10 = df[df['date'] <= cutoff]
    if len(d10) > 0:
        i10 = d10['invested'].sum(); f10 = d10['mktval'].iloc[-1]
        y10 = (d10['date'].iloc[-1] - d10['date'].iloc[0]).days / 365.25
        c10 = ((f10 / i10) ** (1 / y10) - 1) * 100 if y10 > 0 and i10 > 0 else 0
        r10 = (f10 / i10 - 1) * 100 if i10 > 0 else 0
        v10 = d10['mktval'].values; p10 = np.maximum.accumulate(v10)
        dd10 = float((v10 / p10 - 1).min()) * 100
    else:
        i10 = f10 = c10 = r10 = dd10 = None

    d_min = int(df['invested'].min()); d_max = int(df['invested'].max())
    # Multiplier distribution
    mdist = {}
    for mk in [2.5, 2.0, 1.5, 1.0, 0.75, 0.5, 0.25]:
        mdist[mk] = int((df['invested'] == f500(B * mk)).sum())

    return {
        'inv': inv, 'fv': fv, 'cagr': cagr, 'ret': ret, 'dd': dd,
        'dmin': d_min, 'dmax': d_max, 'days': len(df),
        'i10': i10, 'f10': f10, 'c10': c10, 'r10': r10, 'dd10': dd10,
        'mdist': mdist,
    }


# ==================== PRINT ====================
START = [2006, 2014, 2015, 2017, 2018]

print("=" * 115)
print("  Median (三因子中位数共识) vs MA200-only (单因子NDX/MA200分位值)")
print("=" * 115)

for label, mode in [("Median 三因子共识", "median"), ("MA200-Only 单因子", "ma200")]:
    print(f"\n{'─' * 115}")
    print(f"  {label}")
    print(f"{'─' * 115}")

    print(f"\n  📅 10年推演")
    print(f"  {'起点':<6} {'10年投入':>9} {'10年市值':>10} {'年化CAGR':>8} {'累计收益':>10} {'最大回撤':>8}")
    print(f"  {'─' * 6} {'─' * 9} {'─' * 10} {'─' * 8} {'─' * 10} {'─' * 8}")
    for sy in START:
        r = backtest(sy, mode)
        if r is None: continue
        print(f"  {sy:<6} {wan(r['i10']):>9} {wan(r['f10']):>10} {pct(r['c10']):>8} {pct(r['r10']):>10} {pct(r['dd10']):>8}")

    print(f"\n  📅 全周期")
    print(f"  {'起点':<6} {'累计投入':>9} {'最新市值':>10} {'年化CAGR':>8} {'累计收益':>10} {'最大回撤':>8} {'日低':>6} {'日高':>6}")
    print(f"  {'─' * 6} {'─' * 9} {'─' * 10} {'─' * 8} {'─' * 10} {'─' * 8} {'─' * 6} {'─' * 6}")
    for sy in START:
        r = backtest(sy, mode)
        if r is None: continue
        print(f"  {sy:<6} {wan(r['inv']):>9} {wan(r['fv']):>10} {pct(r['cagr']):>8} {pct(r['ret']):>10} {pct(r['dd']):>8} {r['dmin']:>6} {r['dmax']:>6}")

# ---- Multiplier distribution ----
print(f"\n\n{'=' * 115}")
print("  📊 倍数分布对比 (2006起点全周期)")
print(f"{'=' * 115}")
r_med = backtest(2006, 'median')
r_ma = backtest(2006, 'ma200')
print(f"  {'倍数':<8} {'Median-天数':>12} {'Median-%':>9} {'MA200-天数':>12} {'MA200-%':>9}")
print(f"  {'─' * 8} {'─' * 12} {'─' * 9} {'─' * 12} {'─' * 9}")
for mk in [2.5, 2.0, 1.5, 1.0, 0.75, 0.5, 0.25]:
    cm = r_med['mdist'][mk]; ca = r_ma['mdist'][mk]
    print(f"  {f'{mk}x':<8} {cm:>12} {cm/r_med['days']*100:>8.1f}% {ca:>12} {ca/r_ma['days']*100:>8.1f}%")

# ---- Crisis check ----
print(f"\n\n{'=' * 115}")
print("  📊 危机年份单日最高")
print(f"{'=' * 115}")
for yr in [2008, 2020, 2022]:
    for mode, name in [('median', 'Median'), ('ma200', 'MA200')]:
        r = backtest(yr, mode)
        print(f"  {yr} {name}: 最高单日 {r['dmax']:,} CNY")

print(f"\n✅ 完成")
