"""
双模型对比回测: 4因子等权 vs CNN/VIX分位值
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
START_YEARS = [2006, 2008, 2014, 2017]

# ==================== HELPERS ====================
def fmt(n, d=0):
    if n is None: return '—'
    return f"{n:,.{d}f}"

def pct2(n):
    if n is None: return '—'
    return f"{n:+.2f}%"

def wan(n):
    if n is None: return '—'
    return f"{n/10000:.1f}万"

def floor500(x):
    return max(MIN_UNIT, int(x // MIN_UNIT) * MIN_UNIT)

# ==================== SCORING: MODEL A (4-factor equal weight) ====================
def score_daily_change(pct):
    p = pct * 100
    if p < -3: return -3
    if p < -2: return -2
    if p < -1: return -1
    if p <= 1: return 0
    if p <= 2: return 1
    if p <= 3: return 2
    return 3

def score_vix(v):
    if v is None or np.isnan(v): return 0
    if v > 45: return -3
    if v > 35: return -2
    if v > 28: return -1
    if v >= 18: return 0
    if v >= 14: return 1
    if v >= 11: return 2
    return 3

def score_ma200_ratio(r):
    if r is None or np.isnan(r): return 0
    if r < 0.80: return -3
    if r < 0.88: return -2
    if r < 0.95: return -1
    if r <= 1.05: return 0
    if r <= 1.15: return 1
    if r <= 1.25: return 2
    return 3

def score_cnn_fng(f):
    if f is None: return 0
    if f < 15: return -3
    if f < 25: return -2
    if f < 35: return -1
    if f <= 55: return 0
    if f <= 65: return 1
    if f <= 80: return 2
    return 3

def mult_from_composite(c):
    if c < -2.0:   return 2.5
    elif c < -1.0: return 2.0
    elif c < -0.3: return 1.5
    elif c <= 0.3: return 1.0
    elif c <= 1.0: return 0.75
    elif c <= 2.0: return 0.5
    else:          return 0.25

# ==================== SCORING: MODEL B (CNN/VIX percentile) ====================
# Pre-compute the full historical CNN/VIX ratio distribution
# We'll use expanding percentile (only lookback, no future peeking)

def vix_to_cnn_proxy(v):
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

def mult_from_percentile(pct_rank):
    """CNN/VIX ratio percentile → DCA multiplier.
    Lower percentile = lower ratio = more fear = undervalued = higher multiplier.
    """
    if pct_rank < 10:   return 2.5   # extreme fear
    elif pct_rank < 25: return 2.0
    elif pct_rank < 40: return 1.5
    elif pct_rank < 60: return 1.0   # neutral middle band
    elif pct_rank < 75: return 0.75
    elif pct_rank < 90: return 0.5
    else:               return 0.25  # extreme greed

# ==================== LOAD DATA ====================
print("Loading data...")
ndx = pd.read_csv(NDX_CSV, index_col=0, parse_dates=True)['close'].dropna()
vix = pd.read_csv(VIX_CSV, index_col=0, parse_dates=True)['close'].dropna()

with open(CNN_JSON, 'r', encoding='utf-8') as f:
    cnn_data = json.load(f)
cnn_lookup = {h['date']: h['score'] for h in cnn_data.get('history', [])}

# Common dates
common = ndx.index.intersection(vix.index).sort_values()
print(f"Common trading days: {len(common)}, {common[0].date()} ~ {common[-1].date()}")

# Pre-compute MA200 and CNN/VIX ratios for all dates
ma200 = ndx.rolling(200).mean()

# Build CNN/VIX ratio series with proxy
cnn_vix_ratios = []
for dt in common:
    ds = dt.strftime('%Y-%m-%d')
    c = cnn_lookup.get(ds)
    if c is None:
        c = vix_to_cnn_proxy(vix.loc[dt])
    r = c / vix.loc[dt]
    cnn_vix_ratios.append(r)
cnn_vix_ratios = pd.Series(cnn_vix_ratios, index=common)

# ==================== BACKTEST ENGINE ====================
def backtest_dual(start_year):
    """Run both models side-by-side from start_year."""
    start_date = f"{start_year}-01-01"
    trade_dates = common[common >= start_date]
    if len(trade_dates) == 0:
        return None

    # ---- Model A state ----
    inv_a = 0; shares_a = 0
    recs_a = []
    
    # ---- Model B state (expanding percentile) ----
    inv_b = 0; shares_b = 0
    recs_b = []
    ratio_history = []

    for i, dt in enumerate(trade_dates):
        ndx_cur = ndx.loc[dt]
        vix_cur = vix.loc[dt] if dt in vix.index else None
        
        # Daily change
        if i > 0:
            pct_chg = (ndx_cur / ndx.loc[trade_dates[i-1]]) - 1
        else:
            pct_chg = 0
        
        # MA200 ratio
        mr = 1.0
        if dt in ma200.index and not np.isnan(ma200.loc[dt]):
            mr = ndx_cur / ma200.loc[dt]
        
        # CNN F&G
        dt_str = dt.strftime('%Y-%m-%d')
        fng = cnn_lookup.get(dt_str)
        if fng is None:
            fng = vix_to_cnn_proxy(vix_cur)
        
        # --- Model A: 4-factor equal weight ---
        s1 = score_daily_change(pct_chg)
        s2 = score_vix(vix_cur)
        s3 = score_ma200_ratio(mr)
        s4 = score_cnn_fng(fng)
        comp_a = (s1 + s2 + s3 + s4) / 4
        mult_a = mult_from_composite(comp_a)
        amt_a = floor500(BASE_DAILY * mult_a)
        
        shares_a += amt_a / ndx_cur
        inv_a += amt_a
        
        recs_a.append({
            'date': dt, 'year': dt.year, 'invested': amt_a,
            'cum_invested': inv_a, 'ndx_close': ndx_cur,
            'total_shares': shares_a, 'market_value': shares_a * ndx_cur,
        })
        
        # --- Model B: CNN/VIX percentile ---
        cur_ratio = fng / vix_cur if vix_cur else 3.5
        ratio_history.append(cur_ratio)
        
        if len(ratio_history) >= 252:  # need at least 1 year for meaningful percentile
            pct_rank = (np.array(ratio_history) < cur_ratio).sum() / len(ratio_history) * 100
        else:
            pct_rank = 50  # neutral when insufficient data
        
        mult_b = mult_from_percentile(pct_rank)
        amt_b = floor500(BASE_DAILY * mult_b)
        
        shares_b += amt_b / ndx_cur
        inv_b += amt_b
        
        recs_b.append({
            'date': dt, 'year': dt.year, 'invested': amt_b,
            'cum_invested': inv_b, 'ndx_close': ndx_cur,
            'total_shares': shares_b, 'market_value': shares_b * ndx_cur,
            'pct_rank': pct_rank,
        })

    def summarize(recs, label):
        df = pd.DataFrame(recs)
        years_elapsed = (df['date'].iloc[-1] - df['date'].iloc[0]).days / 365.25
        total_inv = df['invested'].sum()
        final_val = df['market_value'].iloc[-1]
        cagr = ((final_val / total_inv) ** (1 / years_elapsed) - 1) * 100 if years_elapsed > 0 else 0
        
        vals = df['market_value'].values
        peak = np.maximum.accumulate(vals)
        max_dd = float((vals / peak - 1).min()) * 100
        
        # Annual
        annual = df.groupby('year').agg(
            annual_invested=('invested', 'sum'),
            year_end_ndx=('ndx_close', 'last'),
            cum_invested=('cum_invested', 'last'),
            cum_shares=('total_shares', 'last'),
        ).reset_index()
        annual['cum_value'] = annual['cum_shares'] * annual['year_end_ndx']
        annual['cum_return_pct'] = (annual['cum_value'] / annual['cum_invested'] - 1) * 100
        
        return {
            'label': label, 'years': years_elapsed, 'days': len(df),
            'total_inv': total_inv, 'final_val': final_val,
            'pnl': final_val - total_inv,
            'total_ret': (final_val / total_inv - 1) * 100,
            'cagr': cagr, 'max_dd': max_dd,
            'annual': annual, '_df': df,
        }
    
    return {
        'start_year': start_year,
        'start_date': trade_dates[0].strftime('%Y-%m-%d'),
        'end_date': trade_dates[-1].strftime('%Y-%m-%d'),
        'A': summarize(recs_a, '4因子等权'),
        'B': summarize(recs_b, 'CNN/VIX分位'),
    }


# ==================== RUN ====================
print("\n" + "=" * 90)
print("双模型对比回测: 4因子等权 vs CNN/VIX分位值")
print("=" * 90)

results = {}
for sy in START_YEARS:
    r = backtest_dual(sy)
    if r:
        results[sy] = r

# ==================== COMPARISON TABLE ====================
print(f"\n{'起点':<6} {'模型':<14} {'年数':<6} {'总投入':>10} {'最终市值':>12} {'总收益率':>10} {'CAGR':>9} {'最大回撤':>9}")
print(f"{'─'*6} {'─'*14} {'─'*6} {'─'*10} {'─'*12} {'─'*10} {'─'*9} {'─'*9}")

for sy in START_YEARS:
    r = results.get(sy)
    if r is None: continue
    for m in ['A', 'B']:
        d = r[m]
        print(f"{sy:<6} {d['label']:<14} {d['years']:<6.1f} {wan(d['total_inv']):>10} {wan(d['final_val']):>12} {pct2(d['total_ret']):>10} {pct2(d['cagr']):>9} {pct2(d['max_dd']):>9}")
    print(f"{'─'*6} {'─'*14} {'─'*6} {'─'*10} {'─'*12} {'─'*10} {'─'*9} {'─'*9}")

# ==================== YEARLY DETAIL FOR EACH START ====================
for sy in START_YEARS:
    r = results.get(sy)
    if r is None: continue
    
    print(f"\n\n{'─'*90}")
    print(f"📅 起点 {sy} 逐年对比")
    print(f"{'─'*90}")
    
    ann_a = r['A']['annual']
    ann_b = r['B']['annual']
    
    print(f"{'年份':<6} {'A-年投(万)':>10} {'B-年投(万)':>10} {'投差':>8} {'A-累计(万)':>11} {'B-累计(万)':>11} {'A-收益率':>9} {'B-收益率':>9}")
    print(f"{'─'*6} {'─'*10} {'─'*10} {'─'*8} {'─'*11} {'─'*11} {'─'*9} {'─'*9}")
    
    for yr in sorted(set(ann_a['year'].tolist() + ann_b['year'].tolist())):
        ra = ann_a[ann_a['year'] == yr]
        rb = ann_b[ann_b['year'] == yr]
        ai = ra['annual_invested'].values[0]/10000 if len(ra)>0 else 0
        bi = rb['annual_invested'].values[0]/10000 if len(rb)>0 else 0
        ac = ra['cum_invested'].values[0]/10000 if len(ra)>0 else 0
        bc = rb['cum_invested'].values[0]/10000 if len(rb)>0 else 0
        ar = ra['cum_return_pct'].values[0] if len(ra)>0 else 0
        br = rb['cum_return_pct'].values[0] if len(rb)>0 else 0
        diff = ai - bi
        print(f"{yr:<6} {ai:>10.1f} {bi:>10.1f} {diff:>+7.1f} {ac:>11.1f} {bc:>11.1f} {ar:>+8.2f}% {br:>+8.2f}%")

# ==================== DELTA SUMMARY ====================
print(f"\n\n{'='*90}")
print("📊 差异汇总 (B - A)")
print(f"{'='*90}")
print(f"{'起点':<6} {'Δ总投入(万)':>12} {'Δ最终市值(万)':>12} {'ΔCAGR':>9} {'Δ最大回撤':>9}")
print(f"{'─'*6} {'─'*12} {'─'*12} {'─'*9} {'─'*9}")
for sy in START_YEARS:
    r = results.get(sy)
    if r is None: continue
    d_inv = (r['B']['total_inv'] - r['A']['total_inv']) / 10000
    d_val = (r['B']['final_val'] - r['A']['final_val']) / 10000
    d_cagr = r['B']['cagr'] - r['A']['cagr']
    d_dd = r['B']['max_dd'] - r['A']['max_dd']
    print(f"{sy:<6} {d_inv:>+12.1f} {d_val:>+12.1f} {d_cagr:>+8.2f}% {d_dd:>+8.2f}%")

# ==================== MULTIPLIER DISTRIBUTION ====================
print(f"\n\n{'='*90}")
print("📊 定投倍数分布对比")
print(f"{'='*90}")
labels = {2.5: '2.5x极低', 2.0: '2.0x低', 1.5: '1.5x偏低', 1.0: '1.0x中性', 0.75: '0.75x偏高', 0.5: '0.5x高', 0.25: '0.25x极高'}
for sy in START_YEARS:
    r = results.get(sy)
    if r is None: continue
    print(f"\n{sy}:")
    print(f"{'倍数':<12} {'A-4因子等权':>15} {'B-CNN/VIX分位':>15}")
    print(f"{'─'*12} {'─'*15} {'─'*15}")
    
    for mkey in [2.5, 2.0, 1.5, 1.0, 0.75, 0.5, 0.25]:
        df_a = r['A']['_df']
        df_b = r['B']['_df']
        
        # Model A: derive mult from composite
        df_a2 = df_a.copy()
        df_a2['mult'] = df_a2.apply(
            lambda row: mult_from_composite(
                (score_daily_change(
                    (row['ndx_close'] / df_a2['ndx_close'].shift(1).loc[row.name] - 1) 
                     if row.name != df_a2.index[0] else 0)
                ) / 4  # simplified
            ), axis=1
        )
        
        # Simpler: just count based on invested amount
        mask_a = df_a['invested'] == floor500(BASE_DAILY * mkey)
        mask_b = df_b['invested'] == floor500(BASE_DAILY * mkey)
        
        ca = mask_a.sum()
        cb = mask_b.sum()
        pa = ca / len(df_a) * 100
        pb = cb / len(df_b) * 100
        
        print(f"{labels[mkey]:<12} {ca:>4}天 {pa:>5.1f}%    {cb:>4}天 {pb:>5.1f}%")

print(f"\n✅ 回测完成")
