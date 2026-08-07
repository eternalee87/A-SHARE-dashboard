"""回溯历史类似时期和市场环境"""

import json

d = json.load(open('data/gold_data.json', 'r', encoding='utf-8'))
prices = [(r['date'], r['close']) for r in d['history']['XAU'] if r.get('close')]
dxy_list = [(r['date'], r['close']) for r in d['history']['DXY'] if r.get('close')]
y10_list = [(r['date'], r['close']) for r in d['history']['US10Y'] if r.get('close')]


def nearest(lst, target):
    best = None
    for x in lst:
        if x[0] <= target:
            best = x
    return best


def ma_at(idx, period):
    if idx < period - 1:
        return None
    return sum(p[1] for p in prices[idx - period + 1:idx + 1]) / period


# ================================================
# Part 1: 季度快照
# ================================================
checkpoints = [
    ('2022-01-03', '2022Q1: 美联储启动加息周期'),
    ('2022-03-08', '2022-03: 金价见顶 $2,070 (俄乌冲突后高点)'),
    ('2022-07-14', '2022-07: 死叉形成，回撤加深'),
    ('2022-09-28', '2022-09: 金价阶段底 $1,622 (-21.5%)'),
    ('2022-11-03', '2022-11: FOMC加息75bp但暗示放缓'),
    ('2022-12-30', '2022-12: 死叉结束，金叉即将形成'),
    ('2023-01-26', '2023-01: MA50金叉MA200'),
    ('2023-03-09', '2023-03: SVB倒闭，黄金避险跳涨'),
    ('2023-05-04', '2023-05: 金价冲$2,060，接近前高'),
    ('2024-01-02', '2024Q1: 金价横盘 $2,000-2,100'),
    ('2024-03-08', '2024-03: 金价突破 $2,100 创历史新高'),
    ('2024-09-26', '2024-09: 金价$2,650，美联储开始降息'),
    ('2025-01-02', '2025Q1: 金价$2,650，牛市加速'),
    ('2025-04-02', '2025-04: 对等关税冲击，金价短暂回调'),
    ('2025-06-19', '2025-06: 金价冲 $5,300+ 历史极值'),
    ('2025-10-13', '2025-10: 金价$4,100，牛市途中'),
    ('2026-01-02', '2026Q1: 金价反弹至$5,000'),
    ('2026-03-09', '2026-03: 金价$5,092 二次见顶'),
    ('2026-07-16', '2026-07: 近期低点 ~$3,900 (-26.6%)'),
    ('2026-08-05', '2026-08: 当前 $4,222，MA20站上但死叉'),
]

print("=" * 100)
print("  黄金关键时间点全景 (2022-2026)")
print("=" * 100)
print(f"{'Date':<12} {'Gold':>8} {'MA50':>8} {'MA200':>8} {'DXY':>7} {'10Y%':>6} {'DD%':>6} {'Cross':<8} {'Context'}")
print("-" * 100)

for target_date, context in checkpoints:
    g = nearest(prices, target_date)
    dx = nearest(dxy_list, target_date)
    y10 = nearest(y10_list, target_date)
    if not g:
        continue

    idx = next((i for i, p in enumerate(prices) if p[0] == g[0]), -1)
    if idx < 0:
        continue

    gold_price = g[1]
    ma50 = ma_at(idx, 50)
    ma200 = ma_at(idx, 200)

    y1_start = max(0, idx - 252)
    y1_high = max(p[1] for p in prices[y1_start:idx + 1])
    dd = (gold_price / y1_high - 1) * 100

    cross = ""
    if ma50 and ma200:
        cross = "GOLDEN" if ma50 > ma200 else "DEATH"

    def fmt(v, prec=0, dollar=False):
        if v is None:
            return "     N/A"
        pfx = "$" if dollar else ""
        return f"{pfx}{v:>{7+int(dollar)}.{prec}f}" if prec > 0 else f"{pfx}{v:>{7+int(dollar)}.0f}"

    print(f"{g[0]:<12} {fmt(gold_price, 0, True)} {fmt(ma50, 0, True)} {fmt(ma200, 0, True)} "
          f"{fmt(dx[1] if dx else None, 2):>7} {fmt(y10[1] if y10 else None, 2):>6} "
          f"{dd:>+5.1f}% {cross:<8} {context}")

# ================================================
# Part 2: 搜索所有死叉周期
# ================================================
print()
print("=" * 100)
print("  所有 MA50/MA200 死叉周期 及 后续走势")
print("=" * 100)

dc_periods = []
in_dc = False
dc_start = 0

for idx in range(200, len(prices)):
    ma50_c = ma_at(idx, 50)
    ma200_c = ma_at(idx, 200)
    is_dc = ma50_c and ma200_c and ma50_c < ma200_c

    if is_dc and not in_dc:
        dc_start = idx
        in_dc = True
    elif not is_dc and in_dc:
        dc_end = idx - 1
        in_dc = False

        end_price = prices[dc_end][1]
        start_price = prices[dc_start][1]
        dc_days = dc_end - dc_start + 1
        dd_start = (start_price / max(p[1] for p in prices[max(0, dc_start - 252):dc_start + 1]) - 1) * 100
        dd_end = (end_price / max(p[1] for p in prices[max(0, dc_end - 252):dc_end + 1]) - 1) * 100

        # Forward from END of death cross
        for m, label in [(1, '1M'), (3, '3M'), (6, '6M'), (12, '12M')]:
            fwd_i = min(dc_end + 21 * m, len(prices) - 1)
            ret = (prices[fwd_i][1] / end_price - 1) * 100
            dc_periods.append({
                'start': prices[dc_start][0], 'end': prices[dc_end][0],
                'days': dc_days,
                'start_price': start_price, 'end_price': end_price,
                'dd_start': round(dd_start, 1), 'dd_end': round(dd_end, 1),
                'period': label, 'fwd_ret': round(ret, 1),
            })

# Catch in-progress
if in_dc:
    dc_end = len(prices) - 1
    start_price = prices[dc_start][1]
    end_price = prices[dc_end][1]
    dd_end = (end_price / max(p[1] for p in prices[max(0, dc_end - 252):dc_end + 1]) - 1) * 100
    print(f"\n  ** 当前进行中的死叉 ** {prices[dc_start][0][:10]} ~ {prices[dc_end][0][:10]} "
          f"({dc_end - dc_start + 1}天), 回撤{dd_end:.1f}%")

# Summary by forward period
print()
print(f"{'死叉期间':<26} {'持续':>5} {'结束价':>8} {'死叉内DD':>8} {'1M Fwd':>8} {'3M Fwd':>8} {'6M Fwd':>8} {'12M Fwd':>9}")
print("-" * 95)

# Unique DC periods
seen = set()
for dp in dc_periods:
    key = dp['start'] + dp['end']
    if key not in seen:
        seen.add(key)
        # Print first occurrence (1M forward)
        continues = [x for x in dc_periods if x['start'] == dp['start'] and x['end'] == dp['end']]
        rets = {}
        for c in continues:
            rets[c['period']] = c['fwd_ret']
        
        f1 = f"{rets.get('1M', 0):+.1f}%"
        f3 = f"{rets.get('3M', 0):+.1f}%"
        f6 = f"{rets.get('6M', 0):+.1f}%"
        f12 = f"{rets.get('12M', 0):+.1f}%"
        
        dd_label = f"{dp['dd_end']:+.1f}%"
        marker = " <-- NOW" if dp['end'] >= '2026-07' else ""
        print(f"{dp['start'][:10]} ~ {dp['end'][:10]}  {dp['days']:>4}d ${dp['end_price']:>7,.0f} {dd_label:>8} {f1:>8} {f3:>8} {f6:>8} {f12:>9}{marker}")

# ================================================
# Part 3: 2022 vs 2026 深度对比
# ================================================
print()
print("=" * 100)
print("  2022 死叉期 vs 2026 死叉期 深度对比")
print("=" * 100)

# Find the 2022 DC period
dc_2022 = [x for x in dc_periods if x['start'][:4] == '2022']
dc_2026_current = (prices[dc_start][0], prices[len(prices) - 1][0]) if in_dc else (None, None)

print()
print("  维度            | 2022死叉期                    | 2026死叉期 (当前)")
print("  ----------------|------------------------------|------------------------------")

comparisons = [
    ("金价区间", 
     "$1,722 ~ $1,826", 
     f"${prices[dc_start][1]:,.0f} ~ ${prices[len(prices)-1][1]:,.0f}"),
    ("回撤幅度",
     "从$2,070跌至$1,622 (-21.5%)",
     "从$5,318跌至~$3,900 (-26.6%)"),
    ("死叉持续时间",
     "约5个月 (2022-07 ~ 2022-12)",
     "当前约1个月 (2026-07 ~ now)"),
    ("美联储政策",
     "暴力加息: 1.75% → 4.50%，75bp×4次",
     "降息周期中: 5.50% → 3.63%，已降息6次"),
    ("美元DXY",
     "DXY 107→114 强势升值",
     "DXY 99~101 弱势震荡"),
    ("实际利率",
     "10Y TIPS从-1%急升至+1.6%",
     "TIPS 2.4% 相对稳定"),
    ("通胀环境",
     "CPI 9.1%→7.1%，高位回落",
     "CPI ~2.5%，关税驱动可能反弹"),
    ("宏观背景",
     "美联储历史性紧缩 + 强美元",
     "去美元化 + 财政赤字 + 央行购金"),
    ("定性信号",
     "全部利空 (加息+强美元+紧财政)",
     "全部利多 (降息+弱美元+宽财政)"),
    ("之后走势",
     "金叉形成后6个月 +20%",
     "???"),
]

for dim, v2022, v2026 in comparisons:
    print(f"  {dim:<16} | {v2022:<30} | {v2026:<30}")

print()
print("  === 核心差异 ===")
print("  2022死叉: 基本面+技术面同时利空 → 死叉是有效的趋势确认信号")
print("  2026死叉: 基本面利多 vs 技术面利空 → 死叉可能只是牛市中的深度回调")
print("  2022定性信号: 全面看空 (Fed加息+强美元+实际利率急升)")
print("  2026定性信号: 全面看多 (Fed降息+弱美元+去美元化+央行购金)")
print()
print("  历史类比: 如果当前类似2022Q4，那么死叉解除后可能出现强反弹(6M +20%)")
print("  风险: 2026回撤更深(-26.6% vs -21.5%)，且死叉刚开始1个月，可能尚未结束")
