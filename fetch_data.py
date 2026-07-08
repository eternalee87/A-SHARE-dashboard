"""
A股风格指数数据抓取脚本 v3
主数据源: akshare (腾讯/Sina API)
备选数据源: tushare (需设置 TUSHARE_TOKEN 环境变量)
"""
import sys, io, os, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import pandas as pd
import akshare as ak

BASE = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(BASE, 'data', 'style_indices_v2.csv')

# ==================== INDEX DEFINITIONS ====================
STYLE_INDICES = [
    ('大盘价值', 'sh000919'), ('大盘成长', 'sh000918'),
    ('中盘价值', 'sz399374'), ('中盘成长', 'sz399375'),
    ('小盘价值', 'sz399376'), ('小盘成长', 'sz399377'),
]
BENCHMARK_INDICES = [
    ('沪深300','sh000300'), ('上证指数','sh000001'), ('中证500','sh000905'),
    ('中证1000','sh000852'), ('上证50','sh000016'), ('创业板指','sz399006'),
    ('中证红利','sh000922'),
]
ALL_INDICES = STYLE_INDICES + BENCHMARK_INDICES
ALL_COLS = [name for name, _ in ALL_INDICES]
SLEEP_SEC = 0.5

# ==================== TUSHARE (optional) ====================
def try_tushare_fetch(name, ts_code, start, end):
    """Try fetching via tushare if token is available"""
    token = os.environ.get('TUSHARE_TOKEN', '')
    if not token:
        return None
    try:
        import tushare as ts
        ts.set_token(token)
        pro = ts.pro_api()
        df = pro.index_daily(ts_code=ts_code, start_date=start, end_date=end)
        if df is not None and len(df) > 0:
            df['trade_date'] = pd.to_datetime(df['trade_date'])
            df = df.set_index('trade_date').sort_index()
            return df['close'].rename(name)
    except Exception as e:
        print(f"    tushare fallback error: {e}")
    return None

# ==================== AKSHARE ====================
def fetch_one_ak(name, symbol, start, end):
    """Fetch via akshare Tencent API"""
    print(f"  Fetching {name} ({symbol})...", end=' ', flush=True)
    try:
        df = ak.stock_zh_index_daily_tx(symbol=symbol, start_date=start, end_date=end)
        df['date'] = pd.to_datetime(df['date'])
        df = df.set_index('date')
        s = df['close'].rename(name)
        print(f"{len(s)} rows, {s.index[0].strftime('%Y-%m-%d')} ~ {s.index[-1].strftime('%Y-%m-%d')}")
        return s
    except Exception as e:
        print(f"ERROR: {e}")
        return None

TUSHARE_MAP = {
    '上证指数':'000001.SH','沪深300':'000300.SH','上证50':'000016.SH',
    '中证500':'000905.SH','中证1000':'000852.SH','创业板指':'399006.SZ',
    '中证红利':'000922.SH','大盘价值':'000919.SH','大盘成长':'000918.SH',
    '中盘价值':'399374.SZ','中盘成长':'399375.SZ','小盘价值':'399376.SZ','小盘成长':'399377.SZ',
}

def fetch_all(start='20130101', end='20260707'):
    """Fetch all indices, trying tushare first for latest, akshare for history"""
    series_list = []
    use_tushare = bool(os.environ.get('TUSHARE_TOKEN', ''))

    for name, symbol in ALL_INDICES:
        s = None
        # Try tushare for recent data (last 30 days) if available
        if use_tushare and name in TUSHARE_MAP:
            s = try_tushare_fetch(name, TUSHARE_MAP[name], start, end)

        # Fallback to akshare
        if s is None:
            s = fetch_one_ak(name, symbol, start, end)

        if s is not None:
            series_list.append(s)
        time.sleep(SLEEP_SEC)

    df = pd.concat(series_list, axis=1).sort_index().ffill()
    style_cols = [n for n, _ in STYLE_INDICES]
    df = df.dropna(subset=style_cols, how='all')
    return df

# ==================== MAIN ====================
if __name__ == '__main__':
    print("=" * 60)
    print("A股风格指数数据抓取 v3 (akshare + tushare)")
    token = os.environ.get('TUSHARE_TOKEN', '')
    print(f"tushare: {'已配置' if token else '未配置(仅使用akshare)'}")
    print(f"输出: {CSV_PATH}")
    print("=" * 60)

    existing = None
    if os.path.exists(CSV_PATH):
        existing = pd.read_csv(CSV_PATH, index_col=0, parse_dates=True)
        print(f"已有数据: {len(existing)} 行, {existing.index[0].strftime('%Y-%m-%d')} ~ {existing.index[-1].strftime('%Y-%m-%d')}")
        from datetime import datetime, timedelta
        last_date = existing.index[-1]
        fetch_start = (last_date - timedelta(days=30)).strftime('%Y%m%d')
        today_str = datetime.now().strftime('%Y%m%d')
        print(f"增量更新: {fetch_start} ~ {today_str}")
    else:
        fetch_start = '20130101'
        today_str = '20260707'
        print(f"全量获取: {fetch_start} ~ {today_str}")

    print("\n抓取中...")
    df_new = fetch_all(start=fetch_start, end=today_str)

    if existing is not None and len(df_new) > 0:
        new_start = df_new.index[0]
        old_part = existing[existing.index < new_start]
        combined = pd.concat([old_part, df_new])
        combined = combined[~combined.index.duplicated(keep='last')]
        combined = combined.sort_index()
        print(f"\n合并后: {len(combined)} 行")
        df_final = combined
    else:
        df_final = df_new

    df_final = df_final[ALL_COLS]
    os.makedirs(os.path.dirname(CSV_PATH), exist_ok=True)
    df_final.to_csv(CSV_PATH, float_format='%.4f')
    print(f"\n保存完成: {CSV_PATH}")
    print(f"日期范围: {df_final.index[0].strftime('%Y-%m-%d')} ~ {df_final.index[-1].strftime('%Y-%m-%d')}")
    print(f"最新收盘 ({df_final.index[-1].strftime('%Y-%m-%d')}):")
    for col in ALL_COLS:
        print(f"  {col}: {df_final[col].iloc[-1]:.2f}")
