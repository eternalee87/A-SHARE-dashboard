"""
中证红利 (000922) 定投仪表盘 — 数据抓取
优先 akshare 自动抓取，失败则用本地 CSV 兜底
"""
import sys, io, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import pandas as pd

BASE = os.path.dirname(os.path.abspath(__file__))
PRICE_CSV = os.path.join(BASE, 'data', 'csi_price.csv')
PE_CSV = os.path.join(BASE, 'data', 'csi_pe.csv')

print(f"{'='*60}")
print(f"中证红利 (000922) 数据抓取")
print(f"{'='*60}")

# ===== PRICE from akshare =====
try:
    import akshare as ak
    df_price = ak.index_zh_a_hist(symbol='000922', period='daily', start_date='20040101', end_date='20301231')
    if len(df_price) > 0:
        df_price = df_price.rename(columns={'日期': 'date', '收盘': 'close'})
        df_price['date'] = pd.to_datetime(df_price['date'])
        df_price = df_price[['date', 'close']].set_index('date').sort_index()
        df_price.to_csv(PRICE_CSV, float_format='%.2f')
        print(f"Price: akshare OK, {len(df_price)} rows, {df_price.index[0].date()} ~ {df_price.index[-1].date()}, latest={df_price.iloc[-1,0]:.2f}")
    else:
        raise Exception("empty data")
except Exception as e:
    print(f"Price: akshare failed ({str(e)[:60]}), using cached CSV")
    df_price = pd.read_csv(PRICE_CSV, index_col=0, parse_dates=True)
    print(f"Price: cached {len(df_price)} rows, latest={df_price.iloc[-1,0]:.2f}")

# ===== PE from akshare =====
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
        # Merge with existing PE CSV to extend history
        if os.path.exists(PE_CSV):
            old_pe = pd.read_csv(PE_CSV, index_col=0, parse_dates=True)
            df_pe = pd.concat([old_pe, df_pe])
            df_pe = df_pe[~df_pe.index.duplicated(keep='last')].sort_index()
        df_pe.to_csv(PE_CSV, float_format='%.2f')
        print(f"PE: akshare OK, {len(df_pe)} rows, {df_pe.index[0].date()} ~ {df_pe.index[-1].date()}, latest PE={df_pe.iloc[-1,0]:.2f}")
    else:
        raise Exception("empty data")
except Exception as e:
    print(f"PE: akshare failed ({str(e)[:60]}), using cached CSV")
    if os.path.exists(PE_CSV):
        df_pe = pd.read_csv(PE_CSV, index_col=0, parse_dates=True)
        print(f"PE: cached {len(df_pe)} rows, latest PE={df_pe.iloc[-1,0]:.2f}")
    else:
        print(f"PE: no cached data")

print(f"\n{'='*60}")
print(f"数据抓取完成")
