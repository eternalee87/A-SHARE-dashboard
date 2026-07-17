"""
Mean vs Median 精细对比: 10年推演 + 至今全周期
"""
import sys, io, os, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import pandas as pd
import numpy as np

BASE = os.path.dirname(os.path.abspath(__file__))
NDX_CSV = os.path.join(BASE, 'data', 'ndx_data.csv')
VIX_CSV = os.path.join(BASE, 'data', 'vix_data.csv')
CNN_JSON = os.path.join(BASE, 'data', 'cnn_fng.json')

BASE_DAILY = 2000
MIN_UNIT = 500
START_YEARS = [2006, 2014, 2015, 2017, 2018]

ndx = pd.read_csv(NDX_CSV, index_col=0, parse_dates=True)['close'].dropna()
vix = pd.read_csv(VIX_CSV, index_col=0, parse_dates=True)['close'].dropna()
with open(CNN_JSON, 'r', encoding='utf-8') as f:
    cnn_data = json.load(f)
cnn_lookup = {h['date']: h['score'] for h in cnn_data.get('history', [])}

common = ndx.index.intersection(vix.index).sort_values()
ma200 = ndx.rolling(200).mean()

all_vix = []
all_ma = []
all_cnn = []
for dt in common:
    ds = dt.strftime('%Y-%m-%d')
    c = cnn_lookup.get(ds)
    if c is None:
        vv = vix.loc[dt] if dt in vix.index else None
        if vv is None or np.isnan(vv):
            c = 50
        elif vv > 40:
            c = 5
        elif vv > 35:
            c = 15
        elif vv > 30:
            c = 22
        elif vv > 28:
            c = 28
        elif vv > 25:
            c = 35
        elif vv > 22:
            c = 42
        elif vv > 20:
            c = 48
        elif vv > 18:
            c = 55
        elif vv > 16:
            c = 62
        elif vv > 14:
            c = 70
        elif vv > 12:
            c = 78
        else:
            c = 88
    all_vix.append(float(vix.loc[dt]) if dt in vix.index else 20.0)
    mr = float(ndx.loc[dt] / ma200.loc[dt]) if dt in ma200.index and not np.isnan(ma200.loc[dt]) else 1.0
    all_ma.append(mr)
    all_cnn.append(float(c))
all_vix = np.array(all_vix)
all_ma = np.array(all_ma)
all_cnn = np.array(all_cnn)


def score_from_pct(pct):
    if pct < 5: return -3
    if pct < 15: return -2
    if pct < 30: return -1
    if pct <= 70: return 0
    if pct <= 85: return 1
    if pct <= 95: return 2
    return 3


def mult_from_comp(c):
    if c < -2.0: return 2.5
    if c < -1.0: return 2.0
    if c < -0.3: return 1.5
    if c <= 0.3: return 1.0
    if c <= 1.0: return 0.75
    if c <= 2.0: return 0.5
    return 0.25


def f500(x):
    return max(MIN_UNIT, int(x // MIN_UNIT) * MIN_UNIT)


def cn(v):
    if v is None: return '—'
    return f"{v/10000:.1f}万"


def cp(v):
    if v is None: return '—'
    return f"{v:+.2f}%"


def ci(v):
    if v is None: return '—'
    return f"{v:,.0f}"


def backtest(sy, use_median):
    td = common[common >= f"{sy}-01-01"]
    if len(td) == 0:
        return None
    inv = 0.0
    sh = 0.0
    rows = []
    for dt in td:
        nc = ndx.loc[dt]
        vc = vix.loc[dt] if dt in vix.index else None
        mr = 1.0
        if dt in ma200.index and not np.isnan(ma200.loc[dt]):
            mr = nc / ma200.loc[dt]
        ds = dt.strftime('%Y-%m-%d')
        fng = cnn_lookup.get(ds)
        if fng is None:
            if vc is None or np.isnan(vc):
                fng = 50
            elif vc > 40:
                fng = 5
            elif vc > 35:
                fng = 15
            elif vc > 30:
                fng = 22
            elif vc > 28:
                fng = 28
            elif vc > 25:
                fng = 35
            elif vc > 22:
                fng = 42
            elif vc > 20:
                fng = 48
            elif vc > 18:
                fng = 55
            elif vc > 16:
                fng = 62
            elif vc > 14:
                fng = 70
            elif vc > 12:
                fng = 78
            else:
                fng = 88
        pv = (all_vix <= vc).sum() / len(all_vix) * 100 if vc else 50
        pm = (all_ma <= mr).sum() / len(all_ma) * 100
        pc = (all_cnn <= fng).sum() / len(all_cnn) * 100
        s1 = score_from_pct(100 - pv)
        s2 = score_from_pct(pm)
        s3 = score_from_pct(pc)
        if use_median:
            comp = float(np.median([s1, s2, s3]))
        else:
            comp = round((s1 + s2 + s3) / 3, 2)
        amt = f500(BASE_DAILY * mult_from_comp(comp))
        sh += amt / nc
        inv += amt
        rows.append({
            'date': dt, 'ndx': nc, 'invested': amt,
            'cum_inv': inv, 'shares': sh, 'mktval': sh * nc,
        })
    df = pd.DataFrame(rows)
    y = (df['date'].iloc[-1] - df['date'].iloc[0]).days / 365.25
    fv = df['mktval'].iloc[-1]
    cagr = ((fv / inv) ** (1 / y) - 1) * 100 if y > 0 else 0
    ret = (fv / inv - 1) * 100
    vals = df['mktval'].values
    peak = np.maximum.accumulate(vals)
    max_dd = float((vals / peak - 1).min()) * 100
    cutoff = df['date'].iloc[0] + pd.DateOffset(years=10)
    d10 = df[df['date'] <= cutoff]
    if len(d10) > 0:
        inv10 = d10['invested'].sum()
        fv10 = d10['mktval'].iloc[-1]
        y10 = (d10['date'].iloc[-1] - d10['date'].iloc[0]).days / 365.25
        cagr10 = ((fv10 / inv10) ** (1 / y10) - 1) * 100 if y10 > 0 and inv10 > 0 else 0
        ret10 = (fv10 / inv10 - 1) * 100 if inv10 > 0 else 0
        v10 = d10['mktval'].values
        p10 = np.maximum.accumulate(v10)
        dd10 = float((v10 / p10 - 1).min()) * 100
    else:
        inv10 = fv10 = cagr10 = ret10 = dd10 = None
    daily_min = int(df['invested'].min())
    daily_max = int(df['invested'].max())
    return {
        'total_inv': inv, 'final_val': fv, 'cagr': cagr, 'ret': ret,
        'max_dd': max_dd, 'daily_min': daily_min, 'daily_max': daily_max,
        'inv10': inv10, 'fv10': fv10, 'cagr10': cagr10, 'ret10': ret10,
        'dd10': dd10,
    }


# ==================== PRINT ====================
print("=" * 110)
print("  Mean vs Median 完整推演对比")
print("=" * 110)

for label, use_median in [("Mean (等权平均 - 当前模型)", False), ("Median (中位数共识 - 优化建议)", True)]:
    print(f"\n{'─' * 110}")
    print(f"  {label}")
    print(f"{'─' * 110}")

    print(f"\n  📅 10年推演")
    print(f"  {'起点':<6} {'10年投入':>9} {'10年市值':>10} {'年化CAGR':>8} {'累计收益率':>10} {'最大回撤':>8} {'日最低':>7} {'日最高':>7}")
    print(f"  {'─' * 6} {'─' * 9} {'─' * 10} {'─' * 8} {'─' * 10} {'─' * 8} {'─' * 7} {'─' * 7}")
    for sy in START_YEARS:
        r = backtest(sy, use_median)
        if r is None: continue
        print(f"  {sy:<6} {cn(r['inv10']):>9} {cn(r['fv10']):>10} {cp(r['cagr10']):>8} {cp(r['ret10']):>10} {cp(r['dd10']):>8} {ci(r['daily_min']):>7} {ci(r['daily_max']):>7}")

    print(f"\n  📅 全周期 (至 2026-07-16)")
    print(f"  {'起点':<6} {'累计投入':>9} {'最新市值':>10} {'年化CAGR':>8} {'累计收益率':>10} {'最大回撤':>8} {'日最低':>7} {'日最高':>7}")
    print(f"  {'─' * 6} {'─' * 9} {'─' * 10} {'─' * 8} {'─' * 10} {'─' * 8} {'─' * 7} {'─' * 7}")
    for sy in START_YEARS:
        r = backtest(sy, use_median)
        if r is None: continue
        print(f"  {sy:<6} {cn(r['total_inv']):>9} {cn(r['final_val']):>10} {cp(r['cagr']):>8} {cp(r['ret']):>10} {cp(r['max_dd']):>8} {ci(r['daily_min']):>7} {ci(r['daily_max']):>7}")

# ==================== DELTA ====================
print(f"\n\n{'=' * 110}")
print("  Mean vs Median 差异 (Median - Mean)")
print(f"{'=' * 110}")

for period, ki, kf, kc, kr, kd in [
    ("10年推演", 'inv10', 'fv10', 'cagr10', 'ret10', 'dd10'),
    ("全周期", 'total_inv', 'final_val', 'cagr', 'ret', 'max_dd'),
]:
    print(f"\n  {period}:")
    print(f"  {'起点':<6} {'Δ投入':>9} {'Δ市值':>10} {'ΔCAGR':>8} {'Δ累计收益':>10} {'Δ最大回撤':>8}")
    print(f"  {'─' * 6} {'─' * 9} {'─' * 10} {'─' * 8} {'─' * 10} {'─' * 8}")
    for sy in START_YEARS:
        rm = backtest(sy, False)
        rd = backtest(sy, True)
        if rm is None or rd is None: continue
        di = rd[ki] - rm[ki] if rd[ki] is not None and rm[ki] is not None else None
        dv = rd[kf] - rm[kf] if rd[kf] is not None and rm[kf] is not None else None
        dc = rd[kc] - rm[kc] if rd[kc] is not None and rm[kc] is not None else None
        dr = rd[kr] - rm[kr] if rd[kr] is not None and rm[kr] is not None else None
        dd_ = rd[kd] - rm[kd] if rd[kd] is not None and rm[kd] is not None else None
        print(f"  {sy:<6} {cn(di):>9} {cn(dv):>10} {cp(dc):>8} {cp(dr):>10} {cp(dd_):>8}")

print(f"\n✅ 完成")
