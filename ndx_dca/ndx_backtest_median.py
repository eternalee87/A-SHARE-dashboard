"""
模型对比: mean vs median 三因子分位值
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

def fmt(n, d=0): return f"{n:,.{d}f}" if n is not None else '—'
def pct2(n): return f"{n:+.2f}%" if n is not None else '—'
def wan(n): return f"{n/10000:.1f}万" if n is not None else '—'
def f500(x): return max(MIN_UNIT, int(x // MIN_UNIT) * MIN_UNIT)

# ==================== LOAD ====================
ndx = pd.read_csv(NDX_CSV, index_col=0, parse_dates=True)['close'].dropna()
vix = pd.read_csv(VIX_CSV, index_col=0, parse_dates=True)['close'].dropna()
with open(CNN_JSON, 'r', encoding='utf-8') as f:
    cnn_data = json.load(f)
cnn_lookup = {h['date']: h['score'] for h in cnn_data.get('history', [])}

common = ndx.index.intersection(vix.index).sort_values()
ma200 = ndx.rolling(200).mean()

def vix_to_cnn(v):
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

def score_from_percentile(pct):
    if pct < 5:   return -3
    if pct < 15:  return -2
    if pct < 30:  return -1
    if pct <= 70: return 0
    if pct <= 85: return 1
    if pct <= 95: return 2
    return 3

def mult_from_composite(c):
    if c < -2.0:   return 2.5
    elif c < -1.0: return 2.0
    elif c < -0.3: return 1.5
    elif c <= 0.3: return 1.0
    elif c <= 1.0: return 0.75
    elif c <= 2.0: return 0.5
    else:          return 0.25

# Pre-compute full percentile baselines
all_vix = []; all_ma = []; all_cnn = []
for dt in common:
    ds = dt.strftime('%Y-%m-%d')
    c = cnn_lookup.get(ds)
    if c is None: c = vix_to_cnn(vix.loc[dt] if dt in vix.index else None)
    all_vix.append(float(vix.loc[dt]) if dt in vix.index else 20.0)
    mr = float(ndx.loc[dt] / ma200.loc[dt]) if dt in ma200.index and not np.isnan(ma200.loc[dt]) else 1.0
    all_ma.append(mr)
    all_cnn.append(float(c))
all_vix = np.array(all_vix); all_ma = np.array(all_ma); all_cnn = np.array(all_cnn)

# ==================== BACKTEST ====================
def backtest_median_vs_mean(start_year):
    start_date = f"{start_year}-01-01"
    td = common[common >= start_date]
    if len(td) == 0: return None

    inv_m = inv_d = 0.0; sh_m = sh_d = 0.0  # m=median, d=mean
    recs_m = []; recs_d = []

    for i, dt in enumerate(td):
        ndx_cur = ndx.loc[dt]
        vix_cur = vix.loc[dt] if dt in vix.index else None
        dt_str = dt.strftime('%Y-%m-%d')
        
        mr = 1.0
        if dt in ma200.index and not np.isnan(ma200.loc[dt]):
            mr = ndx_cur / ma200.loc[dt]
        
        fng = cnn_lookup.get(dt_str)
        if fng is None: fng = vix_to_cnn(vix_cur)
        
        p_vix = (all_vix <= vix_cur).sum() / len(all_vix) * 100 if vix_cur else 50
        p_ma = (all_ma <= mr).sum() / len(all_ma) * 100
        p_cnn = (all_cnn <= fng).sum() / len(all_cnn) * 100
        
        s1 = score_from_percentile(100 - p_vix)
        s2 = score_from_percentile(p_ma)
        s3 = score_from_percentile(p_cnn)
        
        comp_mean = round((s1 + s2 + s3) / 3, 2)
        comp_median = float(np.median([s1, s2, s3]))
        
        mult_m = mult_from_composite(comp_median)
        mult_d = mult_from_composite(comp_mean)
        
        amt_m = f500(BASE_DAILY * mult_m)
        amt_d = f500(BASE_DAILY * mult_d)
        
        sh_m += amt_m / ndx_cur; inv_m += amt_m
        sh_d += amt_d / ndx_cur; inv_d += amt_d
        
        recs_m.append({'date': dt, 'year': dt.year, 'invested': amt_m,
                       'cum_inv': inv_m, 'ndx': ndx_cur, 'shares': sh_m,
                       'mktval': sh_m * ndx_cur, 'composite': comp_median})
        recs_d.append({'date': dt, 'year': dt.year, 'invested': amt_d,
                       'cum_inv': inv_d, 'ndx': ndx_cur, 'shares': sh_d,
                       'mktval': sh_d * ndx_cur, 'composite': comp_mean})

    def summ(recs, label):
        df = pd.DataFrame(recs)
        y = (df['date'].iloc[-1] - df['date'].iloc[0]).days / 365.25
        inv = df['invested'].sum()
        fv = df['mktval'].iloc[-1]
        cagr = ((fv / inv) ** (1 / y) - 1) * 100 if y > 0 else 0
        vals = df['mktval'].values
        peak = np.maximum.accumulate(vals)
        max_dd = float((vals / peak - 1).min()) * 100
        daily_min = df['invested'].min()
        daily_max = df['invested'].max()
        
        # Annual
        annual = df.groupby('year').agg(
            annual_invested=('invested', 'sum'),
            year_end_ndx=('ndx', 'last'),
            cum_invested=('cum_inv', 'last'),
            cum_shares=('shares', 'last'),
        ).reset_index()
        annual['cum_value'] = annual['cum_shares'] * annual['year_end_ndx']
        annual['cum_return_pct'] = (annual['cum_value'] / annual['cum_invested'] - 1) * 100
        
        # Multiplier distribution
        mults = {}
        for mk in [2.5, 2.0, 1.5, 1.0, 0.75, 0.5, 0.25]:
            mults[mk] = (df['invested'] == f500(BASE_DAILY * mk)).sum()
        
        return {
            'label': label, 'years': y, 'total_inv': inv, 'final_val': fv,
            'total_ret': (fv / inv - 1) * 100, 'cagr': cagr, 'max_dd': max_dd,
            'daily_min': daily_min, 'daily_max': daily_max,
            'annual': annual, 'mults': mults, 'total_10yr': inv,
        }
    
    return {
        'start_year': start_year,
        'start_date': td[0].strftime('%Y-%m-%d'),
        'end_date': td[-1].strftime('%Y-%m-%d'),
        'mean': summ(recs_d, 'Mean (当前)'),
        'median': summ(recs_m, 'Median (优化)'),
    }

# ==================== RUN ====================
print("=" * 100)
print("模型对比: Mean (等权平均) vs Median (中位数共识)")
print("=" * 100)

results = {}
for sy in START_YEARS:
    results[sy] = backtest_median_vs_mean(sy)

# ---- Summary table ----
print(f"\n{'起点':<6} {'模型':<16} {'年数':<5} {'10年投入':>10} {'总投入':>10} {'最终市值':>12} {'CAGR':>8} {'最大回撤':>8} {'日最低':>7} {'日最高':>7}")
print('─' * 100)
for sy in START_YEARS:
    r = results[sy]
    if r is None: continue
    for m in ['mean', 'median']:
        d = r[m]
        inv_10yr = d['annual'][d['annual']['year'] <= r['start_year'] + 9]['annual_invested'].sum() if len(d['annual']) > 0 else 0
        print(f"{sy:<6} {d['label']:<16} {d['years']:<5.1f} {wan(inv_10yr):>10} {wan(d['total_inv']):>10} {wan(d['final_val']):>12} {pct2(d['cagr']):>8} {pct2(d['max_dd']):>8} {fmt(d['daily_min'],0):>7} {fmt(d['daily_max'],0):>7}")
    print('─' * 100)

# ---- Multiplier distribution ----
print(f"\n\n{'='*100}")
print("📊 定投倍数分布 (全周期)")
print(f"{'='*100}")
labels_m = {2.5:'2.5x', 2.0:'2.0x', 1.5:'1.5x', 1.0:'1.0x', 0.75:'0.75x', 0.5:'0.5x', 0.25:'0.25x'}
for sy in START_YEARS:
    r = results[sy]
    if r is None: continue
    print(f"\n{sy}:")
    print(f"{'倍数':<8} {'Mean-天数':>10} {'Mean-%':>8} {'Median-天数':>12} {'Median-%':>8} {'差异':>8}")
    print('─' * 60)
    for mk in [2.5, 2.0, 1.5, 1.0, 0.75, 0.5, 0.25]:
        cm = r['mean']['mults'][mk]; cd = r['median']['mults'][mk]
        tm = len(r['mean']['annual']) * 250  # approximate
        td = len(r['median']['annual']) * 250
        print(f"{labels_m[mk]:<8} {cm:>10} {cm/tm*100:>7.1f}% {cd:>12} {cd/td*100:>7.1f}% {cd-cm:>+8}")

# ---- Yearly detail for 2006 (longest) ----
print(f"\n\n{'='*100}")
print("📅 2006起点逐年对比")
print(f"{'='*100}")
r0 = results[2006]
ann_m = r0['mean']['annual']; ann_d = r0['median']['annual']
print(f"{'年份':<6} {'Mean-年投(万)':>12} {'Median-年投(万)':>14} {'投差':>8} {'Mean-累计(万)':>13} {'Median-累计(万)':>13} {'Mean-收益':>10} {'Median-收益':>10}")
print('─' * 90)
for yr in sorted(set(ann_m['year'].tolist())):
    rm = ann_m[ann_m['year'] == yr]; rd = ann_d[ann_d['year'] == yr]
    ai = rm['annual_invested'].values[0]/10000 if len(rm)>0 else 0
    bi = rd['annual_invested'].values[0]/10000 if len(rd)>0 else 0
    ac = rm['cum_invested'].values[0]/10000 if len(rm)>0 else 0
    bc = rd['cum_invested'].values[0]/10000 if len(rd)>0 else 0
    ar = rm['cum_return_pct'].values[0] if len(rm)>0 else 0
    br = rd['cum_return_pct'].values[0] if len(rd)>0 else 0
    print(f"{yr:<6} {ai:>12.1f} {bi:>14.1f} {bi-ai:>+7.1f} {ac:>13.1f} {bc:>13.1f} {ar:>+9.2f}% {br:>+9.2f}%")

# ---- Scenario: today's signal comparison ----
print(f"\n\n{'='*100}")
print("📊 当前信号对比 (2026-07-16 数据)")
print(f"{'='*100}")
vix_cur = all_vix[-1]; ma_cur = all_ma[-1]; cnn_cur = all_cnn[-1]
p_vix = (all_vix <= vix_cur).sum() / len(all_vix) * 100
p_ma = (all_ma <= ma_cur).sum() / len(all_ma) * 100
p_cnn = (all_cnn <= cnn_cur).sum() / len(all_cnn) * 100
s1 = score_from_percentile(100 - p_vix)
s2 = score_from_percentile(p_ma)
s3 = score_from_percentile(p_cnn)
comp_mean = round((s1+s2+s3)/3, 2)
comp_median = float(np.median([s1, s2, s3]))
print(f"  VIX={vix_cur:.2f} p{p_vix:.1f} → s={s1:+d}")
print(f"  MA200={ma_cur:.4f} p{p_ma:.1f} → s={s2:+d}")
print(f"  CNN={cnn_cur:.1f} p{p_cnn:.1f} → s={s3:+d}")
print(f"  Mean:   ({s1:+d}+{s2:+d}+{s3:+d})/3 = {comp_mean:+.2f} → {mult_from_composite(comp_mean)}x → {f500(BASE_DAILY*mult_from_composite(comp_mean)):,} CNY")
print(f"  Median: median({s1:+d},{s2:+d},{s3:+d}) = {comp_median:+.0f} → {mult_from_composite(comp_median)}x → {f500(BASE_DAILY*mult_from_composite(comp_median)):,} CNY")

print(f"\n✅ 完成")
