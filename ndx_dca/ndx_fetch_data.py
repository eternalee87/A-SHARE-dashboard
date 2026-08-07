"""
纳斯达克100定投仪表盘 — 数据抓取脚本 v2
数据源: Yahoo Finance v8 API (直连) + CNN Fear & Greed Index
"""
import sys, io, os, time, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import pandas as pd
import requests
from datetime import datetime, timedelta

BASE = os.path.dirname(os.path.abspath(__file__))
NDX_CSV = os.path.join(BASE, 'data', 'ndx_data.csv')
VIX_CSV = os.path.join(BASE, 'data', 'vix_data.csv')
CNN_JSON = os.path.join(BASE, 'data', 'cnn_fng.json')

YF_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
}

# ==================== Yahoo Finance Direct API ====================
def fetch_yahoo_chart(symbol, period1, period2=None):
    """
    Fetch historical data from Yahoo Finance v8 chart API.
    period1: start date as 'YYYY-MM-DD' or Unix timestamp
    period2: end date (default: now)
    Returns DataFrame with 'close' column or None.
    """
    if isinstance(period1, str):
        period1 = int(datetime.strptime(period1, '%Y-%m-%d').timestamp())
    if period2 is None:
        period2 = int(datetime.now().timestamp())
    elif isinstance(period2, str):
        period2 = int(datetime.strptime(period2, '%Y-%m-%d').timestamp())

    url = f'https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?period1={period1}&period2={period2}&interval=1d&events=history'
    
    try:
        r = requests.get(url, headers=YF_HEADERS, timeout=15)
        if r.status_code != 200:
            print(f"    HTTP {r.status_code}")
            return None
        data = r.json()
    except Exception as e:
        print(f"    Request error: {e}")
        return None

    result = data.get('chart', {}).get('result', [])
    if not result:
        print(f"    No data in response")
        return None

    result = result[0]
    timestamps = result.get('timestamp', [])
    quotes = result.get('indicators', {}).get('quote', [{}])[0]

    if not timestamps or 'close' not in quotes:
        print(f"    Missing timestamps or close data")
        return None

    closes = quotes['close']
    if len(timestamps) != len(closes):
        print(f"    Mismatched data length")
        return None

    # Build DataFrame
    dates = [datetime.fromtimestamp(ts).strftime('%Y-%m-%d') for ts in timestamps]
    df = pd.DataFrame({'date': dates, 'close': closes})
    df['date'] = pd.to_datetime(df['date'])
    df = df.set_index('date')
    df = df.dropna()

    return df


def update_csv_from_api(symbol, csv_path, label, lookback_years=40):
    """
    Fetch and update CSV data for a symbol using Yahoo Finance API.
    Handles incremental update.
    """
    print(f"\n{'='*50}")
    print(f"Fetching {label} ({symbol})...")

    existing = None
    if os.path.exists(csv_path):
        existing = pd.read_csv(csv_path, index_col=0, parse_dates=True)
        last_date = existing.index[-1]
        print(f"  已有 {len(existing)} 行, 最新: {last_date.strftime('%Y-%m-%d')}")

        # Incremental: fetch from last date - 5 days (for safety overlap)
        fetch_start = (last_date - timedelta(days=5)).strftime('%Y-%m-%d')
        print(f"  增量获取: {fetch_start} ~ 今日")
        df_new = fetch_yahoo_chart(symbol, fetch_start)
    else:
        # Full history
        fetch_start = (datetime.now() - timedelta(days=lookback_years * 365)).strftime('%Y-%m-%d')
        print(f"  全量获取: {fetch_start} ~ 今日")
        df_new = fetch_yahoo_chart(symbol, fetch_start)

    if df_new is None or len(df_new) == 0:
        print(f"  ERROR: No data fetched")
        return existing if existing is not None else None

    # Remove timezone info if present
    if df_new.index.tz is not None:
        df_new.index = df_new.index.tz_localize(None)

    if existing is not None:
        combined = pd.concat([existing, df_new])
        combined = combined[~combined.index.duplicated(keep='last')]
        combined = combined.sort_index()
        result = combined
    else:
        result = df_new

    result = result.dropna()
    os.makedirs(os.path.dirname(csv_path), exist_ok=True)
    result.to_csv(csv_path, float_format='%.2f')
    print(f"  保存: {csv_path}")
    print(f"  范围: {result.index[0].strftime('%Y-%m-%d')} ~ {result.index[-1].strftime('%Y-%m-%d')}")
    print(f"  最新: {result.iloc[-1, 0]:.2f}" if len(result.columns) == 1 else f"  最新 close: {result['close'].iloc[-1]:.2f}")
    print(f"  共 {len(result)} 行")
    return result


# ==================== CNN Fear & Greed Index ====================
def fetch_cnn_fng(json_path):
    """Fetch CNN Fear & Greed Index from CNN data API."""
    print(f"\n{'='*50}")
    print("Fetching CNN Fear & Greed Index...")

    url = 'https://production.dataviz.cnn.io/index/fearandgreed/graphdata'
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Referer': 'https://www.cnn.com/markets/fear-and-greed',
    }

    try:
        r = requests.get(url, headers=headers, timeout=15)
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        print(f"  ERROR fetching CNN F&G: {e}")
        if os.path.exists(json_path):
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            print(f"  使用缓存数据")
            return data
        return None

    fng = data.get('fear_and_greed', {})
    score = fng.get('score', None)
    rating = fng.get('rating', 'unknown')
    ts = fng.get('timestamp', '')

    print(f"  Score: {score:.1f} ({rating})")
    print(f"  Timestamp: {ts}")

    hist_data = data.get('fear_and_greed_historical', {}).get('data', [])
    records = []
    if hist_data:
        for point in hist_data:
            dt = pd.Timestamp(point['x'], unit='ms').strftime('%Y-%m-%d')
            records.append({
                'date': dt,
                'score': point['y'],
                'rating': point.get('rating', '')
            })
        print(f"  历史数据点: {len(records)}")

    output = {
        'current': {'score': score, 'rating': rating, 'timestamp': ts},
        'previous_close': fng.get('previous_close'),
        'previous_1_week': fng.get('previous_1_week'),
        'previous_1_month': fng.get('previous_1_month'),
        'previous_1_year': fng.get('previous_1_year'),
        'history': records[-500:] if records else [],
    }

    os.makedirs(os.path.dirname(json_path), exist_ok=True)
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=1)
    print(f"  保存: {json_path}")

    return output


# ==================== MAIN ====================
if __name__ == '__main__':
    print("=" * 60)
    print("纳斯达克100定投仪表盘 — 数据抓取 v2 (Yahoo API直连)")
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    # 1. NDX
    ndx = update_csv_from_api('%5ENDX', NDX_CSV, 'Nasdaq-100')  # %5E = ^

    # 2. VIX
    vix = update_csv_from_api('%5EVIX', VIX_CSV, 'VIX')

    # 3. CNN Fear & Greed
    cnn = fetch_cnn_fng(CNN_JSON)

    print(f"\n{'='*60}")
    print("数据抓取完成!")
    print(f"  NDX: {len(ndx) if ndx is not None else 0} 行")
    print(f"  VIX: {len(vix) if vix is not None else 0} 行")
    print(f"  CNN F&G: {'OK' if cnn else 'FAILED'}")

    # Show latest values
    if ndx is not None and len(ndx) > 0:
        print(f"\n最新数据 ({ndx.index[-1].strftime('%Y-%m-%d')}):")
        print(f"  NDX: {ndx.iloc[-1, 0]:.2f}")
    if vix is not None and len(vix) > 0:
        print(f"  VIX: {vix.iloc[-1, 0]:.2f}")
