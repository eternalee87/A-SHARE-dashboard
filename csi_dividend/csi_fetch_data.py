"""
中证红利质量指数 (931468) 定投仪表盘 — 数据抓取
数据源: akshare
"""
import sys, io, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import pandas as pd
import akshare as ak

BASE = os.path.dirname(os.path.abspath(__file__))
CSI_CSV = os.path.join(BASE, 'data', 'csi_data.csv')

print("=" * 60)
print("中证红利质量指数 (931468) 数据抓取")
print(f"时间: {pd.Timestamp.now()}")
print("=" * 60)

# Fetch full history
df = ak.index_zh_a_hist(symbol='931468', period='daily', start_date='20040101', end_date='20301231')

# Map columns
df = df.rename(columns={
    '日期': 'date', '收盘': 'close', '开盘': 'open',
    '最高': 'high', '最低': 'low', '成交量': 'volume'
})
df['date'] = pd.to_datetime(df['date'])
df = df.set_index('date')[['close']].dropna()
df = df.sort_index()

os.makedirs(os.path.dirname(CSI_CSV), exist_ok=True)
df.to_csv(CSI_CSV, float_format='%.2f')
print(f"Saved: {CSI_CSV}")
print(f"Range: {df.index[0].strftime('%Y-%m-%d')} ~ {df.index[-1].strftime('%Y-%m-%d')}")
print(f"Rows: {len(df)}, Latest: {df.iloc[-1, 0]:.2f}")
