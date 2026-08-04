"""
中证红利 (000922) 定投仪表盘 — 数据抓取
腾讯财经API (稳定) + akshare PE数据
"""
import sys, io, os, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import pandas as pd
import requests

BASE = os.path.dirname(os.path.abspath(__file__))
PRICE_CSV = os.path.join(BASE, 'data', 'csi_price.csv')
PE_CSV = os.path.join(BASE, 'data', 'csi_pe.csv')

print("=" * 60)
print("中证红利 (000922) 数据抓取")
print("=" * 60)

# ===== PRICE: 腾讯财经 K线 API =====
try:
    # Fetch last 2000 days (~8 years)
    url = 'https://web.ifzq.gtimg.cn/appstock/app/fqkline/get?param=sh000922,day,,,2000,qfq'
    r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=15)
    data = r.json()
    
    if data.get('code') == 0:
        klines = data['data']['sh000922']['day']
        rows = []
        for k in klines:
            rows.append({'date': k[0], 'close': float(k[2])})
        df_new = pd.DataFrame(rows)
        df_new['date'] = pd.to_datetime(df_new['date'])
        df_new = df_new.set_index('date').sort_index()
        
        # Merge with existing CSV to preserve old history
        if os.path.exists(PRICE_CSV):
            df_old = pd.read_csv(PRICE_CSV, index_col=0, parse_dates=True)
            df_price = pd.concat([df_old, df_new])
            df_price = df_price[~df_price.index.duplicated(keep='last')].sort_index()
        else:
            df_price = df_new
        
        df_price.to_csv(PRICE_CSV, float_format='%.2f')
        print(f"Price: Tencent OK, {len(df_price)} rows, {df_price.index[0].date()} ~ {df_price.index[-1].date()}, latest={df_price.iloc[-1,0]:.2f}")
    else:
        raise Exception(f"API returned {data}")
except Exception as e:
    print(f"Price: Tencent failed ({str(e)[:80]}), using cached")
    df_price = pd.read_csv(PRICE_CSV, index_col=0, parse_dates=True)

# ===== PE: akshare =====
try:
    import akshare as ak
    df_pe = ak.stock_zh_index_value_csindex(symbol='000922')
    if len(df_pe) > 0:
        cols = df_pe.columns.tolist()
        date_col = cols[0]
        pe_col = [c for c in cols if '盈' in c][0]
        df_pe = df_pe.rename(columns={date_col: 'date', pe_col: 'PE-TTM'})
        df_pe['date'] = pd.to_datetime(df_pe['date'])
        df_pe = df_pe[['date', 'PE-TTM']].set_index('date').sort_index()
        if os.path.exists(PE_CSV):
            old_pe = pd.read_csv(PE_CSV, index_col=0, parse_dates=True)
            df_pe = pd.concat([old_pe, df_pe])
            df_pe = df_pe[~df_pe.index.duplicated(keep='last')].sort_index()
        df_pe.to_csv(PE_CSV, float_format='%.2f')
        print(f"PE: akshare OK, {len(df_pe)} rows, latest PE={df_pe.iloc[-1,0]:.2f}")
    else:
        raise Exception("empty")
except Exception as e:
    print(f"PE: akshare failed ({str(e)[:80]}), cached")
    if os.path.exists(PE_CSV):
        print(f"  cached PE: {len(pd.read_csv(PE_CSV, index_col=0))} rows")

print(f"\n数据抓取完成")
