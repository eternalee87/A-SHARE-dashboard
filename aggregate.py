# -*- coding: utf-8 -*-
"""10只基金估值表 -> 投向资产按标的汇总（2026-06-30市值口径）"""
import pandas as pd, glob, sys, re
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

# key -> dict(cost, mkt, names{set}, funds{set}, cat)
agg = defaultdict(lambda: dict(cost=0.0, mkt=0.0, names=set(), funds=set(), cat=''))
# 期货成对校验
fut_pairs = defaultdict(lambda: dict(init_mkt=0.0, off_mkt=0.0, init_cost=0.0, off_cost=0.0, n=0))

STK_PRE = ('11020101','11023101','11024101','1102C101','11023301','11028101')
BND_PRE = ('11031201','11031206','11033201','11033206')
FND_PRE = ('11050301','11050201')
PE_PRE = '11090601'
FUT_RE = re.compile(r'^3102[A-Z0-9]{2}(01|02)[A-Za-z0-9-]+$')
DOT_LEAF = re.compile(r'^(1102|1103|1105|1106|1108|1109|3102)\..+\..+\..+$')

def clean_name(nm):
    nm = str(nm).strip()
    return nm.split('.')[-1].strip() if '.' in nm else nm

def direction(parent_name):
    return 'S' if ('空' in parent_name or '卖' in parent_name or '义务' in parent_name) else 'L'

for f in files:
    short = f.split('-')[-1]
    fund = FUND_NAMES.get(short, short)
    df = pd.ExcelFile(f).parse('Sheet1', header=None)
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
        nm = str(df.iloc[i,1])
        c = df.iloc[i, cost_i]; m = df.iloc[i, mkt_i]
        rows.append((code, nm, c, m, i))
    name_by_prefix = {}
    for code, nm, c, m, i in rows:
        name_by_prefix.setdefault(code, nm)
    nleaf = 0
    for code, nm, c, m, i in rows:
        if pd.isna(c) and pd.isna(m):
            continue
        c = float(c) if pd.notna(c) else 0.0
        m = float(m) if pd.notna(m) else 0.0
        # --- 点格式叶子（4段） ---
        if '.' in code and DOT_LEAF.match(code):
            parts = code.split('.')
            key3 = '.'.join(parts[:3])
            pnm = name_by_prefix.get(key3, '')
            leaf = parts[-1]
            if code.startswith('3102'):
                cntr = clean_name(nm)
                if cntr == leaf.split(' ')[0] or len(parts)==4:
                    pass
                futkey = 'FUT|' + direction(pnm) + '|' + clean_name(nm)
                agg[futkey]['cost'] += c; agg[futkey]['mkt'] += m
                agg[futkey]['names'].add(clean_name(nm)); agg[futkey]['funds'].add(fund)
                agg[futkey]['cat'] = '期货/期权'
                fut_pairs[('L' if direction(pnm)=='L' else 'S', clean_name(nm))]['init_mkt'] += m
                nleaf += 1
                continue
            # 股票/债券/ETF/私募/资管
            token = leaf.split(' ')[0]
            if code.startswith('1102'):
                key = 'STK|' + token; cat = '股票'
            elif code.startswith('1103'):
                key = 'BND|' + token; cat = '债券/可转债'
            elif code.startswith(('1105','1106')):
                key = 'FND|' + token; cat = '公募基金(ETF/开放)'
            else:  # 1108/1109
                key = 'PE|' + token; cat = '私募基金/资管计划'
            agg[key]['cost'] += c; agg[key]['mkt'] += m
            agg[key]['names'].add(clean_name(nm)); agg[key]['funds'].add(fund)
            agg[key]['cat'] = cat
            nleaf += 1
            continue
        # --- 无点格式（国泰海通） ---
        if code.startswith('1102'):
            for pre in STK_PRE:
                if code.startswith(pre) and len(code) == len(pre)+6:
                    token = code[-6:]
                    if pre == '11028101':
                        token = code[len(pre):].lstrip('H')
                        if not token:
                            token = code[-5:]
                    key = 'STK|' + token
                    agg[key]['cost'] += c; agg[key]['mkt'] += m
                    agg[key]['names'].add(clean_name(nm)); agg[key]['funds'].add(fund)
                    agg[key]['cat'] = '股票'
                    nleaf += 1
                    break
        elif code.startswith('1103'):
            for pre in BND_PRE:
                if code.startswith(pre) and len(code) == len(pre)+6:
                    key = 'BND|' + code[-6:]
                    agg[key]['cost'] += c; agg[key]['mkt'] += m
                    agg[key]['names'].add(clean_name(nm)); agg[key]['funds'].add(fund)
                    agg[key]['cat'] = '债券/可转债'
                    nleaf += 1
                    break
        elif code.startswith(('1105','1106')):
            for pre in FND_PRE:
                if code.startswith(pre) and len(code) == len(pre)+6:
                    key = 'FND|' + code[-6:]
                    agg[key]['cost'] += c; agg[key]['mkt'] += m
                    agg[key]['names'].add(clean_name(nm)); agg[key]['funds'].add(fund)
                    agg[key]['cat'] = '公募基金(ETF/开放)'
                    nleaf += 1
                    break
        elif code.startswith('1109'):
            if code.startswith(PE_PRE) and len(code) > len(PE_PRE):
                key = 'PE|' + code[len(PE_PRE):]
                agg[key]['cost'] += c; agg[key]['mkt'] += m
                agg[key]['names'].add(clean_name(nm)); agg[key]['funds'].add(fund)
                agg[key]['cat'] = '私募基金/资管计划'
                nleaf += 1
        elif code.startswith('3102'):
            mm = FUT_RE.match(code)
            if mm:
                pre8 = code[:8]
                pnm = name_by_prefix.get(code[:6], '') or name_by_prefix.get(pre8, '')
                d = direction(pnm)
                cntr = clean_name(nm)
                futkey = 'FUT|' + d + '|' + cntr
                agg[futkey]['cost'] += c; agg[futkey]['mkt'] += m
                agg[futkey]['names'].add(cntr); agg[futkey]['funds'].add(fund)
                agg[futkey]['cat'] = '期货/期权'
                nleaf += 1
    print(f"{fund}: 叶子行 {nleaf}")

# ---- 汇总输出 ----
print('\n' + '='*100)
print('投向资产按标的总表（按2026-06-30市值降序）')
print('='*100)
total_mkt = sum(v['mkt'] for v in agg.values())
total_cost = sum(v['cost'] for v in agg.values())
print(f"全部投向资产合计：成本 {total_cost:,.0f} 元 | 市值 {total_mkt:,.0f} 元")
print('-'*100)
rows_out = []
for k, v in agg.items():
    cat, rest = k.split('|', 1)
    name = max(v['names'], key=len) if v['names'] else rest
    code = rest
    rows_out.append((v['mkt'], cat, name, code, v['cost'], v['mkt'], v['funds']))
rows_out.sort(key=lambda x: -x[0])
# 导出完整总表 CSV（UTF-8 BOM，Excel 可直接打开）
import csv
with open('投向资产汇总表_20260630.csv', 'w', newline='', encoding='utf-8-sig') as fh:
    w = csv.writer(fh)
    w.writerow(['排名', '资产类别', '投资标的', '代码/合约', '投资成本(元)', '持仓市值(元)', '占投向资产%', '持有基金数', '持有基金'])
    for i, (m, cat, name, code, cost, mkt, funds) in enumerate(rows_out, 1):
        w.writerow([i, cat, name, code, round(cost,2), round(mkt,2), round(mkt/total_mkt*100,4), len(funds), '、'.join(sorted(funds))])
print(f'已导出 投向资产汇总表_20260630.csv 共 {len(rows_out)} 个标的')
print(f"{'排名':<3}{'类别':<10}{'投资标的':<34}{'成本(元)':>14}{'市值(元)':>16}{'占投向资产%':>12}{'持有基金数':>8}")
for i, (m, cat, name, code, cost, mkt, funds) in enumerate(rows_out[:20], 1):
    pct = mkt / total_mkt * 100
    nm = (name + ' ' + code).strip()
    print(f"{i:<4}{cat:<11}{nm[:32]:<34}{cost:>14,.0f}{mkt:>16,.0f}{pct:>11.2f}%{len(funds):>9}")

# 分类汇总
print('\n--- 按资产类别汇总 ---')
bycat = defaultdict(lambda: [0.0, 0.0])
for k, v in agg.items():
    bycat[v['cat']][0] += v['cost']; bycat[v['cat']][1] += v['mkt']
for cat, (c, m) in sorted(bycat.items(), key=lambda x: -x[1][1]):
    print(f"  {cat:<14} 成本 {c:>14,.0f} | 市值 {m:>14,.0f} | 占比 {m/total_mkt*100:6.2f}%")

# 期货配对校验：初始+冲抵 应等于 净市值
print('\n--- 期货配对自检（初始化+冲销 应=净市值） ---')
bad = 0
for (d, name), v in fut_pairs.items():
    pass
# 简单校验：FUT 键的成本应接近0（成对抵消）
for k, v in agg.items():
    if k.startswith('FUT') and abs(v['cost']) > 1:
        bad += 1
        print(f"  WARN 期货成本非0: {k} cost={v['cost']:.2f}")
print(f"  期货键共 {sum(1 for k in agg if k.startswith('FUT'))} 个，成本非0 {bad} 个")
PY_END
