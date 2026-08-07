# -*- coding: utf-8 -*-
"""10只基金估值表 -> 投向资产穿透汇总（穿透到子基金底层，2026-06-30）"""
import pandas as pd, glob, sys, re, csv
from collections import defaultdict
sys.stdout.reconfigure(encoding='utf-8')

files = sorted(glob.glob(r'.reasonix/attachments/clipboard-20260806-115134.*.xls'))
FUND_NAMES = {
    '000011.xls': '闻道灵动多空1号', '000012.xls': '闻道灵动多空2号',
    '000013.xls': '闻道全周期尊享1号', '000014.xls': '闻道稳健一号',
    '000015.xls': '闻道量化进取', '000016.xls': '闻道金牛优选',
    '000017.xls': '闻道进取3号', '000018.xls': '闻道金牛优选2号',
    '000019.xls': '闻道进取2号', '000020.xls': '闻道稳健2号',
}
# 底层子基金：文件 -> 净资产(2026-06-30, 元)
SUB_NAV = {
    '000011.xls': 77881450.96,  # 灵动多空1号
    '000013.xls': 56720073.37,  # 全周期尊享1号
    '000017.xls': 46740673.92,  # 进取3号
    '000018.xls': 56636702.39,  # 金牛优选2号
    '000019.xls': 38109842.35,  # 进取2号
}
SUBKEY_OF_FILE = {'000011.xls':'AGX17B','000013.xls':'AUW65B','000017.xls':'TD517B',
                  '000018.xls':'TL258B','000019.xls':'VQ608B'}
TOTAL_NAV = 513383634.0  # 10只基金净资产合计(2026-06-30)

STK_PRE = ('11020101','11023101','11024101','1102C101','11023301','11028101')
BND_PRE = ('11031201','11031206','11033201','11033206')
FND_PRE = ('11050301','11050201')
PE_PRE = '11090601'
FUT_RE = re.compile(r'^3102[A-Z0-9]{2}(01|02)[A-Za-z0-9-]+$')
DOT_LEAF = re.compile(r'^(1102|1103|1105|1106|1108|1109|3102)\..+\..+\..+$')

def clean_name(nm):
    nm = str(nm).strip()
    return nm.split('.')[-1].strip() if '.' in nm else nm

def direction(pnm):
    return 'S' if ('空' in pnm or '卖' in pnm or '义务' in pnm) else 'L'

def parse_invest(path):
    """返回 (agg, nleaf)。agg: key -> dict(cost,mkt,names,cat)"""
    df = pd.ExcelFile(path).parse('Sheet1', header=None)
    hdr = None
    for i in range(min(8, len(df))):
        if str(df.iloc[i,0]).strip() == '科目代码':
            hdr = i; break
    ncol = df.shape[1]
    cost_i, mkt_i = (7,11) if ncol==16 else ((6,9) if ncol==14 else (4,7))
    rows = []
    for i in range(hdr+1, len(df)):
        code = str(df.iloc[i,0]).strip()
        if not code or not code.startswith(('1102','1103','1105','1106','1108','1109','3102')):
            continue
        rows.append((code, str(df.iloc[i,1]), df.iloc[i,cost_i], df.iloc[i,mkt_i]))
    name_by_prefix = {c: n for c, n, _, _ in rows}
    agg = defaultdict(lambda: dict(cost=0.0, mkt=0.0, names=set(), cat=''))
    nleaf = 0
    for code, nm, c, m in rows:
        if pd.isna(c) and pd.isna(m):
            continue
        c = float(c) if pd.notna(c) else 0.0
        m = float(m) if pd.notna(m) else 0.0
        if '.' in code and DOT_LEAF.match(code):
            parts = code.split('.')
            key3 = '.'.join(parts[:3])
            pnm = name_by_prefix.get(key3, '')
            token = parts[-1].split(' ')[0]
            if code.startswith('3102'):
                # 名义价值口径：只取“初始合约价值/成本”行(第3段=01)，冲抵行(02)不参与
                if parts[2] == '02':
                    continue
                key = 'FUT|' + direction(pnm) + '|' + clean_name(nm); cat = '期货/期权'
            elif code.startswith('1102'):
                key = 'STK|' + token; cat = '股票'
            elif code.startswith('1103'):
                key = 'BND|' + token; cat = '债券/可转债'
            elif code.startswith(('1105','1106')):
                key = 'FND|' + token; cat = '公募基金(ETF/开放)'
            else:
                key = 'PE|' + token; cat = '私募基金/资管计划'
            agg[key]['cost'] += c; agg[key]['mkt'] += m
            agg[key]['names'].add(clean_name(nm)); agg[key]['cat'] = cat
            nleaf += 1
        elif code.startswith('1102'):
            for pre in STK_PRE:
                if code.startswith(pre) and len(code) == len(pre)+6:
                    token = code[len(pre):].lstrip('H')
                    key = 'STK|' + token
                    agg[key]['cost'] += c; agg[key]['mkt'] += m
                    agg[key]['names'].add(clean_name(nm)); agg[key]['cat'] = '股票'
                    nleaf += 1; break
        elif code.startswith('1103'):
            for pre in BND_PRE:
                if code.startswith(pre) and len(code) == len(pre)+6:
                    key = 'BND|' + code[-6:]
                    agg[key]['cost'] += c; agg[key]['mkt'] += m
                    agg[key]['names'].add(clean_name(nm)); agg[key]['cat'] = '债券/可转债'
                    nleaf += 1; break
        elif code.startswith(('1105','1106')):
            for pre in FND_PRE:
                if code.startswith(pre) and len(code) == len(pre)+6:
                    key = 'FND|' + code[-6:]
                    agg[key]['cost'] += c; agg[key]['mkt'] += m
                    agg[key]['names'].add(clean_name(nm)); agg[key]['cat'] = '公募基金(ETF/开放)'
                    nleaf += 1; break
        elif code.startswith('1109'):
            if code.startswith(PE_PRE) and len(code) > len(PE_PRE):
                key = 'PE|' + code[len(PE_PRE):]
                agg[key]['cost'] += c; agg[key]['mkt'] += m
                agg[key]['names'].add(clean_name(nm)); agg[key]['cat'] = '私募基金/资管计划'
                nleaf += 1
        elif code.startswith('3102'):
            mm = FUT_RE.match(code)
            if mm:
                if mm.group(1) == '02':
                    continue  # 冲销行不参与（名义价值口径）
                pnm = name_by_prefix.get(code[:6], '') or name_by_prefix.get(code[:8], '')
                key = 'FUT|' + direction(pnm) + '|' + clean_name(nm)
                agg[key]['cost'] += c; agg[key]['mkt'] += m
                agg[key]['names'].add(clean_name(nm)); agg[key]['cat'] = '期货/期权'
                nleaf += 1
    return agg, nleaf

# ---- 1. 直接层（10只基金） ----
direct = {}
hold_pe = defaultdict(float)   # 子基金key -> 被母基金持有市值合计
hold_pe_cost = defaultdict(float)
full_of = {f.split('-')[-1]: f for f in files}
for f in files:
    agg, _ = parse_invest(f)
    direct[f] = agg
    for k, v in agg.items():
        if k.startswith('PE|'):
            hold_pe[k.split('|')[1]] += v['mkt']
            hold_pe_cost[k.split('|')[1]] += v['cost']

# ---- 2. 穿透摊薄 ----
final = defaultdict(lambda: dict(cost=0.0, mkt=0.0, names=set(), cat=''))
print('=== 穿透过程（子基金 -> 摊薄权重） ===')
thin_info = {}
for sub_short, nav in SUB_NAV.items():
    sub_f = full_of[sub_short]
    subkey = SUBKEY_OF_FILE[sub_short]
    held = hold_pe.get(subkey, 0.0)
    w = held / nav if nav else 0.0
    subagg, _ = parse_invest(sub_f)
    thin_info[subkey] = (held, nav, w)
    for k, v in subagg.items():
        if k.startswith('PE|'):
            continue
        final[k]['cost'] += v['cost'] * w
        final[k]['mkt'] += v['mkt'] * w
        final[k]['names'] |= v['names']; final[k]['cat'] = v['cat']
for subkey, (held, nav, w) in sorted(thin_info.items()):
    print(f"  {subkey:>8}: 被母基金持有 {held:>13,.0f} 元 / 净资产 {nav:>13,.0f} 元 = {w*100:6.2f}%")

# ---- 3. 直接层并入（私募项只保留未穿透的外部资管） ----
for f in files:
    for k, v in direct[f].items():
        if k.startswith('PE|'):
            sub = k.split('|')[1]
            if sub in SUBKEY_OF_FILE.values():
                continue  # 闻道系子基金已穿透，剔除
        final[k]['cost'] += v['cost']
        final[k]['mkt'] += v['mkt']
        final[k]['names'] |= v['names']; final[k]['cat'] = v['cat']

# ---- 4. 输出 ----
print('口径：非期货标的=市值；期货/期权=名义合约价值(最新结算价×乘数×手数，多头为正/空头为负)；期权=权利金市值')
print('占比分母=10只基金净资产合计')
total_mkt = sum(v['mkt'] for v in final.values())
total_cost = sum(v['cost'] for v in final.values())
fut_long = sum(v['mkt'] for k, v in final.items() if k.startswith('FUT|L'))
fut_short = sum(v['mkt'] for k, v in final.items() if k.startswith('FUT|S'))
print(f"\n合计：成本 {total_cost:,.0f} 元 | 市值/名义价值(净额) {total_mkt:,.0f} 元 | 期货多头名义 {fut_long:,.0f} | 期货空头名义 {fut_short:,.0f}")
print(f"10基金净资产合计 {TOTAL_NAV:,.0f} 元\n")
rows = []
for k, v in final.items():
    cat, rest = k.split('|', 1)
    name = max(v['names'], key=len) if v['names'] else rest
    rows.append((v['mkt'], cat, name, rest, v['cost'], v['mkt']))
rows.sort(key=lambda x: -x[0])
with open('投向资产穿透汇总表_20260630.csv', 'w', newline='', encoding='utf-8-sig') as fh:
    w = csv.writer(fh)
    w.writerow(['排名', '资产类别', '投资标的', '代码/合约', '投资成本(元)', '市值/名义价值(元)', '占10基金净资产%', '备注'])
    for i, (m, cat, name, code, cost, mkt) in enumerate(rows, 1):
        note = '名义价值口径' if cat == 'FUT' else '市值口径'
        w.writerow([i, cat, name, code, round(cost,2), round(mkt,2), round(mkt/TOTAL_NAV*100,4), note])
print(f"已导出 投向资产穿透汇总表_20260630.csv 共 {len(rows)} 个标的\n")
print(f"{'排名':<4}{'类别':<10}{'投资标的':<36}{'摊后市值/名义(元)':>18}{'占净资产%':>10}")
for i, (m, cat, name, code, cost, mkt) in enumerate(rows[:25], 1):
    nm = (name + ' ' + code).strip()
    print(f"{i:<5}{cat:<11}{nm[:34]:<36}{mkt:>18,.0f}{mkt/TOTAL_NAV*100:>9.2f}%")
bycat = defaultdict(lambda: [0.0, 0.0])
for k, v in final.items():
    bycat[v['cat']][0] += v['cost']; bycat[v['cat']][1] += v['mkt']
print('\n--- 穿透后按资产类别汇总（市值/名义价值） ---')
for cat, (c, m) in sorted(bycat.items(), key=lambda x: -x[1][1]):
    print(f"  {cat:<14} 成本 {c:>16,.0f} | 市值/名义 {m:>16,.0f} | 占净资产 {m/TOTAL_NAV*100:6.2f}%")
print(f"  其中：期货多头名义 {fut_long:,.0f} 元（占净资产 {fut_long/TOTAL_NAV*100:.2f}%）| 期货空头名义 {fut_short:,.0f} 元（占净资产 {fut_short/TOTAL_NAV*100:.2f}%）")
PY_END
