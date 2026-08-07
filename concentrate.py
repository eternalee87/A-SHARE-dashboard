# -*- coding: utf-8 -*-
"""每只产品穿透后持仓集中度：前5大/前10大（衍生品按市值=浮动盈亏，私募按子基金底层穿透）"""
import pandas as pd, glob, sys, re
from collections import defaultdict
sys.stdout.reconfigure(encoding='utf-8')

files = sorted(glob.glob(r'.reasonix/attachments/clipboard-20260806-115134.*.xls'))
FUND_NAMES = {
    '000011.xls': '灵动多空1号', '000012.xls': '灵动多空2号',
    '000013.xls': '全周期尊享1号', '000014.xls': '稳健一号',
    '000015.xls': '量化进取', '000016.xls': '金牛优选',
    '000017.xls': '进取3号', '000018.xls': '金牛优选2号',
    '000019.xls': '进取2号', '000020.xls': '稳健2号',
}
NAV = {  # 净资产（元）
    '000011.xls': 77881450.96, '000012.xls': 23487624.61, '000013.xls': 56720073.37,
    '000014.xls': 33053127.43, '000015.xls': 20138477.47, '000016.xls': 87336370.51,
    '000017.xls': 46740673.92, '000018.xls': 56636702.39, '000019.xls': 38109842.35,
    '000020.xls': 73279292.47,
}
SUBKEY = {'000011.xls': 'AGX17B', '000013.xls': 'AUW65B', '000017.xls': 'TD517B',
          '000018.xls': 'TL258B', '000019.xls': 'VQ608B'}

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

def parse_invest_mkt(path):
    """投资叶子按市值口径：期货=浮动盈亏(初始行+冲抵行自然抵消)，期权=权利金市值"""
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
    agg = defaultdict(lambda: dict(cost=0.0, mkt=0.0, names=set()))
    for code, nm, c, m in rows:
        if pd.isna(c) and pd.isna(m):
            continue
        c = float(c) if pd.notna(c) else 0.0
        m = float(m) if pd.notna(m) else 0.0
        if '.' in code and DOT_LEAF.match(code):
            parts = code.split('.')
            pnm = name_by_prefix.get('.'.join(parts[:3]), '')
            token = parts[-1].split(' ')[0]
            if code.startswith('3102'):
                if parts[2] not in ('01', '02'):
                    continue
                key = 'FUT|' + direction(pnm) + '|' + clean_name(nm)
            elif code.startswith('1102'):
                key = 'STK|' + token
            elif code.startswith('1103'):
                key = 'BND|' + token
            elif code.startswith(('1105','1106')):
                key = 'FND|' + token
            else:
                key = 'PE|' + token
            agg[key]['cost'] += c; agg[key]['mkt'] += m
            agg[key]['names'].add(clean_name(nm))
        elif code.startswith('1102'):
            for pre in STK_PRE:
                if code.startswith(pre) and len(code) == len(pre)+6:
                    token = code[len(pre):].lstrip('H')
                    agg['STK|'+token]['cost'] += c; agg['STK|'+token]['mkt'] += m
                    agg['STK|'+token]['names'].add(clean_name(nm)); break
        elif code.startswith('1103'):
            for pre in BND_PRE:
                if code.startswith(pre) and len(code) == len(pre)+6:
                    k = 'BND|'+code[-6:]
                    agg[k]['cost'] += c; agg[k]['mkt'] += m
                    agg[k]['names'].add(clean_name(nm)); break
        elif code.startswith(('1105','1106')):
            for pre in FND_PRE:
                if code.startswith(pre) and len(code) == len(pre)+6:
                    k = 'FND|'+code[-6:]
                    agg[k]['cost'] += c; agg[k]['mkt'] += m
                    agg[k]['names'].add(clean_name(nm)); break
        elif code.startswith('1109'):
            if code.startswith(PE_PRE) and len(code) > len(PE_PRE):
                k = 'PE|'+code[len(PE_PRE):]
                agg[k]['cost'] += c; agg[k]['mkt'] += m
                agg[k]['names'].add(clean_name(nm))
        elif code.startswith('3102'):
            mm = FUT_RE.match(code)
            if mm:
                if mm.group(1) == '99':
                    continue
                pnm = name_by_prefix.get(code[:6], '') or name_by_prefix.get(code[:8], '')
                k = 'FUT|' + direction(pnm) + '|' + clean_name(nm)
                agg[k]['cost'] += c; agg[k]['mkt'] += m
                agg[k]['names'].add(clean_name(nm))
    return agg

def full_of(short):
    for f in files:
        if f.endswith(short):
            return f

# 子基金逐标的持仓（市值口径）
sub_agg = {s: parse_invest_mkt(full_of(s)) for s in SUBKEY}

# 每只产品穿透
print(f"{'产品':<12}{'穿透后投向(元)':>15}{'前5集中度':>10}{'前10集中度':>11}  前5大持仓(标的名:占投向%)")
print('-'*130)
detail = {}
for f in files:
    short = f.split('-')[-1]
    agg = parse_invest_mkt(f)
    for k, v in list(agg.items()):
        if k.startswith('PE|'):
            sub = k.split('|')[1]
            sub_short = None
            for s, sk in SUBKEY.items():
                if sk == sub:
                    sub_short = s; break
            if sub_short is None:
                continue  # 五矿：保留原样
            w = v['mkt'] / NAV[sub_short]
            for sk2, sv in sub_agg[sub_short].items():
                agg[sk2]['mkt'] += sv['mkt'] * w
                agg[sk2]['cost'] += sv['cost'] * w
                agg[sk2]['names'] |= sv['names']
            del agg[k]
    total = sum(v['mkt'] for v in agg.values())
    items = sorted(agg.items(), key=lambda x: -x[1]['mkt'])
    top5 = items[:5]; top10 = items[:10]
    c5 = sum(v['mkt'] for _, v in top5) / total if total else 0
    c10 = sum(v['mkt'] for _, v in top10) / total if total else 0
    nm = FUND_NAMES[short]
    detail[short] = (nm, total, c5, c10, top5)
    top5_str = '、'.join(f"{max(v['names'], key=len) if v['names'] else k.split('|')[-1]}({v['mkt']/total*100:.1f}%)" for _, v in top5)
    print(f"{nm:<13}{total:>15,.0f}{c5*100:>9.2f}%{c10*100:>10.2f}%  {top5_str[:100]}")
print()
print('--- 前5大持仓明细（市值，元） ---')
rows_out = []
for short, (nm, total, c5, c10, top5) in detail.items():
    rows_out.append({
        '产品': nm, '穿透后投向(元)': round(total, 2),
        '前5大集中度%': round(c5*100, 2), '前10大集中度%': round(c10*100, 2),
        '前5大持仓': '、'.join(f"{max(v['names'], key=len) if v['names'] else k.split('|')[-1]}({v['mkt']/total*100:.1f}%)" for k, v in top5)})
pd.DataFrame(rows_out).to_csv('10只产品持仓集中度_20260630.csv', index=False, encoding='utf-8-sig')
print('\n已导出 10只产品持仓集中度_20260630.csv')
for short, (nm, total, c5, c10, top5) in detail.items():
    print(f"\n【{nm}】穿透后投向 {total:,.0f} 元 | 前5 {c5*100:.2f}% | 前10 {c10*100:.2f}%")
    for i, (k, v) in enumerate(top5, 1):
        name = max(v['names'], key=len) if v['names'] else k
        print(f"   {i}. {name:<36}{v['mkt']:>14,.0f}  {v['mkt']/total*100:6.2f}%")
