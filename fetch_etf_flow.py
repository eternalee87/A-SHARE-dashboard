"""国家队ETF份额跟踪 - 数据抓取脚本"""
import sys, io, os, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import pandas as pd
import akshare as ak
from datetime import datetime, timedelta

BASE = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(BASE, 'data', 'etf_flow.csv')

# 国家队常用宽基ETF
TARGET_ETFS = {
    '510300': ('沪深300ETF华泰', 'SSE'),
    '510310': ('沪深300ETF易方达', 'SSE'),
    '510330': ('沪深300ETF华夏', 'SSE'),
    '159919': ('沪深300ETF嘉实', 'SZSE'),
    '510050': ('上证50ETF', 'SSE'),
    '510500': ('中证500ETF', 'SSE'),
    '512100': ('中证1000ETF', 'SSE'),
    '159845': ('中证1000ETF华夏', 'SZSE'),
    '159915': ('创业板ETF', 'SZSE'),
    '588000': ('科创50ETF', 'SSE'),
}

def fetch_sse(date_str):
    """获取上交所ETF某日份额"""
    try:
        df = ak.fund_etf_scale_sse(date=date_str)
        df = df[['基金代码', '基金份额']].copy()
        df['日期'] = pd.to_datetime(date_str)
        df.columns = ['code', 'shares', 'date']
        return df
    except Exception as e:
        print(f"  SSE {date_str} error: {e}")
        return None

def fetch_szse():
    """获取深交所ETF最新份额"""
    try:
        df = ak.fund_etf_scale_szse()
        col_map = {}
        for c in df.columns:
            if '代码' in c or 'code' in str(c).lower():
                col_map[c] = 'code'
            elif '份额' in c or 'share' in str(c).lower():
                col_map[c] = 'shares'
        df = df.rename(columns=col_map)
        df = df[['code', 'shares']].copy()
        df['date'] = pd.Timestamp.now().normalize()
        return df
    except Exception as e:
        print(f"  SZSE error: {e}")
        return None

def get_trading_dates(n=15):
    """获取最近n个交易日(近似，跳过周末)"""
    dates = []
    d = datetime.now()
    while len(dates) < n:
        if d.weekday() < 5:  # Mon-Fri
            dates.append(d.strftime('%Y%m%d'))
        d -= timedelta(days=1)
    return dates

if __name__ == '__main__':
    print("=" * 50)
    print("国家队ETF份额抓取")
    print("=" * 50)

    # Get trading dates
    dates = get_trading_dates(15)
    print(f"日期范围: {dates[-1]} ~ {dates[0]}")

    all_data = []

    # SSE data for each date
    for date_str in dates:
        print(f"Fetching SSE {date_str}...", end=' ')
        df = fetch_sse(date_str)
        if df is not None:
            target = df[df['code'].isin(TARGET_ETFS.keys())]
            all_data.append(target)
            print(f"{len(target)} ETFs")
        else:
            print("failed")
        time.sleep(0.3)

    # SZSE latest data
    print("Fetching SZSE latest...", end=' ')
    df_sz = fetch_szse()
    if df_sz is not None:
        target = df_sz[df_sz['code'].isin(TARGET_ETFS.keys())]
        all_data.append(target)
        print(f"{len(target)} ETFs")
    else:
        print("failed")

    if all_data:
        combined = pd.concat(all_data, ignore_index=True)
        combined = combined.sort_values(['code', 'date'])
        
        # Pivot to get wide format: rows=code, columns=dates
        pivot = combined.pivot_table(
            values='shares', index='code', columns='date', aggfunc='first'
        )
        pivot = pivot.sort_index(axis=1)
        
        # Add names
        pivot.index = [f"{c} {TARGET_ETFS.get(c, ('',))[0]}" for c in pivot.index]
        
        pivot.to_csv(CSV_PATH)
        print(f"\n保存: {CSV_PATH}")
        print(f"ETF数量: {len(pivot)}")
        print(f"日期范围: {pivot.columns[0].strftime('%Y-%m-%d')} ~ {pivot.columns[-1].strftime('%Y-%m-%d')}")
        
        # Show latest changes
        print("\n最新日份额变化 (亿份):")
        for code in pivot.index:
            vals = pivot.loc[code].dropna()
            if len(vals) >= 2:
                delta = (vals.iloc[-1] - vals.iloc[-2]) / 1e8
                print(f"  {code}: {delta:+.2f}")
    else:
        print("No data fetched!")
