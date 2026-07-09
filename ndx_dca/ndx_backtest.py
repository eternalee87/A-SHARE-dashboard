"""
纳斯达克100定投策略 — 历史回测脚本
回测起点: 2006, 2008, 2014, 2017
CNN恐慌贪婪指数历史有限（仅~2年），更早时期用VIX代理估算。
"""
import sys, io, os, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import pandas as pd
import numpy as np

BASE = os.path.dirname(os.path.abspath(__file__))
NDX_CSV = os.path.join(BASE, 'data', 'ndx_data.csv')
VIX_CSV = os.path.join(BASE, 'data', 'vix_data.csv')
CNN_JSON = os.path.join(BASE, 'data', 'cnn_fng.json')

# ==================== CONFIG ====================
TARGET_TOTAL = 5_000_000
TARGET_YEARS = 10
TRADING_DAYS_PER_YEAR = 250
BASE_DAILY = TARGET_TOTAL / (TARGET_YEARS * TRADING_DAYS_PER_YEAR)
MIN_UNIT = 500
START_YEARS = [2006, 2008, 2014, 2017]

def fmt(n, decimals=0):
    if n is None: return '—'
    return f"{n:,.{decimals}f}"

def pct2(n):
    if n is None: return '—'
    return f"{n:+.2f}%"

def wan(n):
    if n is None: return '—'
    return f"{n/10000:.1f}万"

def floor_to_unit(amount, unit=MIN_UNIT):
    return max(unit, int(amount // unit) * unit)

# ==================== SCORING ====================
def score_daily_change(pct_change):
    pct = pct_change * 100
    if pct < -3: return -3
    if pct < -2: return -2
    if pct < -1: return -1
    if pct <= 1: return 0
    if pct <= 2: return 1
    if pct <= 3: return 2
    return 3

def score_vix(vix_val):
    if vix_val is None or np.isnan(vix_val): return 0
    if vix_val > 45: return -3
    if vix_val > 35: return -2
    if vix_val > 28: return -1
    if vix_val >= 18: return 0
    if vix_val >= 14: return 1
    if vix_val >= 11: return 2
    return 3

def score_ma200_ratio(ratio):
    if ratio is None or np.isnan(ratio): return 0
    if ratio < 0.80: return -3
    if ratio < 0.88: return -2
    if ratio < 0.95: return -1
    if ratio <= 1.05: return 0
    if ratio <= 1.15: return 1
    if ratio <= 1.25: return 2
    return 3

def score_cnn_fng(fng_score):
    if fng_score is None: return 0
    if fng_score < 15: return -3
    if fng_score < 25: return -2
    if fng_score < 35: return -1
    if fng_score <= 55: return 0
    if fng_score <= 65: return 1
    if fng_score <= 80: return 2
    return 3

def get_multiplier(composite):
    if composite < -2.0:   return 2.5
    elif composite < -1.0: return 2.0
    elif composite < -0.3: return 1.5
    elif composite <= 0.3: return 1.0
    elif composite <= 1.0: return 0.75
    elif composite <= 2.0: return 0.5
    else:                  return 0.25

def vix_to_fng_proxy(vix_val):
    """Estimate CNN Fear & Greed from VIX when CNN data unavailable."""
    if vix_val is None or np.isnan(vix_val): return 50
    if vix_val > 40: return 5
    if vix_val > 35: return 15
    if vix_val > 30: return 22
    if vix_val > 28: return 28
    if vix_val > 25: return 35
    if vix_val > 22: return 42
    if vix_val > 20: return 48
    if vix_val > 18: return 55
    if vix_val > 16: return 62
    if vix_val > 14: return 70
    if vix_val > 12: return 78
    return 88

# ==================== LOAD DATA ====================
print("Loading data...")
ndx_df = pd.read_csv(NDX_CSV, index_col=0, parse_dates=True)
vix_df = pd.read_csv(VIX_CSV, index_col=0, parse_dates=True)

with open(CNN_JSON, 'r', encoding='utf-8') as f:
    cnn_data = json.load(f)

ndx = ndx_df['close'].dropna()
vix = vix_df['close'].dropna()

cnn_lookup = {}
for h in cnn_data.get('history', []):
    cnn_lookup[h['date']] = h['score']

print(f"NDX: {ndx.index[0].date()} ~ {ndx.index[-1].date()}, {len(ndx)} rows")
print(f"VIX: {vix.index[0].date()} ~ {vix.index[-1].date()}, {len(vix)} rows")
print(f"CNN: {len(cnn_lookup)} data points, {list(cnn_lookup.keys())[0]} ~ {list(cnn_lookup.keys())[-1]}")

# ==================== BACKTEST ENGINE ====================
def backtest(start_year):
    """Simulate DCA from Jan 1 of start_year to latest data."""
    start_date = f"{start_year}-01-01"
    
    # Find common trading days where both NDX and VIX have data
    common_all = ndx.index.intersection(vix.index)
    common = common_all[common_all >= start_date]
    if len(common) == 0:
        return None
    
    trade_dates = common.sort_values()
    
    ndx_full = ndx[ndx.index <= trade_dates[-1]]
    ma200_series = ndx_full.rolling(200).mean()
    
    total_invested = 0
    total_shares = 0
    records = []
    
    for i, dt in enumerate(trade_dates):
        ndx_cur = ndx.loc[dt]
        vix_cur = vix.loc[dt] if dt in vix.index else None
        
        pct_change = 0
        if i > 0:
            prev_idx = trade_dates[i-1]
            pct_change = (ndx_cur / ndx.loc[prev_idx]) - 1
        
        ma200_ratio = 1.0
        if dt in ma200_series.index and not np.isnan(ma200_series.loc[dt]):
            ma200_ratio = ndx_cur / ma200_series.loc[dt]
        
        dt_str = dt.strftime('%Y-%m-%d')
        if dt_str in cnn_lookup:
            fng_score = cnn_lookup[dt_str]
        else:
            fng_score = vix_to_fng_proxy(vix_cur)
        
        s1 = score_daily_change(pct_change)
        s2 = score_vix(vix_cur)
        s3 = score_ma200_ratio(ma200_ratio)
        s4 = score_cnn_fng(fng_score)
        composite = (s1 + s2 + s3 + s4) / 4
        
        multiplier = get_multiplier(composite)
        dca_amount = floor_to_unit(BASE_DAILY * multiplier)
        
        shares_bought = dca_amount / ndx_cur
        total_invested += dca_amount
        total_shares += shares_bought
        
        records.append({
            'date': dt,
            'year': dt.year,
            'invested': dca_amount,
            'cum_invested': total_invested,
            'ndx_close': ndx_cur,
            'total_shares': total_shares,
            'market_value': total_shares * ndx_cur,
            'composite': composite,
        })
    
    df = pd.DataFrame(records)
    
    # Annual summary
    annual = df.groupby('year').agg(
        annual_invested=('invested', 'sum'),
        year_end_ndx=('ndx_close', 'last'),
        cum_invested=('cum_invested', 'last'),
        cum_shares=('total_shares', 'last'),
    ).reset_index()
    annual['cum_value'] = annual['cum_shares'] * annual['year_end_ndx']
    annual['cum_return_pct'] = (annual['cum_value'] / annual['cum_invested'] - 1) * 100
    
    # Final stats
    final = df.iloc[-1]
    years_elapsed = (df['date'].iloc[-1] - df['date'].iloc[0]).days / 365.25
    final_value = final['market_value']
    cagr = ((final_value / total_invested) ** (1 / years_elapsed) - 1) * 100 if years_elapsed > 0 else 0
    
    ndx_start = ndx.loc[trade_dates[0]]
    ndx_end = ndx.loc[trade_dates[-1]]
    ndx_return = (ndx_end / ndx_start - 1) * 100
    ndx_cagr = ((ndx_end / ndx_start) ** (1 / years_elapsed) - 1) * 100
    
    # Max drawdown
    vals = df['market_value'].values
    peak = np.maximum.accumulate(vals)
    max_dd = float((vals / peak - 1).min()) * 100
    
    ndx_vals = df['ndx_close'].values
    ndx_peak = np.maximum.accumulate(ndx_vals)
    ndx_max_dd = float((ndx_vals / ndx_peak - 1).min()) * 100
    
    return {
        'start_year': start_year,
        'start_date': trade_dates[0].strftime('%Y-%m-%d'),
        'end_date': trade_dates[-1].strftime('%Y-%m-%d'),
        'trading_days': len(trade_dates),
        'years_elapsed': round(years_elapsed, 1),
        'total_invested': total_invested,
        'final_value': final_value,
        'pnl': final_value - total_invested,
        'total_return_pct': (final_value / total_invested - 1) * 100,
        'cagr_pct': cagr,
        'ndx_return_pct': ndx_return,
        'ndx_cagr_pct': ndx_cagr,
        'max_dd_pct': max_dd,
        'ndx_max_dd_pct': ndx_max_dd,
        'annual': annual,
        '_records': records,
    }


# ==================== RUN ====================
print("\n" + "=" * 80)
print("纳斯达克100 定投策略回测")
print(f"策略: 4因子估值模型 × 动态倍数定投 (基础{BASE_DAILY:,.0f}/日, 最小{MIN_UNIT}元)")
print("=" * 80)

results = {}
for sy in START_YEARS:
    r = backtest(sy)
    if r:
        results[sy] = r

# ==================== DETAILED OUTPUT ====================
for sy in START_YEARS:
    r = results.get(sy)
    if r is None:
        print(f"\n{sy}: 数据不足，跳过")
        continue
    
    print(f"\n{'─'*80}")
    print(f"📅 起始: {r['start_year']}年 ({r['start_date']} ~ {r['end_date']}, {r['years_elapsed']}年, {r['trading_days']}个交易日)")
    print(f"{'─'*80}")
    
    ann = r['annual']
    print(f"{'年份':<6} {'年投入(万)':>10} {'累计投入(万)':>12} {'年末NDX':>10} {'年末市值(万)':>12} {'累计收益率':>10}")
    print(f"{'─'*6} {'─'*10} {'─'*12} {'─'*10} {'─'*12} {'─'*10}")
    
    for _, row in ann.iterrows():
        yr = int(row['year'])
        ai = row['annual_invested'] / 10000
        ci = row['cum_invested'] / 10000
        ndx_v = row['year_end_ndx']
        cv = row['cum_value'] / 10000
        ret = row['cum_return_pct']
        print(f"{yr:<6} {ai:>10.1f} {ci:>12.1f} {ndx_v:>10.0f} {cv:>12.1f} {ret:>+9.2f}%")
    
    print(f"{'─'*6} {'─'*10} {'─'*12} {'─'*10} {'─'*12} {'─'*10}")
    print(f"\n  📊 总投入:         {wan(r['total_invested'])} CNY")
    print(f"  💰 最终市值:       {wan(r['final_value'])} CNY")
    print(f"  📈 总盈亏:         {wan(r['pnl'])} CNY")
    print(f"  📊 总收益率:       {pct2(r['total_return_pct'])}")
    print(f"  📈 年化收益率(CAGR): {pct2(r['cagr_pct'])}")
    print(f"  📉 NDX买入持有收益: {pct2(r['ndx_return_pct'])}")
    print(f"  📉 NDX年化收益:     {pct2(r['ndx_cagr_pct'])}")
    print(f"  ⚠️  组合最大回撤:   {pct2(r['max_dd_pct'])}")
    print(f"  ⚠️  NDX最大回撤:    {pct2(r['ndx_max_dd_pct'])}")

# ==================== COMPARISON ====================
print(f"\n\n{'='*80}")
print("📊 各起点汇总对比")
print(f"{'='*80}")
print(f"{'起点':<8} {'年数':<6} {'总投入(万)':>10} {'最终市值(万)':>12} {'总收益率':>10} {'CAGR':>10} {'NDX CAGR':>10} {'最大回撤':>10}")
print(f"{'─'*8} {'─'*6} {'─'*10} {'─'*12} {'─'*10} {'─'*10} {'─'*10} {'─'*10}")
for sy in START_YEARS:
    r = results.get(sy)
    if r:
        print(f"{sy:<8} {r['years_elapsed']:<6} {wan(r['total_invested']):>10} {wan(r['final_value']):>12} {pct2(r['total_return_pct']):>10} {pct2(r['cagr_pct']):>10} {pct2(r['ndx_cagr_pct']):>10} {pct2(r['max_dd_pct']):>10}")
print(f"{'─'*8} {'─'*6} {'─'*10} {'─'*12} {'─'*10} {'─'*10} {'─'*10} {'─'*10}")

# ==================== VALUATION DISTRIBUTION ====================
print(f"\n\n{'='*80}")
print("📊 估值分布 — 各时段定投倍数使用频率")
print(f"{'='*80}")
print(f"{'起点':<8} {'极度低估 2.5x':>14} {'中度低估 2.0x':>14} {'轻度低估 1.5x':>14} {'中性 1.0x':>12} {'轻度高估 0.75x':>14} {'中度高估 0.5x':>14} {'严重高估 0.25x':>14}")
print(f"{'─'*8} {'─'*14} {'─'*14} {'─'*14} {'─'*12} {'─'*14} {'─'*14} {'─'*14}")
for sy in START_YEARS:
    r = results.get(sy)
    if r is None: continue
    df_rec = pd.DataFrame(r['_records'])
    df_rec['mult'] = df_rec['composite'].apply(get_multiplier)
    counts = df_rec['mult'].value_counts()
    total = len(df_rec)
    vals = []
    for m in [2.5, 2.0, 1.5, 1.0, 0.75, 0.5, 0.25]:
        c = counts.get(m, 0)
        vals.append(f"{c:>4}天 {c/total*100:>5.1f}%")
    print(f"{sy:<8} {vals[0]:>14} {vals[1]:>14} {vals[2]:>14} {vals[3]:>12} {vals[4]:>14} {vals[5]:>14} {vals[6]:>14}")
print(f"{'─'*8} {'─'*14} {'─'*14} {'─'*14} {'─'*12} {'─'*14} {'─'*14} {'─'*14}")

print(f"\n✅ 回测完成")
