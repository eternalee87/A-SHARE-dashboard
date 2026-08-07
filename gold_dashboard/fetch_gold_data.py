"""
黄金交易机会看板 — 数据获取模块
数据源：Yahoo Finance（国际品种）、东方财富（上海金）、FRED（美国宏观）
"""

import json
import os
import time
import datetime
from pathlib import Path

import requests

# ============================================================
# 配置
# ============================================================
OUTPUT_DIR = Path(__file__).parent / "data"
OUTPUT_DIR.mkdir(exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

DATA_FILE = OUTPUT_DIR / "gold_data.json"

YAHOO_SYMBOLS = {
    "XAU": "GC=F",          # COMEX黄金期货
    "DXY": "DX-Y.NYB",     # 美元指数
    "US10Y": "^TNX",        # 美国10年期国债收益率
    "USDCNY": "CNY=X",      # 美元/人民币
    "SPX": "^GSPC",         # 标普500
    "VIX": "^VIX",          # VIX恐慌指数
}

FRED_SERIES = {
    "DFII10": "DFII10",       # 10Y TIPS收益率
    "DFF": "DFF",             # 联邦基金利率
    "CPIAUCSL": "CPIAUCSL",   # CPI
    "CPILFESL": "CPILFESL",   # 核心CPI
    "NAPM": "NAPM",           # ISM制造业PMI
}


def fetch_yahoo(symbol, range_str="5y", interval="1d"):
    """从Yahoo Finance获取历史数据"""
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
    params = {"range": range_str, "interval": interval, "includePrePost": "false"}
    try:
        resp = requests.get(url, headers=HEADERS, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        result = data["chart"]["result"][0]
        timestamps = result["timestamp"]
        quotes = result["indicators"]["quote"][0]
        adjclose = result["indicators"]["adjclose"][0].get("adjclose", []) if "adjclose" in result["indicators"] else []

        records = []
        for i, ts in enumerate(timestamps):
            dt = datetime.datetime.utcfromtimestamp(ts).strftime("%Y-%m-%d")
            rec = {"date": dt}
            for key in ["open", "high", "low", "close"]:
                val = quotes.get(key, [None])[i]
                rec[key] = round(val, 4) if val is not None else None
            if adjclose and i < len(adjclose) and adjclose[i] is not None:
                rec["adjclose"] = round(adjclose[i], 4)
            records.append(rec)
        return records
    except Exception as e:
        print(f"  [Yahoo] {symbol}: {e}")
        return None


def fetch_fred_csv(series_id):
    """从FRED公开CSV获取数据"""
    url = f"https://fred.stlouisfed.org/data/{series_id}.txt"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=30)
        resp.raise_for_status()
        lines = resp.text.strip().split("\n")
        records = []
        for line in lines:
            if line.startswith("DATE") or not line.strip():
                continue
            parts = line.strip().split()
            if len(parts) >= 2:
                try:
                    records.append({"date": parts[0], "value": float(parts[1])})
                except ValueError:
                    continue
        return records
    except Exception as e:
        print(f"  [FRED CSV] {series_id}: {e}")
        return None


def fetch_shanghai_gold():
    """获取上海金AU9999 — 东方财富API + 新浪备用"""
    # 方法1: 东方财富
    try:
        url = "https://push2his.eastmoney.com/api/qt/stock/kline/get"
        params = {
            "secid": "113.AU9999",
            "fields2": "f51,f52,f53,f54,f55,f56,f57",
            "klt": "101",
            "fqt": "1",
            "lmt": "1",
        }
        resp = requests.get(url, headers=HEADERS, params=params, timeout=15)
        data = resp.json()
        if data.get("data") and data["data"].get("klines"):
            kline = data["data"]["klines"][0].split(",")
            if len(kline) >= 3:
                return {
                    "date": kline[0],
                    "price": float(kline[2]),
                    "open": float(kline[1]),
                    "high": float(kline[3]) if len(kline) > 3 else None,
                    "low": float(kline[4]) if len(kline) > 4 else None,
                }
    except Exception as e:
        print(f"  [EastMoney] AU9999: {e}")

    # 方法2: 新浪备用
    try:
        url = "https://hq.sinajs.cn/list=hf_AU9999"
        h = {**HEADERS, "Referer": "https://finance.sina.com.cn"}
        resp = requests.get(url, headers=h, timeout=15)
        resp.encoding = "gbk"
        for line in resp.text.split("\n"):
            if "=" in line and '"' in line:
                parts = line.split('"')[1].split(",")
                if parts[0]:
                    return {
                        "date": datetime.date.today().isoformat(),
                        "price": float(parts[0]),
                        "open": float(parts[2]) if len(parts) > 2 and parts[2] else None,
                        "high": float(parts[3]) if len(parts) > 3 and parts[3] else None,
                        "low": float(parts[4]) if len(parts) > 4 and parts[4] else None,
                    }
    except Exception:
        pass

    return None


def fetch_shanghai_gold_history(days=1260):
    """获取上海金历史数据（用于回测）"""
    try:
        url = "https://push2his.eastmoney.com/api/qt/stock/kline/get"
        params = {
            "secid": "113.AU9999",
            "fields2": "f51,f52,f53,f54,f55,f56,f57",
            "klt": "101",
            "fqt": "1",
            "lmt": str(days),
        }
        resp = requests.get(url, headers=HEADERS, params=params, timeout=30)
        data = resp.json()
        if data.get("data") and data["data"].get("klines"):
            records = []
            for kline_str in data["data"]["klines"]:
                parts = kline_str.split(",")
                if len(parts) >= 3:
                    records.append({
                        "date": parts[0],
                        "open": float(parts[1]),
                        "close": float(parts[2]),
                        "high": float(parts[3]) if len(parts) > 3 else None,
                        "low": float(parts[4]) if len(parts) > 4 else None,
                    })
            return records
    except Exception as e:
        print(f"  [EastMoney History] AU9999: {e}")
    return None


def fetch_all_data():
    """获取全部数据"""
    print("=" * 60)
    print(f"黄金看板数据获取开始: {datetime.datetime.now().isoformat()}")
    print("=" * 60)

    result = {
        "fetched_at": datetime.datetime.now().isoformat(),
        "daily": {},
        "history": {},
        "fred": {},
    }

    # ---- Yahoo Finance ----
    print("\n[Yahoo] 获取每日数据...")
    for name, symbol in YAHOO_SYMBOLS.items():
        records = fetch_yahoo(symbol)
        if records and records:
            result["history"][name] = records
            result["daily"][name] = records[-1]
            print(f"  {name} ({symbol}): {records[-1]['date']} close={records[-1].get('close')}")
        time.sleep(0.5)

    # ---- 上海金 ----
    print("\n[上海金] 获取AU9999...")
    sh_gold = fetch_shanghai_gold()
    if sh_gold:
        result["daily"]["AU9999"] = sh_gold
        print(f"  AU9999: {sh_gold.get('price')} (日期: {sh_gold.get('date')})")

    # 上海金历史
    print("\n[上海金] 获取历史数据...")
    sh_history = fetch_shanghai_gold_history()
    if sh_history:
        result["history"]["AU9999"] = sh_history
        print(f"  AU9999历史: {len(sh_history)} 条, {sh_history[0]['date']} ~ {sh_history[-1]['date']}")

    # ---- FRED ----
    print("\n[FRED] 获取宏观数据...")
    for name, series_id in FRED_SERIES.items():
        records = fetch_fred_csv(series_id)
        if records:
            result["fred"][name] = records[-120:]  # 保留最近120条
            latest = records[-1]
            result["daily"][f"fred_{name}"] = {"date": latest["date"], "value": latest["value"]}
            print(f"  {name} ({series_id}): {latest['date']} = {latest['value']}")
        time.sleep(0.3)

    # ---- 计算衍生指标 ----
    print("\n[Calc] 计算衍生指标...")
    _calc_derived(result)

    # ---- 保存 ----
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2, default=str)
    file_size = DATA_FILE.stat().st_size / 1024
    print(f"\n数据已保存至: {DATA_FILE} ({file_size:.1f} KB)")

    return result


def _calc_derived(result):
    """计算衍生指标"""
    daily = result["daily"]
    history = result["history"]
    fred = result.get("fred", {})

    # 1. 实际利率 = TIPS收益率（优先）或 10Y名义-CPI同比
    tips_val = None
    if "fred_DFII10" in daily:
        tips_val = daily["fred_DFII10"]["value"]
        daily["real_yield"] = {"value": tips_val, "source": "10Y TIPS (DFII10)"}
    elif "US10Y" in daily:
        est = daily["US10Y"].get("close", 0) - 2.5
        daily["real_yield"] = {"value": round(est, 2), "source": "10Y名义 - 2.5%(估计CPI)"}

    # 2. 上海金 vs 伦敦金溢价
    if "XAU" in daily and "AU9999" in daily:
        xau_usd = daily["XAU"].get("close", 0)
        au9999_cny = daily["AU9999"].get("price", 0)
        usdcny = daily.get("USDCNY", {}).get("close", 7.2)
        if xau_usd and au9999_cny and usdcny:
            oz_to_gram = 31.1035
            implied_cny = xau_usd * usdcny / oz_to_gram
            daily["gold_premium"] = {
                "au9999_cny_per_gram": round(au9999_cny, 2),
                "xau_usd_per_oz": xau_usd,
                "usdcny": usdcny,
                "implied_cny_per_gram": round(implied_cny, 2),
                "premium_pct": round((au9999_cny / implied_cny - 1) * 100, 2),
            }

    # 3. 美国经济象限指标
    # PMI
    if "fred_NAPM" in daily:
        daily["ism_pmi"] = daily["fred_NAPM"]["value"]
    # CPI同比
    if "fred_CPIAUCSL" in daily:
        daily["cpi_headline"] = daily["fred_CPIAUCSL"]["value"]
    if "fred_CPILFESL" in daily:
        daily["cpi_core"] = daily["fred_CPILFESL"]["value"]

    # 联邦基金利率
    if "fred_DFF" in daily:
        daily["fed_rate"] = daily["fred_DFF"]["value"]

    # 4. 黄金技术统计
    if "XAU" in history:
        prices = [r["close"] for r in history["XAU"] if r.get("close")]
        if len(prices) >= 200:
            current = prices[-1]
            ma50 = sum(prices[-50:]) / 50
            ma200 = sum(prices[-200:]) / 200
            y1_prices = prices[-252:] if len(prices) >= 252 else prices
            daily["gold_stats"] = {
                "current": current,
                "ma50": round(ma50, 2),
                "ma200": round(ma200, 2),
                "ma50_ratio": round(current / ma50, 4),
                "ma200_ratio": round(current / ma200, 4),
                "max_1y": round(max(y1_prices), 2),
                "min_1y": round(min(y1_prices), 2),
                "pct_from_1y_low": round((current / min(y1_prices) - 1) * 100, 2),
                "pct_from_1y_high": round((current / max(y1_prices) - 1) * 100, 2),
            }

    # 5. DXY统计
    if "DXY" in history:
        dxy_prices = [r["close"] for r in history["DXY"] if r.get("close")]
        if len(dxy_prices) >= 50:
            current_dxy = dxy_prices[-1]
            daily["dxy_stats"] = {
                "current": current_dxy,
                "ma50": round(sum(dxy_prices[-50:]) / 50, 2),
                "ma200": round(sum(dxy_prices[-200:]) / 200, 2) if len(dxy_prices) >= 200 else None,
            }

    # 6. 实际利率趋势(短期: 3个月)
    if "DFII10" in fred and len(fred["DFII10"]) >= 60:
        tips_data = fred["DFII10"]
        recent = [d["value"] for d in tips_data[-60:]]
        daily["tips_trend"] = {
            "current": tips_data[-1]["value"],
            "ma_1m": round(sum(recent[-20:]) / min(20, len(recent[-20:])), 2),
            "ma_3m": round(sum(recent) / len(recent), 2),
            "direction": "up" if tips_data[-1]["value"] > sum(recent[:30]) / 30 else "down",
        }

    print("  衍生指标计算完成")


if __name__ == "__main__":
    fetch_all_data()
