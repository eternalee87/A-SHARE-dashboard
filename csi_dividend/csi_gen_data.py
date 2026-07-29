"""
中证红利质量指数 (931468) 定投 — 信号计算
MA200分位值模型 · 周度定投 · 2年目标100万
"""
import sys, io, os, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import pandas as pd, numpy as np
from datetime import datetime
from collections import OrderedDict

BASE = os.path.dirname(os.path.abspath(__file__))
CSI_CSV = os.path.join(BASE, 'data', 'csi_data.csv')
HISTORY_CSV = os.path.join(BASE, 'data', 'dca_history.csv')
OUTPUT_JSON = os.path.join(BASE, 'data', 'dashboard_data.json')

# Config
START_DATE = '2026-07-10'
TARGET_TOTAL = 1_000_000
TARGET_YEARS = 2
BASE_WEEKLY = TARGET_TOTAL / (TARGET_YEARS * 52)  # ~9,615
MIN_UNIT = 500

def f500(x): return max(MIN_UNIT, int(x // MIN_UNIT) * MIN_UNIT)

# Load
csi = pd.read_csv(CSI_CSV, index_col=0, parse_dates=True)['close']
ma200 = csi.rolling(200).mean()
all_ma = np.array([float(csi.loc[dt] / ma200.loc[dt]) if dt in ma200.index and not np.isnan(ma200.loc[dt]) else 1.0 for dt in csi.index])

print(f"CSI 931468: {len(csi)} rows, {csi.index[0].date()} ~ {csi.index[-1].date()}, latest={csi.iloc[-1]:.2f}")
print(f"Target: {TARGET_TOTAL/10000:.0f}万 / {TARGET_YEARS}年, base weekly={BASE_WEEKLY:,.0f} CNY")

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

# Current valuation
csi_cur = float(csi.iloc[-1])
ma200_cur = float(ma200.iloc[-1]) if not np.isnan(ma200.iloc[-1]) else csi_cur
ratio = csi_cur / ma200_cur
p_ma = (all_ma <= ratio).sum() / len(all_ma) * 100
score = int(sc(p_ma))
multiplier = mc(score)
dca_amount = f500(BASE_WEEKLY * multiplier)

if score < -2.0:   level, label, color = 'severe_under', '🔥 极度低估', '#006400'
elif score < -1.0: level, label, color = 'moderate_under', '🟢 中度低估', '#228B22'
elif score < -0.3: level, label, color = 'mild_under', '🟡 轻度低估', '#32CD32'
elif score <= 0.3: level, label, color = 'neutral', '⚪ 中性/合理', '#808080'
elif score <= 1.0: level, label, color = 'mild_over', '🟠 轻度高估', '#FFA500'
elif score <= 2.0: level, label, color = 'moderate_over', '🔴 中度高估', '#FF4500'
else:              level, label, color = 'severe_over', '💀 严重高估', '#FF0000'

print(f"MA200: {ma200_cur:.2f}, Ratio: {ratio:.4f}, P{p_ma:.1f}, Score: {score:+d}, {label}, {dca_amount:,} CNY")

# History
if os.path.exists(HISTORY_CSV):
    hist = pd.read_csv(HISTORY_CSV, index_col=0, parse_dates=True)
else:
    hist = pd.DataFrame(columns=['csi_close','dca_amount','shares_bought',
                                  'cum_invested','cum_shares','market_value','pnl','return_rate'])

# Weekly recording
all_dates = csi.index[csi.index >= START_DATE]
week_map = OrderedDict()
for dt in all_dates:
    iso = dt.isocalendar()
    week_map[(iso[0], iso[1])] = dt
weekly_dates = pd.DatetimeIndex(list(week_map.values())).sort_values()
existing = set(hist.index.strftime('%Y-%m-%d')) if len(hist) > 0 else set()

missed = [(dt, dt.strftime('%Y-%m-%d')) for dt in weekly_dates if dt.strftime('%Y-%m-%d') not in existing]

if missed:
    new_rows = []
    ci = hist['dca_amount'].sum() if len(hist) > 0 else 0
    cs = hist['shares_bought'].sum() if len(hist) > 0 else 0
    for dt, ds in missed:
        nc = float(csi.loc[dt])
        shares = dca_amount / nc
        ci += dca_amount; cs += shares
        new_rows.append({'csi_close': nc, 'dca_amount': dca_amount, 'shares_bought': shares,
                         'cum_invested': ci, 'cum_shares': cs, 'market_value': cs*nc,
                         'pnl': cs*nc-ci, 'return_rate': (cs*nc/ci-1)*100 if ci>0 else 0})
    ndf = pd.DataFrame(new_rows, index=[pd.Timestamp(ds) for _, ds in missed])
    hist = pd.concat([hist, ndf]).sort_index()
    hist.index.name = 'date'

# Recompute cumulative
if len(hist) > 0:
    hist = hist.sort_index()
    ci = 0; cs = 0
    for idx in hist.index:
        ci += hist.loc[idx, 'dca_amount']; cs += hist.loc[idx, 'shares_bought']
        nv = hist.loc[idx, 'csi_close']
        hist.loc[idx, 'cum_invested'] = ci; hist.loc[idx, 'cum_shares'] = cs
        hist.loc[idx, 'market_value'] = cs*nv; hist.loc[idx, 'pnl'] = cs*nv-ci
        hist.loc[idx, 'return_rate'] = (cs*nv/ci-1)*100 if ci>0 else 0
    hist.to_csv(HISTORY_CSV, float_format='%.6f')
    total_inv = ci; total_sh = cs
else:
    total_inv = 0; total_sh = 0

cur_val = total_sh * csi_cur
pnl = cur_val - total_inv
ret = pnl/total_inv*100 if total_inv>0 else 0
csi_start = csi[csi.index >= START_DATE].iloc[0]
csi_ret = (csi_cur/csi_start-1)*100

# Max DD
vals = hist['cum_shares']*hist['csi_close'] if len(hist)>0 else pd.Series([0])
peak = vals.expanding().max()
dd = float((vals/peak-1).min())*100 if len(vals)>0 else 0
csi_since = csi[csi.index >= START_DATE]
csi_peak = csi_since.expanding().max()
csi_dd = float((csi_since/csi_peak-1).min())*100 if len(csi_since)>0 else 0

# Charts
r180 = csi.iloc[-180:]
ts_180 = [str(d)[:10] for d in r180.index]
vals_180 = [float(v) for v in r180.values]
ma_180 = [float(v) for v in ma200.iloc[-180:].values]
ratio_hist = (csi/ma200).dropna().iloc[-360:]
rts = [str(d)[:10] for d in ratio_hist.index]
rvs = [float(v) for v in ratio_hist.values]
hts = [str(d)[:10] for d in hist.index] if len(hist)>0 else []
hvs = [float(v) for v in (hist['cum_shares']*hist['csi_close']).values] if len(hist)>0 else []
his = [float(v) for v in hist['cum_invested'].values] if len(hist)>0 else []

out = {
    'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
    'last_trading_day': csi.index[-1].strftime('%Y-%m-%d'),
    'csi': round(csi_cur, 2), 'ma200': round(ma200_cur, 2), 'ratio': round(ratio, 4),
    'pct_rank': round(p_ma, 1), 'score': score, 'valuation_label': label,
    'valuation_color': color, 'multiplier': multiplier,
    'base_weekly': round(BASE_WEEKLY, 0), 'dca_amount': dca_amount,
    'target_total': TARGET_TOTAL, 'target_years': TARGET_YEARS,
    'start_date': START_DATE, 'min_unit': MIN_UNIT,
    'total_invested': round(total_inv, 0), 'total_shares': round(total_sh, 6),
    'current_value': round(cur_val, 0), 'pnl': round(pnl, 0),
    'return_rate': round(ret, 2), 'csi_return': round(csi_ret, 2),
    'portfolio_max_dd': round(dd, 4), 'csi_max_dd': round(csi_dd, 4),
    'ts_180': ts_180, 'vals_180': vals_180, 'ma_180': ma_180,
    'ratio_ts': rts, 'ratio_vals': rvs,
    'hist_ts': hts, 'hist_vals': hvs, 'hist_invested': his,
}

with open(OUTPUT_JSON, 'w', encoding='utf-8') as f:
    json.dump(out, f, ensure_ascii=False, indent=1, default=str)
print(f"Output: {OUTPUT_JSON}")
print(f"Weekly DCA: {dca_amount:,} CNY — {label} | Total: {total_inv:,.0f} CNY | Value: {cur_val:,.0f} CNY")
