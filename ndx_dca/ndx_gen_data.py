"""
纳斯达克100定投仪表盘 — 信号计算 & 定投金额生成
目标: 10年总定投 ~500万, 起始日 2026-07-10
"""
import sys, io, os, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import pandas as pd
import numpy as np
from datetime import datetime, date

BASE = os.path.dirname(os.path.abspath(__file__))
NDX_CSV = os.path.join(BASE, 'data', 'ndx_data.csv')
VIX_CSV = os.path.join(BASE, 'data', 'vix_data.csv')
CNN_JSON = os.path.join(BASE, 'data', 'cnn_fng.json')
HISTORY_CSV = os.path.join(BASE, 'data', 'dca_history.csv')
OUTPUT_JSON = os.path.join(BASE, 'data', 'ndx_dashboard_data.json')

# ==================== CONFIG ====================
START_DATE = '2026-07-10'
TARGET_TOTAL = 5_000_000        # 目标总定投 500万
TARGET_YEARS = 10               # 10年
TRADING_DAYS_PER_YEAR = 250
BASE_DAILY = TARGET_TOTAL / (TARGET_YEARS * TRADING_DAYS_PER_YEAR)  # ~2000
MIN_UNIT = 500                  # 最小单位 500元

print(f"Base daily DCA: {BASE_DAILY:.0f} CNY (target {TARGET_TOTAL/10000:.0f}万 / {TARGET_YEARS}年 / ~{TARGET_YEARS*TRADING_DAYS_PER_YEAR}个交易日)")

# ==================== HELPERS ====================
def to_py(v):
    if isinstance(v, (np.integer,)): return int(v)
    if isinstance(v, (np.floating, np.float64)): return float(v)
    if isinstance(v, (np.bool_,)): return bool(v)
    if isinstance(v, (pd.Timestamp,)): return str(v)[:10]
    return v

def floor_to_unit(amount, unit=MIN_UNIT):
    """向下取整到最小单位"""
    return max(unit, int(amount // unit) * unit)

# ==================== LOAD DATA ====================
print("\nLoading data...")
ndx_df = pd.read_csv(NDX_CSV, index_col=0, parse_dates=True)
vix_df = pd.read_csv(VIX_CSV, index_col=0, parse_dates=True)

with open(CNN_JSON, 'r', encoding='utf-8') as f:
    cnn_data = json.load(f)

ndx = ndx_df['close']
vix = vix_df['close']

# Align dates - use NDX dates as primary
common_dates = ndx.index.intersection(vix.index)
ndx = ndx[common_dates]
vix = vix[common_dates]

print(f"NDX: {len(ndx)} rows, {ndx.index[0].strftime('%Y-%m-%d')} ~ {ndx.index[-1].strftime('%Y-%m-%d')}")
print(f"VIX: {len(vix)} rows")
print(f"Latest NDX: {ndx.iloc[-1]:.2f}")
print(f"Latest VIX: {vix.iloc[-1]:.2f}")

# ==================== COMPUTE MA200 ====================
ndx_ma200 = ndx.rolling(200).mean()
ndx_ma200_ratio = ndx.iloc[-1] / ndx_ma200.iloc[-1]
print(f"NDX MA200: {ndx_ma200.iloc[-1]:.2f}, Ratio: {ndx_ma200_ratio:.4f}")

# ==================== VALUATION SCORING (3-Factor Percentile Model) ====================
# Core idea: use historical percentile instead of absolute thresholds.
# VIX (inverted): high VIX = high percentile = fear → undervalued → negative score
# NDX/MA200: high ratio = high percentile → overvalued → positive score
# CNN F&G: high = high percentile → greed → positive score

# Build CNN full-history lookup (with VIX proxy for missing dates)
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

cnn_hist_lookup = {}
for h in cnn_data.get('history', []):
    cnn_hist_lookup[h['date']] = h['score']

# Build full-history arrays for percentile computation
all_vix = []
all_ma_ratio = []
all_cnn = []
for dt in common_dates:
    ds = dt.strftime('%Y-%m-%d')
    c = cnn_hist_lookup.get(ds)
    if c is None:
        c = vix_to_cnn(vix.loc[dt] if dt in vix.index else None)
    all_vix.append(float(vix.loc[dt]) if dt in vix.index else 20.0)
    mr = float(ndx.loc[dt] / ndx_ma200.loc[dt]) if dt in ndx_ma200.index and not np.isnan(ndx_ma200.loc[dt]) else 1.0
    all_ma_ratio.append(mr)
    all_cnn.append(float(c))

all_vix = np.array(all_vix)
all_ma_ratio = np.array(all_ma_ratio)
all_cnn = np.array(all_cnn)

print(f"Percentile baseline: {len(all_vix)} data points from {common_dates[0].strftime('%Y-%m-%d')} to {common_dates[-1].strftime('%Y-%m-%d')}")

def score_from_percentile(pct):
    """Percentile (0-100) → score (-3 to +3), designed for fat tails"""
    if pct < 5:   return -3
    if pct < 15:  return -2
    if pct < 30:  return -1
    if pct <= 70: return 0
    if pct <= 85: return 1
    if pct <= 95: return 2
    return 3

# Current values
ndx_cur = float(ndx.iloc[-1])
vix_cur = float(vix.iloc[-1])
cnn_cur = cnn_data.get('current', {})
cnn_score_val = cnn_cur.get('score')
cnn_rating = cnn_cur.get('rating', 'unknown')
ndx_ma200_ratio = float(ndx_cur / ndx_ma200.iloc[-1])
ndx_prev_val = float(ndx.iloc[-2]) if len(ndx) > 1 else ndx_cur
ndx_pct_change = (ndx_cur / ndx_prev_val) - 1

# Compute percentiles against full history
# VIX: higher = more fear → inverted for score
p_vix = (all_vix <= vix_cur).sum() / len(all_vix) * 100
# MA200 ratio: higher = more overvalued
p_ma = (all_ma_ratio <= ndx_ma200_ratio).sum() / len(all_ma_ratio) * 100
# CNN: higher = more greed
cnn_val = float(cnn_score_val) if cnn_score_val is not None else 50.0
if cnn_score_val is None:
    cnn_val = vix_to_cnn(vix_cur)
p_cnn = (all_cnn <= cnn_val).sum() / len(all_cnn) * 100

# Score: VIX inverted (high VIX = fear = undervalued)
s1 = score_from_percentile(100 - p_vix)
s2 = score_from_percentile(p_ma)
s3 = score_from_percentile(p_cnn)

composite = round((s1 + s2 + s3) / 3, 2)

print(f"\nValuation Scores (3-Factor Percentile Model):")
print(f"  VIX: {vix_cur:.2f} → p{p_vix:.1f} (inverted {100-p_vix:.1f}) → score {s1:+d}")
print(f"  NDX/MA200: {ndx_ma200_ratio:.4f} → p{p_ma:.1f} → score {s2:+d}")
print(f"  CNN F&G: {cnn_val:.1f} ({cnn_rating}) → p{p_cnn:.1f} → score {s3:+d}")
print(f"  COMPOSITE: {composite}")

# Valuation level
if composite < -2.0:
    val_level = 'severely_undervalued'
    val_label = '极度低估'
    val_color = '#006400'  # dark green
    multiplier = 2.5
elif composite < -1.0:
    val_level = 'moderately_undervalued'
    val_label = '中度低估'
    val_color = '#228B22'
    multiplier = 2.0
elif composite < -0.3:
    val_level = 'mildly_undervalued'
    val_label = '轻度低估'
    val_color = '#32CD32'
    multiplier = 1.5
elif composite <= 0.3:
    val_level = 'neutral'
    val_label = '中性/合理估值'
    val_color = '#808080'
    multiplier = 1.0
elif composite <= 1.0:
    val_level = 'mildly_overvalued'
    val_label = '轻度高估'
    val_color = '#FFA500'
    multiplier = 0.75
elif composite <= 2.0:
    val_level = 'moderately_overvalued'
    val_label = '中度高估'
    val_color = '#FF4500'
    multiplier = 0.5
else:
    val_level = 'severely_overvalued'
    val_label = '严重高估'
    val_color = '#FF0000'
    multiplier = 0.25

# DCA amount
dca_raw = BASE_DAILY * multiplier
dca_amount = floor_to_unit(dca_raw)

print(f"\nValuation: {val_label} (multiplier={multiplier}x)")
print(f"DCA Amount: {dca_amount:,} CNY (raw: {dca_raw:.0f})")

# ==================== INVESTMENT HISTORY ====================
# Load or initialize history
if os.path.exists(HISTORY_CSV):
    hist_df = pd.read_csv(HISTORY_CSV, index_col=0, parse_dates=True)
    print(f"\nInvestment history: {len(hist_df)} records")
else:
    hist_df = pd.DataFrame(columns=[
        'ndx_close', 'dca_amount', 'shares_bought',
        'cumulative_invested', 'cumulative_shares',
        'market_value', 'pnl', 'return_rate'
    ])
    hist_df.index.name = 'date'
    print("\nNew investment history initialized")

# Check if today is a trading day and we need to record
today_str = datetime.now().strftime('%Y-%m-%d')
today_date = datetime.now().date()
start_dt = datetime.strptime(START_DATE, '%Y-%m-%d').date()

# Only record if today >= start date and is a trading day (NDX has data)
last_ndx_date = ndx.index[-1].strftime('%Y-%m-%d')
last_ndx_dt = ndx.index[-1]

print(f"Today: {today_str}, Last NDX date: {last_ndx_date}")
print(f"Start date: {START_DATE}, Started: {today_date >= start_dt}")

# ==================== RECORD TODAY'S INVESTMENT ====================
# Use the latest NDX data date (yesterday's close or today's)
# Record if: data date >= start date AND not yet in history
existing_dates = hist_df.index.strftime('%Y-%m-%d').tolist() if len(hist_df) > 0 else []
should_record = (last_ndx_date >= START_DATE) and (last_ndx_date not in existing_dates)

if should_record:
    shares = dca_amount / ndx_cur
    prev_invested = hist_df['dca_amount'].sum() if len(hist_df) > 0 else 0
    prev_shares = hist_df['shares_bought'].sum() if len(hist_df) > 0 else 0
    cum_invested = prev_invested + dca_amount
    cum_shares = prev_shares + shares

    new_row = pd.DataFrame([{
        'ndx_close': ndx_cur,
        'dca_amount': dca_amount,
        'shares_bought': shares,
        'cumulative_invested': cum_invested,
        'cumulative_shares': cum_shares,
        'market_value': cum_shares * ndx_cur,
        'pnl': cum_shares * ndx_cur - cum_invested,
        'return_rate': (cum_shares * ndx_cur / cum_invested - 1) * 100 if cum_invested > 0 else 0,
    }], index=[pd.Timestamp(last_ndx_date)])

    hist_df = pd.concat([hist_df, new_row])
    hist_df.index.name = 'date'
    hist_df.to_csv(HISTORY_CSV, float_format='%.6f')
    print(f"\n✅ 记录今日定投: {dca_amount:,} CNY → {shares:.6f} 份 NDX")
    print(f"   累计投入: {cum_invested:,.0f} CNY, 累计份额: {cum_shares:.6f}")

# For summary: calculate based on history + potential new record
if len(hist_df) > 0:
    total_invested = hist_df['dca_amount'].sum()
    total_shares = hist_df['shares_bought'].sum()
    last_record_date = hist_df.index[-1].strftime('%Y-%m-%d')
    print(f"  Total invested: {total_invested:,.0f} CNY")
    print(f"  Total shares: {total_shares:.4f}")
    print(f"  Last record: {last_record_date}")
else:
    total_invested = 0
    total_shares = 0
    print("  No investment history yet")

# Current market value
current_value = total_shares * ndx_cur
pnl = current_value - total_invested
return_rate = (pnl / total_invested * 100) if total_invested > 0 else 0

# NDX return since start date
ndx_start_val = None
if start_dt <= today_date:
    # Find closest NDX value to start date
    start_idx = ndx.index[ndx.index >= START_DATE]
    if len(start_idx) > 0:
        ndx_start_val = ndx[start_idx[0]]
        ndx_return = (ndx_cur / ndx_start_val - 1) * 100
    else:
        ndx_return = None
else:
    ndx_return = None

print(f"\nSummary:")
print(f"  Current value: {current_value:,.0f} CNY")
print(f"  P&L: {pnl:+,.0f} CNY")
print(f"  Return rate: {return_rate:+.2f}%")
if ndx_start_val:
    print(f"  NDX start: {ndx_start_val:.2f}, NDX return: {ndx_return:+.2f}%")

# ==================== MAX DRAWDOWN ====================
def calc_max_drawdown(series):
    """Calculate max drawdown from peak."""
    if len(series) == 0:
        return 0
    peak = series.expanding().max()
    dd = (series / peak) - 1
    return float(dd.min())

# Portfolio max drawdown
if len(hist_df) > 0 and total_invested > 0:
    portfolio_values = hist_df['cumulative_shares'] * hist_df['ndx_close']
    portfolio_max_dd = calc_max_drawdown(portfolio_values)
else:
    portfolio_max_dd = 0

# NDX max drawdown since start
if ndx_start_val is not None:
    ndx_since_start = ndx[ndx.index >= START_DATE]
    if len(ndx_since_start) > 1:
        ndx_max_dd = calc_max_drawdown(ndx_since_start)
    else:
        ndx_max_dd = 0
else:
    ndx_max_dd = 0

print(f"  Portfolio max DD: {portfolio_max_dd*100:.2f}%")
print(f"  NDX max DD (since start): {ndx_max_dd*100:.2f}%")

# ==================== BUILD OUTPUT JSON ====================
# 180-day NDX for chart
r180 = ndx.iloc[-180:]
ndx_ts_180 = [str(d)[:10] for d in r180.index]
ndx_vals_180 = [float(v) for v in r180.values]
ma200_vals_180 = [float(v) for v in ndx_ma200.iloc[-180:].values]

# VIX 180-day for chart
vix_180 = vix.iloc[-180:]
vix_vals_180 = [float(v) for v in vix_180.values]

# CNN history for chart
cnn_history = cnn_data.get('history', [])
cnn_ts = [h['date'] for h in cnn_history[-180:]]
cnn_vals = [h['score'] for h in cnn_history[-180:]]

# NDX/MA200 ratio history
ratio_hist = (ndx / ndx_ma200).dropna().iloc[-360:]
ratio_ts = [str(d)[:10] for d in ratio_hist.index]
ratio_vals = [float(v) for v in ratio_hist.values]

# Investment history for chart
if len(hist_df) > 0:
    hist_ts = [str(d)[:10] for d in hist_df.index]
    hist_invested = [float(v) for v in hist_df['cumulative_invested'].values]
    hist_values = [float(v) for v in (hist_df['cumulative_shares'] * hist_df['ndx_close']).values]
else:
    hist_ts, hist_invested, hist_values = [], [], []

output = {
    'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
    'last_trading_day': last_ndx_date,
    'is_trading_day': len(hist_df) > 0 and hist_df.index[-1].strftime('%Y-%m-%d') == last_ndx_date,

    # Current values
    'ndx': round(float(ndx_cur), 2),
    'ndx_change_pct': round(float(ndx_pct_change) * 100, 2),
    'vix': round(float(vix_cur), 2),
    'ndx_ma200': round(float(ndx_ma200.iloc[-1]), 2),
    'ndx_ma200_ratio': round(float(ndx_ma200_ratio), 4),
    'cnn_fng_score': round(float(cnn_val), 2) if cnn_val else None,
    'cnn_fng_rating': cnn_rating,

    # Valuation scores (3-factor percentile model)
    'score_vix': s1,
    'score_ma200': s2,
    'score_cnn': s3,
    'pct_vix': round(float(p_vix), 1),
    'pct_ma200': round(float(p_ma), 1),
    'pct_cnn': round(float(p_cnn), 1),
    'composite_score': composite,
    'valuation_level': val_level,
    'valuation_label': val_label,
    'valuation_color': val_color,
    'multiplier': multiplier,

    # DCA
    'base_daily': round(BASE_DAILY, 0),
    'dca_amount': dca_amount,
    'min_unit': MIN_UNIT,
    'target_total': TARGET_TOTAL,
    'target_years': TARGET_YEARS,
    'start_date': START_DATE,

    # Summary
    'total_invested': round(float(total_invested), 0),
    'total_shares': round(float(total_shares), 6),
    'current_value': round(float(current_value), 0),
    'pnl': round(float(pnl), 0),
    'return_rate': round(float(return_rate), 2),
    'ndx_return_since_start': round(float(ndx_return), 2) if ndx_return is not None else None,
    'ndx_start_value': round(float(ndx_start_val), 2) if ndx_start_val else None,
    'portfolio_max_dd': round(float(portfolio_max_dd), 4),
    'ndx_max_dd_since_start': round(float(ndx_max_dd), 4),

    # Chart data
    'ts_180': ndx_ts_180,
    'ndx_180': ndx_vals_180,
    'ma200_180': ma200_vals_180,
    'vix_180': vix_vals_180,
    'cnn_ts': cnn_ts,
    'cnn_vals': cnn_vals,
    'ratio_ts': ratio_ts,
    'ratio_vals': ratio_vals,

    # Investment history chart
    'hist_ts': hist_ts,
    'hist_invested': hist_invested,
    'hist_values': hist_values,
}

# Save
with open(OUTPUT_JSON, 'w', encoding='utf-8') as f:
    json.dump(output, f, ensure_ascii=False, indent=1, default=str)

print(f"\n{'='*60}")
print(f"Output saved: {OUTPUT_JSON}")
print(f"DCA amount for today: {dca_amount:,} CNY — {val_label}")
