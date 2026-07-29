"""
中证红利 (000922) 定投仪表盘 — 数据准备
数据源: 用户提供的 Excel 价格+PE 数据
"""
import sys, io, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import pandas as pd

BASE = os.path.dirname(os.path.abspath(__file__))

# Price data from Excel
px = pd.read_excel('.reasonix/attachments/clipboard-20260729-113909.300220-000002.xlsx')
px = px.dropna(subset=['日期'])
px['date'] = pd.to_datetime(px['日期'])
px = px[['date', '收盘价(元)']].rename(columns={'收盘价(元)': 'close'})
px = px.set_index('date').sort_index()

# PE data from Excel  
pe = pd.read_excel('.reasonix/attachments/clipboard-20260729-174438.679355-000004.xlsx')
pe['date'] = pd.to_datetime(pe['日期'])
pe = pe[['date', 'PE-TTM', 'EPS']].set_index('date').sort_index()

# Save
px.to_csv(os.path.join(BASE, 'data', 'csi_price.csv'), float_format='%.2f')
pe.to_csv(os.path.join(BASE, 'data', 'csi_pe.csv'), float_format='%.2f')

print(f"Price: {px.index[0].date()} ~ {px.index[-1].date()}, {len(px)} rows, latest={px.iloc[-1,0]:.2f}")
print(f"PE: {pe.index[0].date()} ~ {pe.index[-1].date()}, {len(pe)} rows, latest PE={pe.iloc[-1,0]:.2f}")
