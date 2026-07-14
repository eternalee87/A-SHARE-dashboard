"""
三模型对比: 
  A - 四因子绝对值 (当前)
  B - CNN/VIX分位值
  C - 三因子分位值 (VIX分位 + NDX/MA200分位 + CNN分位 → 等权)
+ 20年估值分区时间线
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

def fmt(n, d=0): return f"{n:,.{d}f}" if n is not None else '—'
def pct2(n): return f"{n:+.2f}%" if n is not None else '—'
def wan(n): return f"{n/10000:.1f}万" if n is not None else '—'
def f500(x): return max(MIN_UNIT, int(x // MIN_UNIT) * MIN_UNIT)

# ==================== LOAD ====================
print("Loading data...")
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

# ==================== SCORING HELPERS ====================
def score_from_percentile(pct):
    """Percentile (0-100) → score (-3 to +3), fat-tail design"""
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

# ==================== MODEL A: 4-factor absolute ====================
def score_daily_change(pct):
    p = pct * 100
    if p < -3: return -3
    if p < -2: return -2
    if p < -1: return -1
    if p <= 1: return 0
    if p <= 2: return 1
    if p <= 3: return 2
    return 3

def score_vix_abs(v):
    if v is None or np.isnan(v): return 0
    if v > 45: return -3
    if v > 35: return -2
    if v > 28: return -1
    if v >= 18: return 0
    if v >= 14: return 1
    if v >= 11: return 2
    return 3

def score_ma200_abs(r):
    if r is None or np.isnan(r): return 0
    if r < 0.80: return -3
    if r < 0.88: return -2
    if r < 0.95: return -1
    if r <= 1.05: return 0
    if r <= 1.15: return 1
    if r <= 1.25: return 2
    return 3

def score_cnn_abs(f):
    if f is None: return 0
    if f < 15: return -3
    if f < 25: return -2
    if f < 35: return -1
    if f <= 55: return 0
    if f <= 65: return 1
    if f <= 80: return 2
    return 3

def mult_from_percentile(pct):
    """Model B: CNN/VIX percentile → multiplier"""
    if pct < 10:   return 2.5
    elif pct < 25: return 2.0
    elif pct < 40: return 1.5
    elif pct < 60: return 1.0
    elif pct < 75: return 0.75
    elif pct < 90: return 0.5
    else:          return 0.25

# ==================== BACKTEST (all 3 models) ====================
def backtest_triple(start_year):
    start_date = f"{start_year}-01-01"
    td = common[common >= start_date]
    if len(td) == 0: return None

    inv_a = inv_b = inv_c = 0.0
    sh_a = sh_b = sh_c = 0.0
    recs_a, recs_b, recs_c = [], [], []
    
    # For Model B & C: maintain expanding histories
    ratios_b = []   # CNN/VIX for B
    pcts_vix = []   # VIX for C
    pcts_ma = []    # MA200 ratio for C
    pcts_cnn = []   # CNN for C

    for i, dt in enumerate(td):
        ndx_cur = ndx.loc[dt]
        vix_cur = vix.loc[dt] if dt in vix.index else None
        dt_str = dt.strftime('%Y-%m-%d')
        
        pct_chg = 0
        if i > 0:
            pct_chg = (ndx_cur / ndx.loc[td[i-1]]) - 1
        
        mr = 1.0
        if dt in ma200.index and not np.isnan(ma200.loc[dt]):
            mr = ndx_cur / ma200.loc[dt]
        
        fng = cnn_lookup.get(dt_str)
        if fng is None:
            fng = vix_to_cnn(vix_cur)
        
        # --- MODEL A: 4-factor absolute ---
        sa1 = score_daily_change(pct_chg)
        sa2 = score_vix_abs(vix_cur)
        sa3 = score_ma200_abs(mr)
        sa4 = score_cnn_abs(fng)
        comp_a = (sa1 + sa2 + sa3 + sa4) / 4
        mult_a = mult_from_composite(comp_a)
        amt_a = f500(BASE_DAILY * mult_a)
        sh_a += amt_a / ndx_cur
        inv_a += amt_a
        recs_a.append({'date': dt, 'year': dt.year, 'invested': amt_a,
                       'cum_inv': inv_a, 'ndx': ndx_cur, 'shares': sh_a,
                       'mktval': sh_a * ndx_cur, 'composite': comp_a, 'vix': vix_cur, 'ma_ratio': mr, 'cnn': fng})
        
        # --- MODEL B: CNN/VIX percentile ---
        cur_ratio = fng / vix_cur if vix_cur else 3.5
        ratios_b.append(cur_ratio)
        if len(ratios_b) >= 252:
            pct_b = (np.array(ratios_b) < cur_ratio).sum() / len(ratios_b) * 100
        else:
            pct_b = 50
        mult_b = mult_from_percentile(pct_b)
        amt_b = f500(BASE_DAILY * mult_b)
        sh_b += amt_b / ndx_cur
        inv_b += amt_b
        recs_b.append({'date': dt, 'year': dt.year, 'invested': amt_b,
                       'cum_inv': inv_b, 'ndx': ndx_cur, 'shares': sh_b,
                       'mktval': sh_b * ndx_cur, 'pct_rank': pct_b})
        
        # --- MODEL C: 3-factor expanding percentile ---
        pcts_vix.append(vix_cur if vix_cur else 20)
        pcts_ma.append(mr)
        pcts_cnn.append(fng)
        
        if len(pcts_vix) >= 252:
            # VIX: higher VIX = higher percentile = more fear → negative score
            p_vix = (np.array(pcts_vix) <= vix_cur).sum() / len(pcts_vix) * 100 if vix_cur else 50
            # MA200 ratio: higher = higher percentile → positive score
            p_ma = (np.array(pcts_ma) <= mr).sum() / len(pcts_ma) * 100
            # CNN: higher = higher percentile → positive (greed) score
            p_cnn = (np.array(pcts_cnn) <= fng).sum() / len(pcts_cnn) * 100
        else:
            p_vix = p_ma = p_cnn = 50
        
        # VIX percentile: invert (high VIX = fear = undervalued = negative score)
        sc_vix = score_from_percentile(100 - p_vix)  # inverted
        sc_ma = score_from_percentile(p_ma)
        sc_cnn = score_from_percentile(p_cnn)
        
        comp_c = (sc_vix + sc_ma + sc_cnn) / 3
        mult_c = mult_from_composite(comp_c)
        amt_c = f500(BASE_DAILY * mult_c)
        sh_c += amt_c / ndx_cur
        inv_c += amt_c
        recs_c.append({'date': dt, 'year': dt.year, 'invested': amt_c,
                       'cum_inv': inv_c, 'ndx': ndx_cur, 'shares': sh_c,
                       'mktval': sh_c * ndx_cur, 'composite': comp_c,
                       'vix': vix_cur, 'ma_ratio': mr, 'cnn': fng,
                       'p_vix': p_vix, 'p_ma': p_ma, 'p_cnn': p_cnn,
                       'sc_vix': sc_vix, 'sc_ma': sc_ma, 'sc_cnn': sc_cnn})

    def summ(recs):
        df = pd.DataFrame(recs)
        y = (df['date'].iloc[-1] - df['date'].iloc[0]).days / 365.25
        inv = df['invested'].sum()
        fv = df['mktval'].iloc[-1]
        cagr = ((fv / inv) ** (1 / y) - 1) * 100 if y > 0 else 0
        vals = df['mktval'].values
        peak = np.maximum.accumulate(vals)
        max_dd = float((vals / peak - 1).min()) * 100
        return {'years': y, 'total_inv': inv, 'final_val': fv,
                'total_ret': (fv / inv - 1) * 100, 'cagr': cagr, 'max_dd': max_dd, 'df': df}
    
    return {
        'start_year': start_year,
        'start_date': td[0].strftime('%Y-%m-%d'),
        'end_date': td[-1].strftime('%Y-%m-%d'),
        'A': summ(recs_a), 'B': summ(recs_b), 'C': summ(recs_c),
    }

# ==================== RUN ====================
print(f"Common dates: {len(common)}, {common[0].date()} ~ {common[-1].date()}\n")

results = {}
for sy in START_YEARS:
    results[sy] = backtest_triple(sy)

# ==================== COMPARISON TABLE ====================
hdr = f"{'起点':<6} {'模型':<18} {'总投入':>10} {'最终市值':>12} {'CAGR':>8} {'最大回撤':>8}"
print(hdr)
print('─'*80)
for sy in START_YEARS:
    r = results[sy]
    if r is None: continue
    for m, name in [('A','A-四因子绝对值'), ('B','B-CNN/VIX分位'), ('C','C-三因子分位')]:
        d = r[m]
        print(f"{sy:<6} {name:<18} {wan(d['total_inv']):>10} {wan(d['final_val']):>12} {pct2(d['cagr']):>8} {pct2(d['max_dd']):>8}")
    print('─'*80)

# ==================== MULTIPLIER DISTRIBUTION ====================
print(f"\n\n{'='*80}")
print("📊 定投倍数分布 (2006起点, 全周期)")
print(f"{'='*80}")
r0 = results[2006]
labels_m = {2.5:'2.5x', 2.0:'2.0x', 1.5:'1.5x', 1.0:'1.0x', 0.75:'0.75x', 0.5:'0.5x', 0.25:'0.25x'}
print(f"{'倍数':<8} {'A-四因子绝对值':>16} {'B-CNN/VIX分位':>16} {'C-三因子分位':>16}")
print('─'*8 + ' ' + '─'*16 + ' ' + '─'*16 + ' ' + '─'*16)
for mk in [2.5, 2.0, 1.5, 1.0, 0.75, 0.5, 0.25]:
    row = f"{labels_m[mk]:<8}"
    for m in ['A','B','C']:
        df = r0[m]['df']
        amt_target = f500(BASE_DAILY * mk)
        c = (df['invested'] == amt_target).sum()
        p = c / len(df) * 100
        row += f" {c:>4}天 {p:>5.1f}%  "
    print(row)

# ==================== 20-YEAR VALUATION ZONE TIMELINE ====================
print(f"\n\n{'='*80}")
print("📅 20年估值分区时间线 — Model C (三因子分位值)")
print(f"{'='*80}")

# Use 2006 result for full timeline
df_c = results[2006]['C']['df'].copy()
df_c['date'] = pd.to_datetime(df_c['date'])
df_c.set_index('date', inplace=True)

def zone_label(comp):
    if comp < -2.0: return '🔥极度低估'
    if comp < -1.0: return '🟢中度低估'
    if comp < -0.3: return '🟡轻度低估'
    if comp <= 0.3: return '⚪中性'
    if comp <= 1.0: return '🟠轻度高估'
    if comp <= 2.0: return '🔴中度高估'
    return '💀严重高估'

df_c['zone'] = df_c['composite'].apply(zone_label)

# Print yearly summary: dominant zone + zone distribution per year
print(f"\n{'年份':<6} {'主导估值区':<12} {'极度低估':>8} {'中度低估':>8} {'轻度低估':>8} {'中性':>8} {'轻度高估':>8} {'中度高估':>8} {'严重高估':>8}  {'NDX涨跌':>8}")
print('─'*120)

zones_order = ['🔥极度低估', '🟢中度低估', '🟡轻度低估', '⚪中性', '🟠轻度高估', '🔴中度高估', '💀严重高估']
for yr in range(2006, 2027):
    mask = df_c.index.year == yr
    if mask.sum() == 0: continue
    ydata = df_c[mask]
    counts = ydata['zone'].value_counts()
    dom = counts.index[0] if len(counts) > 0 else '—'
    ndx_chg = (ydata['ndx'].iloc[-1] / ydata['ndx'].iloc[0] - 1) * 100
    
    row = f"{yr:<6} {dom:<12}"
    for z in zones_order:
        c = counts.get(z, 0)
        row += f" {c:>5}天 "
    row += f" {ndx_chg:>+7.1f}%"
    print(row)

# ==================== QUARTERLY BREAKDOWN (recent 5 years) ====================
print(f"\n\n{'='*80}")
print("📅 近5年季度估值分布 — Model C")
print(f"{'='*80}")
df_c['quarter'] = df_c.index.to_period('Q')
for q in sorted(df_c['quarter'].unique())[-20:]:
    qdata = df_c[df_c['quarter'] == q]
    if len(qdata) == 0: continue
    counts = qdata['zone'].value_counts()
    dom = counts.index[0]
    avg_comp = qdata['composite'].mean()
    print(f"{q} | 主导: {dom:<10} | 平均分: {avg_comp:+.2f} | ", end='')
    parts = []
    for z in zones_order:
        c = counts.get(z, 0)
        if c > 0:
            parts.append(f"{z[-4:]}:{c}")
    print(', '.join(parts))

# ==================== FULL CSV EXPORT for inspection ====================
csv_out = os.path.join(BASE, 'data', 'valuation_timeline.csv')
df_c[['ndx','vix','ma_ratio','cnn','composite','zone','p_vix','p_ma','p_cnn','sc_vix','sc_ma','sc_cnn']].to_csv(csv_out, float_format='%.4f')
print(f"\n\n完整20年逐日估值数据已导出: {csv_out}")
print(f"列: date, ndx, vix, ma_ratio, cnn, composite, zone, p_vix, p_ma, p_cnn, sc_vix, sc_ma, sc_cnn")
