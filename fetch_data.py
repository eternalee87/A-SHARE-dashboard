"""
A股风格指数数据抓取脚本
使用 akshare 获取全部风格指数 + 基准指数历史数据，输出统一 CSV
可在本地运行，也可在 GitHub Actions 中每日自动执行
"""
import sys, io, os, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import pandas as pd
import akshare as ak

BASE = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(BASE, 'data', 'style_indices_v2.csv')

# ==================== INDEX DEFINITIONS ====================
# (csv_column_name, akshare_symbol)
STYLE_INDICES = [
    ('大盘价值', 'sh000919'),   # 沪深300价值
    ('大盘成长', 'sh000918'),   # 沪深300成长
    ('中盘价值', 'sz399374'),   # 巨潮中盘价值
    ('中盘成长', 'sz399375'),   # 巨潮中盘成长
    ('小盘价值', 'sz399376'),   # 巨潮小盘价值
    ('小盘成长', 'sz399377'),   # 巨潮小盘成长
]

BENCHMARK_INDICES = [
    ('沪深300',   'sh000300'),
    ('上证指数',   'sh000001'),
    ('中证500',   'sh000905'),
    ('中证1000',   'sh000852'),
    ('上证50',    'sh000016'),
    ('创业板指',   'sz399006'),
    ('中证红利',   'sh000922'),
]

ALL_INDICES = STYLE_INDICES + BENCHMARK_INDICES
ALL_COLS = [name for name, _ in ALL_INDICES]
SLEEP_SEC = 0.5  # politeness delay between requests

# ==================== FETCH ====================
def fetch_one(name, symbol):
    """Fetch one index from akshare, return Series keyed by date"""
    print(f"  Fetching {name} ({symbol})...", end=' ', flush=True)
    try:
        df = ak.stock_zh_index_daily(symbol=symbol)
        df['date'] = pd.to_datetime(df['date'])
        df = df.set_index('date')
        s = df['close'].rename(name)
        print(f"{len(s)} rows, {s.index[0].strftime('%Y-%m-%d')} ~ {s.index[-1].strftime('%Y-%m-%d')}")
        return s
    except Exception as e:
        print(f"ERROR: {e}")
        return None

def fetch_all():
    """Fetch all indices and return combined DataFrame"""
    series_list = []
    for name, symbol in ALL_INDICES:
        s = fetch_one(name, symbol)
        if s is not None:
            series_list.append(s)
        time.sleep(SLEEP_SEC)
    
    df = pd.concat(series_list, axis=1)
    df = df.sort_index()
    # Forward-fill missing (some indices have different trading calendars)
    df = df.ffill()
    # Drop rows where all style indices are NaN
    style_cols = [n for n, _ in STYLE_INDICES]
    df = df.dropna(subset=style_cols, how='all')
    return df

# ==================== MAIN ====================
if __name__ == '__main__':
    print("=" * 60)
    print("A股风格指数数据抓取")
    print(f"输出: {CSV_PATH}")
    print("=" * 60)
    
    # Check if we have existing data to merge with
    existing = None
    if os.path.exists(CSV_PATH):
        existing = pd.read_csv(CSV_PATH, index_col=0, parse_dates=True)
        print(f"已有数据: {len(existing)} 行, {existing.index[0].strftime('%Y-%m-%d')} ~ {existing.index[-1].strftime('%Y-%m-%d')}")
    
    # Fetch fresh data
    print("\n抓取中...")
    df_new = fetch_all()
    
    if existing is not None:
        # Merge: existing takes priority for older data, new for recent
        # Use existing for dates before the new data's start
        new_start = df_new.index[0]
        old_part = existing[existing.index < new_start]
        combined = pd.concat([old_part, df_new])
        # Remove duplicates keeping the last (newer)
        combined = combined[~combined.index.duplicated(keep='last')]
        combined = combined.sort_index()
        print(f"\n合并后: {len(combined)} 行")
        df_final = combined
    else:
        df_final = df_new
    
    # Ensure column order
    df_final = df_final[ALL_COLS]
    
    # Save
    os.makedirs(os.path.dirname(CSV_PATH), exist_ok=True)
    df_final.to_csv(CSV_PATH, float_format='%.4f')
    print(f"\n保存完成: {CSV_PATH}")
    print(f"日期范围: {df_final.index[0].strftime('%Y-%m-%d')} ~ {df_final.index[-1].strftime('%Y-%m-%d')}")
    print(f"最新收盘 ({df_final.index[-1].strftime('%Y-%m-%d')}):")
    for col in ALL_COLS:
        print(f"  {col}: {df_final[col].iloc[-1]:.2f}")
