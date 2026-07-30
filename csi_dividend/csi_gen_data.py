"""
中证红利 (000922) 定投 — MA200分位值 · 周度定投
目标: 2年100万, 基础周投9,615, ETF 159209
已有80万底仓, 非深度低估时节奏放缓
"""
import sys, io, os, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import pandas as pd, numpy as np
from datetime import datetime
from collections import OrderedDict

BASE = os.path.dirname(os.path.abspath(__file__))
CSI_CSV = os.path.join(BASE, 'data', 'csi_price.csv')
PE_CSV = os.path.join(BASE, 'data', 'csi_pe.csv')
HISTORY_CSV = os.path.join(BASE, 'data', 'dca_history.csv')
OUTPUT_JSON = os.path.join(BASE, 'data', 'dashboard_data.json')

START_DATE = '2026-07-10'
TARGET_TOTAL = 1_000_000
TARGET_YEARS = 2
BASE_WEEKLY = TARGET_TOTAL / (TARGET_YEARS * 52)
MIN_UNIT = 500
PAYOUT_RATIO = 0.38  # CSI Dividend avg

def f500(x): return max(MIN_UNIT, int(x // MIN_UNIT) * MIN_UNIT)

# Load
csi = pd.read_csv(CSI_CSV, index_col=0, parse_dates=True)['close']
ma200 = csi.rolling(200).mean()
ten_yr_ago = csi.index[-1] - pd.DateOffset(years=10)
ma_ratios = (csi / ma200).dropna()
ma_baseline = ma_ratios[ma_ratios.index >= ten_yr_ago]

# PE data
try:
    pe_df = pd.read_csv(PE_CSV, index_col=0, parse_dates=True)
    pe_s = pe_df['PE-TTM']
    pe_cur = float(pe_s.iloc[-1])
    pe_baseline = pe_s[pe_s.index >= ten_yr_ago]
    pe_pct = (pe_baseline < pe_cur).sum() / len(pe_baseline) * 100
    
    # Dividend yield estimate: DY = payout_ratio / PE
    dy_s = PAYOUT_RATIO / pe_s
    dy_cur = PAYOUT_RATIO / pe_cur
    dy_baseline = dy_s[dy_s.index >= ten_yr_ago]
    dy_pct = (dy_baseline < dy_cur).sum() / len(dy_baseline) * 100
except:
    pe_cur = pe_pct = dy_cur = dy_pct = None

all_ma_arr = np.array([float(csi.loc[dt]/ma200.loc[dt]) if dt in ma200.index and not np.isnan(ma200.loc[dt]) else 1.0 for dt in ma_baseline.index])

print(f"CSI 000922: {csi.index[0].date()} ~ {csi.index[-1].date()}, {len(csi)} rows")

def sc(p):
    if p < 5: return -3
    if p < 15: return -2
    if p < 30: return -1
    if p <= 70: return 0
    if p <= 85: return 1
    if p <= 95: return 2
    return 3

def mc(c):
    """有80万底仓 → 非深度低估时降速"""
    if c < -2.0: return 2.5
    if c < -1.0: return 2.0
    if c < -0.3: return 1.5
    if c <= 0.3: return 1.0
    if c <= 1.0: return 0.5    # 轻度高估: 降半 (was 0.75)
    if c <= 2.0: return 0.25   # 中度高估: 象征性 (was 0.5)
    return 0.25

csi_cur = float(csi.iloc[-1]); ma200_cur = float(ma200.iloc[-1])
ratio = csi_cur / ma200_cur
p_ma = (all_ma_arr <= ratio).sum() / len(all_ma_arr) * 100
score = int(sc(p_ma))
multiplier = mc(score)
dca_amount = f500(BASE_WEEKLY * multiplier)

if score<-2.0: lvl,label,clr='severe_under','🔥 极度低估','#006400'
elif score<-1.0: lvl,label,clr='moderate_under','🟢 中度低估','#228B22'
elif score<-0.3: lvl,label,clr='mild_under','🟡 轻度低估','#32CD32'
elif score<=0.3: lvl,label,clr='neutral','⚪ 中性/合理','#808080'
elif score<=1.0: lvl,label,clr='mild_over','🟠 轻度高估','#FFA500'
elif score<=2.0: lvl,label,clr='moderate_over','🔴 中度高估','#FF4500'
else: lvl,label,clr='severe_over','💀 严重高估','#FF0000'

print(f"MA200: {ma200_cur:.0f} | Ratio={ratio:.4f} | P{p_ma:.1f} | {label} | {dca_amount:,} CNY")
print(f"  公式: NDX收盘价/{ma200_cur:.0f}(MA200) = {csi_cur:.0f}/{ma200_cur:.0f} = {ratio:.4f}")
if pe_cur:
    print(f"PE: {pe_cur:.2f} (10yr P{pe_pct:.1f}) | 股息率≈{dy_cur*100:.2f}% (10yr P{dy_pct:.1f})")

# History
if os.path.exists(HISTORY_CSV):
    hist = pd.read_csv(HISTORY_CSV, index_col=0, parse_dates=True)
else:
    hist = pd.DataFrame(columns=['csi_close','dca_amount','shares_bought','cum_invested','cum_shares','market_value','pnl','return_rate'])

all_dates = csi.index[csi.index >= START_DATE]
wm = OrderedDict()
for dt in all_dates: iso=dt.isocalendar(); wm[(iso[0],iso[1])]=dt
wd = pd.DatetimeIndex(list(wm.values())).sort_values()
existing = set(hist.index.strftime('%Y-%m-%d')) if len(hist)>0 else set()
missed = [(dt, dt.strftime('%Y-%m-%d')) for dt in wd if dt.strftime('%Y-%m-%d') not in existing]

if missed:
    new_rows = []; ci=hist['dca_amount'].sum() if len(hist)>0 else 0; cs=hist['shares_bought'].sum() if len(hist)>0 else 0
    for dt,ds in missed:
        nc=float(csi.loc[dt]); shares=dca_amount/nc; ci+=dca_amount; cs+=shares
        new_rows.append({'csi_close':nc,'dca_amount':dca_amount,'shares_bought':shares,
                         'cum_invested':ci,'cum_shares':cs,'market_value':cs*nc,'pnl':cs*nc-ci,'return_rate':(cs*nc/ci-1)*100 if ci>0 else 0})
    ndf=pd.DataFrame(new_rows, index=[pd.Timestamp(ds) for _,ds in missed])
    hist=pd.concat([hist,ndf]).sort_index(); hist.index.name='date'

if len(hist)>0:
    hist=hist.sort_index(); ci=0;cs=0
    for idx in hist.index:
        ci+=hist.loc[idx,'dca_amount']; cs+=hist.loc[idx,'shares_bought']; nv=hist.loc[idx,'csi_close']
        hist.loc[idx,'cum_invested']=ci; hist.loc[idx,'cum_shares']=cs
        hist.loc[idx,'market_value']=cs*nv; hist.loc[idx,'pnl']=cs*nv-ci
        hist.loc[idx,'return_rate']=(cs*nv/ci-1)*100 if ci>0 else 0
    hist.to_csv(HISTORY_CSV, float_format='%.6f'); total_inv=ci; total_sh=cs
else: total_inv=0; total_sh=0

cur_val=total_sh*csi_cur; pnl=cur_val-total_inv; ret=pnl/total_inv*100 if total_inv>0 else 0
csi_start=csi[csi.index>=START_DATE].iloc[0]; csi_ret=(csi_cur/csi_start-1)*100

vals=hist['cum_shares']*hist['csi_close'] if len(hist)>0 else pd.Series([0])
peak=vals.expanding().max(); dd=float((vals/peak-1).min())*100 if len(vals)>0 else 0
csi_since=csi[csi.index>=START_DATE]; csi_peak=csi_since.expanding().max()
csi_dd=float((csi_since/csi_peak-1).min())*100 if len(csi_since)>0 else 0

r180=csi.iloc[-180:]; ts_180=[str(d)[:10] for d in r180.index]; vals_180=[float(v) for v in r180.values]
ma_180=[float(v) for v in ma200.iloc[-180:].values]
ratio_hist=(csi/ma200).dropna().iloc[-360:]
rts=[str(d)[:10] for d in ratio_hist.index]; rvs=[float(v) for v in ratio_hist.values]
hts=[str(d)[:10] for d in hist.index] if len(hist)>0 else []
hvs=[float(v) for v in (hist['cum_shares']*hist['csi_close']).values] if len(hist)>0 else []
his=[float(v) for v in hist['cum_invested'].values] if len(hist)>0 else []

out = {
    'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
    'last_trading_day': csi.index[-1].strftime('%Y-%m-%d'),
    'csi': round(csi_cur,2), 'ma200': round(ma200_cur,2), 'ratio': round(ratio,4),
    'ratio_formula': f"{csi_cur:.0f} / {ma200_cur:.0f} = {ratio:.4f}",
    'pct_rank': round(p_ma,1), 'score': score, 'valuation_label': label,
    'valuation_color': clr, 'multiplier': multiplier,
    'base_weekly': round(BASE_WEEKLY,0), 'dca_amount': dca_amount,
    'target_total': TARGET_TOTAL, 'target_years': TARGET_YEARS,
    'start_date': START_DATE, 'min_unit': MIN_UNIT,
    'total_invested': round(total_inv,0), 'total_shares': round(total_sh,6),
    'current_value': round(cur_val,0), 'pnl': round(pnl,0),
    'return_rate': round(ret,2), 'csi_return': round(csi_ret,2),
    'portfolio_max_dd': round(dd,4), 'csi_max_dd': round(csi_dd,4),
    'pe_cur': round(pe_cur,2) if pe_cur else None, 'pe_pct': round(pe_pct,1) if pe_pct else None,
    'dy_cur': round(dy_cur*100,2) if dy_cur else None, 'dy_pct': round(dy_pct,1) if dy_pct else None,
    'ts_180': ts_180, 'vals_180': vals_180, 'ma_180': ma_180,
    'ratio_ts': rts, 'ratio_vals': rvs,
    'hist_ts': hts, 'hist_vals': hvs, 'hist_invested': his,
}

with open(OUTPUT_JSON, 'w', encoding='utf-8') as f:
    json.dump(out, f, ensure_ascii=False, indent=1, default=str)
print(f"Output: {OUTPUT_JSON} | Total: {total_inv:,.0f} CNY | Value: {cur_val:,.0f} CNY")
