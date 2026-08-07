# -*- coding: utf-8 -*-
"""10只基金四类资产仓位：权益类/固收类/现金类/商品及衍生品类（亿元，4位小数）
私募投资按子基金底层穿透归类；衍生品用总名义(多头名义+|空头名义|)
"""
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
SUB_NAV = {'000011.xls': None, '000013.xls': None, '000017.xls': None,
           '000018.xls': None, '000019.xls': None}  # 运行时填净资产
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

def classify_fund(name):
    """基金/ETF 类型 -> 权益/固收/现金/商品"""
    if '货币' in name:
        return 'cash'
    if '债' in name:
        return 'bond'
    if any(k in name for k in ('黄金', '有色', '豆粕', '能源化工', '商品', '期货ETF')):
        return 'comm'
    return 'eq'

def parse_invest(path):
    """投资叶子 -> agg(key -> dict(cost,mkt,names,cat))；期货=名义(初始行市值)，期权=权利金市值"""
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
                if parts[2] == '02':
                    continue
                key = 'FUT|' + direction(pnm) + '|' + clean_name(nm); cat = '期货/期权'
            elif code.startswith('1102'):
                key = 'STK|' + token; cat = '股票'
            elif code.startswith('1103'):
                key = 'BND|' + token; cat = '债券/可转债'
            elif code.startswith(('1105','1106')):
                key = 'FND|' + token; cat = '公募基金'
            else:
                key = 'PE|' + token; cat = '私募'
            agg[key]['cost'] += c; agg[key]['mkt'] += m
            agg[key]['names'].add(clean_name(nm)); agg[key]['cat'] = cat
        elif code.startswith('1102'):
            for pre in STK_PRE:
                if code.startswith(pre) and len(code) == len(pre)+6:
                    token = code[len(pre):].lstrip('H')
                    agg['STK|'+token]['cost'] += c; agg['STK|'+token]['mkt'] += m
                    agg['STK|'+token]['names'].add(clean_name(nm)); agg['STK|'+token]['cat'] = '股票'
                    break
        elif code.startswith('1103'):
            for pre in BND_PRE:
                if code.startswith(pre) and len(code) == len(pre)+6:
                    k = 'BND|'+code[-6:]
                    agg[k]['cost'] += c; agg[k]['mkt'] += m
                    agg[k]['names'].add(clean_name(nm)); agg[k]['cat'] = '债券/可转债'
                    break
        elif code.startswith(('1105','1106')):
            for pre in FND_PRE:
                if code.startswith(pre) and len(code) == len(pre)+6:
                    k = 'FND|'+code[-6:]
                    agg[k]['cost'] += c; agg[k]['mkt'] += m
                    agg[k]['names'].add(clean_name(nm)); agg[k]['cat'] = '公募基金'
                    break
        elif code.startswith('1109'):
            if code.startswith(PE_PRE) and len(code) > len(PE_PRE):
                k = 'PE|'+code[len(PE_PRE):]
                agg[k]['cost'] += c; agg[k]['mkt'] += m
                agg[k]['names'].add(clean_name(nm)); agg[k]['cat'] = '私募'
        elif code.startswith('3102'):
            mm = FUT_RE.match(code)
            if mm:
                if mm.group(1) == '02':
                    continue
                pnm = name_by_prefix.get(code[:6], '') or name_by_prefix.get(code[:8], '')
                k = 'FUT|' + direction(pnm) + '|' + clean_name(nm)
                agg[k]['cost'] += c; agg[k]['mkt'] += m
                agg[k]['names'].add(clean_name(nm)); agg[k]['cat'] = '期货/期权'
    return agg

def calc_nav(path):
    """净资产 = 资产类市值 - 负债类市值（3102 用市值=浮动盈亏口径）"""
    df = pd.ExcelFile(path).parse('Sheet1', header=None)
    hdr = None
    for i in range(min(8, len(df))):
        if str(df.iloc[i,0]).strip() == '科目代码':
            hdr = i; break
    ncol = df.shape[1]
    mkt_i = 11 if ncol==16 else (9 if ncol==14 else 7)
    asset = debt = 0.0
    seen = set()
    for i in range(hdr+1, len(df)):
        code = str(df.iloc[i,0]).strip()
        if not code or not code[0].isdigit():
            continue
        main = code.split('.')[0]
        if main in seen or not (3 <= len(main) <= 4):
            continue
        seen.add(main)
        m = df.iloc[i, mkt_i]
        if pd.isna(m):
            continue
        if main[0] in ('1', '3'):
            asset += float(m)
        elif main[0] == '2':
            debt += float(m)
    return asset - debt

def classify_fund_positions(path):
    """返回 (eq, bond, cash, comm, pe_hold) 直接口径（未穿透），单位元"""
    agg = parse_invest(path)
    eq = bond = comm = 0.0
    cash_fund = 0.0
    pe_hold = defaultdict(float)   # subkey -> 持有市值
    for k, v in agg.items():
        cat, rest = k.split('|', 1)
        if cat == 'STK':
            eq += v['mkt']
        elif cat == 'BND':
            bond += v['mkt']
        elif cat == 'FND':
            t = classify_fund(max(v['names'], key=len))
            if t == 'eq': eq += v['mkt']
            elif t == 'bond': bond += v['mkt']
            elif t == 'comm': comm += v['mkt']   # 商品ETF按市值
            else: cash_fund += v['mkt']
        elif cat == 'PE':
            pe_hold[rest] += v['mkt']
        # FUT：市值口径下从一级科目 3102 取浮动盈亏（下面处理）
    # 一级科目：现金类 & 买入返售
    df = pd.ExcelFile(path).parse('Sheet1', header=None)
    hdr = None
    for i in range(min(8, len(df))):
        if str(df.iloc[i,0]).strip() == '科目代码':
            hdr = i; break
    ncol = df.shape[1]
    mkt_i = 11 if ncol==16 else (9 if ncol==14 else 7)
    cash = cash_fund
    seen = set()
    for i in range(hdr+1, len(df)):
        code = str(df.iloc[i,0]).strip()
        if not code or not code[0].isdigit():
            continue
        main = code.split('.')[0]
        if main in seen:
            continue
        seen.add(main)
        m = df.iloc[i, mkt_i]
        if pd.isna(m):
            continue
        m = float(m)
        if main == '1002' or main == '1021' or main == '1031' or main == '3003':
            cash += m
        elif main == '1202':
            bond += m   # 买入返售 -> 固收类
        elif main == '3102':
            comm += m   # 衍生品市值=浮动盈亏（可正可负）
    return eq, bond, cash, comm, pe_hold

# ---- 主流程 ----
navs = {}
pos = {}
for f in files:
    short = f.split('-')[-1]
    navs[short] = calc_nav(f)
    pos[short] = classify_fund_positions(f)
for short in SUB_NAV:
    SUB_NAV[short] = navs[short]

# 子基金四类构成（直接口径）
sub_pos = {s: pos[s] for s in SUB_NAV}
unpenetrated = defaultdict(float)  # 五矿等无法穿透

results = {}
for f in files:
    short = f.split('-')[-1]
    eq, bond, cash, comm, pe_hold = pos[short]
    for subkey, held in pe_hold.items():
        # 找该子基金对应的文件
        sub_short = None
        for s, k in SUBKEY.items():
            if k == subkey:
                sub_short = s; break
        if sub_short is None:
            unpenetrated[subkey] += held   # 五矿资管（无底层数据）
            continue
        w = held / SUB_NAV[sub_short]
        se, sb, sc, scomm, _ = sub_pos[sub_short]
        eq += se * w; bond += sb * w; cash += sc * w; comm += scomm * w
    results[short] = (eq, bond, cash, comm)

# ---- 输出表格 ----
print(f"{'基金':<14}{'权益类':>12}{'固收类':>12}{'现金类':>12}{'商品及衍生品':>14}{'合计':>12}{'净资产':>12}{'差异':>9}")
print('（单位：亿元）')
t = [0.0]*4
for f in files:
    short = f.split('-')[-1]
    eq, bond, cash, comm = results[short]
    nav = navs[short]
    tot = eq + bond + cash + comm
    diff = tot - nav
    for i, x in enumerate((eq, bond, cash, comm)):
        t[i] += x
    print(f"{FUND_NAMES[short]:<16}{eq/1e8:>12.4f}{bond/1e8:>12.4f}{cash/1e8:>12.4f}{comm/1e8:>14.4f}{tot/1e8:>12.4f}{nav/1e8:>12.4f}{diff/1e8:>9.4f}")
print('-'*95)
print(f"{'合计':<16}{t[0]/1e8:>12.4f}{t[1]/1e8:>12.4f}{t[2]/1e8:>12.4f}{t[3]/1e8:>14.4f}{sum(t)/1e8:>12.4f}{sum(navs.values())/1e8:>12.4f}")
if unpenetrated:
    for k, v in unpenetrated.items():
        print(f"注：{k}（五矿期货宏观量化股指转债一号）无底层估值数据，未穿透归类，市值 {v/1e8:.4f} 亿")
print('口径：商品及衍生品类 = 商品ETF市值 + 期货期权市值(浮动盈亏，可正可负)；其余类同前')
print('注：SAEH44（五矿期货宏观量化股指转债一号）无底层估值数据，未穿透归类，市值 0.0129 亿')
PY_END
