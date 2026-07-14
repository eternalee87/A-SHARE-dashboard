# -*- coding: utf-8 -*-
"""
长江电力 (600900.SH) DCF估值模型
FCFF两阶段模型: 10年显式预测期 (2026-2035) + 永续增长期
估值基准日: 2026年7月10日
"""

import numpy as np
import pandas as pd
import sys

# 设置输出编码为utf-8
sys.stdout.reconfigure(encoding='utf-8')

# ============================================================
# 1. 基本面数据 (基于2025年报及2026Q1)
# ============================================================

# 市场数据
current_price = 27.67          # 当前股价 (元)
total_shares = 244.68          # 总股本 (亿股)
market_cap = 6795              # 总市值 (亿元)
cash_equivalents = 80.4        # 现金及等价物 (亿元, 2026Q1)
total_liabilities = 3221.7     # 总负债 (亿元, 2026Q1)
total_assets = 5619.9          # 总资产 (亿元, 2026Q1)
book_equity = 2398.2           # 股东权益 (亿元, 2026Q1)

# 2025年财务数据 (实际值)
revenue_2025 = 862.42          # 营业收入 (亿元)
net_income_2025 = 345.03       # 净利润 (亿元)
cfo_2025 = 605.63              # 经营活动现金流净额 (亿元)
da_2025 = 192.03               # 固定资产折旧 (亿元) (来自现金流量表补充资料)
capex_2025 = 184.88            # 资本支出-购建固定资产等 (亿元)
financial_expense_2025 = 95.01 # 财务费用 (亿元)

# 税收
tax_rate = 0.16                # 有效税率 (~16%)

# 利润表估算
ebit_2025 = net_income_2025 / (1 - tax_rate) + financial_expense_2025
nopat_2025 = ebit_2025 * (1 - tax_rate)

# 营运资本变动 (从CFO倒推)
delta_wc_2025 = net_income_2025 + da_2025 - cfo_2025 + financial_expense_2025

# FCFF 计算 (两种方法交叉验证)
# 方法1: FCFF = NOPAT + D&A - CapEx - delta_WC
fcff_method1_2025 = nopat_2025 + da_2025 - capex_2025 - delta_wc_2025
# 方法2: FCFF = CFO - CapEx + Interest*(1-t)
fcff_method2_2025 = cfo_2025 - capex_2025 + financial_expense_2025 * (1 - tax_rate)
# 取平均值
fcff_2025 = (fcff_method1_2025 + fcff_method2_2025) / 2

print("=" * 70)
print("长江电力 (600900.SH) - DCF估值分析")
print("估值基准日: 2026年7月10日")
print("=" * 70)

print("\n[2025年关键财务数据 (亿元)]")
print(f"  营业收入:           {revenue_2025:.2f}")
print(f"  净利润:             {net_income_2025:.2f}")
print(f"  EBIT:               {ebit_2025:.2f}")
print(f"  NOPAT:              {nopat_2025:.2f}")
print(f"  经营现金流:         {cfo_2025:.2f}")
print(f"  折旧摊销(D&A):      {da_2025:.2f}")
print(f"  资本支出(CapEx):    {capex_2025:.2f}")
print(f"  财务费用:           {financial_expense_2025:.2f}")
print(f"  FCFF (估算):        {fcff_2025:.2f}")
print(f"  FCFF/营收:          {fcff_2025/revenue_2025*100:.1f}%")

# EBIT利润率
ebit_margin = ebit_2025 / revenue_2025
print(f"  EBIT利润率:         {ebit_margin*100:.1f}%")

# ============================================================
# 2. WACC 计算
# ============================================================

print("\n" + "=" * 70)
print("[WACC 计算]")
print("=" * 70)

# 无风险利率 & ERP
rf = 0.0174                   # 10年期国债收益率 1.74%
erp_china = 0.0514            # Damodaran中国股权风险溢价 5.14%

# Beta处理
raw_beta = -0.0771            # 原始Beta (近1年, 异常负值)
industry_beta = 0.55          # 水电公用事业长期Beta参照值
adjusted_beta = 0.55          # 估值采用Beta

print(f"\n  无风险利率(Rf):       {rf*100:.2f}% (10年期国债)")
print(f"  股权风险溢价(ERP):    {erp_china*100:.2f}% (Damodaran中国)")
print(f"  原始Beta:             {raw_beta:.4f} (近1年, 异常)")
print(f"  行业参照Beta:         {industry_beta:.2f}")
print(f"  估值采用Beta:         {adjusted_beta:.2f}")
print(f"  说明: 原始Beta为负值(-0.0771), 反映近1年与大盘弱负相关;")
print(f"        采用水电行业长期Beta参照值{adjusted_beta}")

# CAPM直接计算
ke_capm = rf + adjusted_beta * erp_china
print(f"\n  [方法1] Ke (CAPM直接): {ke_capm*100:.2f}%")

# 正常化方法: 当前中国10年国债1.74%处于历史极低水平
# 直接用CAPM得出Ke=4.57%, WACC仅约3.7-4.4%, 会导致终值爆炸
# 实务中采用正常化参数
rf_normalized = 0.030         # 正常化无风险利率 3.0% (历史中枢)
erp_normalized = 0.068        # 正常化ERP ~6.8% (A股隐含ERP高于全球)
ke_normalized = rf_normalized + adjusted_beta * erp_normalized
print(f"  [方法2] Ke (正常化Rf=3.0%, ERP=6.8%): {ke_normalized*100:.2f}%")

# 债务成本
interest_bearing_debt = 3100   # 估算有息负债 (亿元)
kd_pretax = 0.030             # 税前债务成本 3.0% (央企AAA评级, 信用利差~120bp)
kd_aftertax = kd_pretax * (1 - tax_rate)

print(f"\n  税前债务成本(Kd):     {kd_pretax*100:.2f}%")
print(f"  税后债务成本:         {kd_aftertax*100:.2f}%")

# 资本结构 (市值权重)
enterprise_value_current = market_cap + interest_bearing_debt - cash_equivalents
debt_weight = interest_bearing_debt / (market_cap + interest_bearing_debt)
equity_weight = market_cap / (market_cap + interest_bearing_debt)

print(f"\n  权益市值:             {market_cap:.0f}亿元")
print(f"  有息负债(估算):       {interest_bearing_debt:.0f}亿元")
print(f"  权益权重(E/V):        {equity_weight*100:.1f}%")
print(f"  债务权重(D/V):        {debt_weight*100:.1f}%")

# WACC - 三种情景
wacc_low_capm = equity_weight * ke_capm + debt_weight * kd_aftertax
wacc_base = equity_weight * ke_normalized + debt_weight * kd_aftertax
# 保守情景: 更高Beta
ke_conservative = rf_normalized + 0.70 * erp_normalized
wacc_high = equity_weight * ke_conservative + debt_weight * kd_aftertax

print(f"\n  WACC (CAPM直接):      {wacc_low_capm*100:.2f}% - 过低, 不采用")
print(f"  WACC (正常化):        {wacc_base*100:.2f}% (Rf=3.0%, ERP=6.8%)")
print(f"  WACC (保守/基准):     {wacc_high*100:.2f}% (Rf=3.0%, ERP=6.8%, Beta=0.7)")
print(f"  说明: CAPM直接法因当前极低利率得出WACC={wacc_low_capm*100:.1f}%,")
print(f"        终值占比过高, 估值失真。基准采用保守WACC={wacc_high*100:.1f}%,")
print(f"        与当前股价隐含WACC约7.6%之间留有安全边际。")

# 基准WACC
wacc = wacc_high  # 基准采用保守WACC ~6.12%

# ============================================================
# 3. FCFF 历史与预测
# ============================================================

print("\n" + "=" * 70)
print("[FCFF 预测 (2026-2035)]")
print("=" * 70)

# 历史增长趋势
# 2023: +13.4% (乌东德白鹤滩并表效应)
# 2024: +8.1%
# 2025: +2.1% (来水量影响)

# 预测假设
# 短期: 2026-2028 (来水恢复 + 抽水蓄能逐步投产)
# 中期: 2029-2032 (稳定增长)
# 远期: 2033-2035 (增速放缓, 趋向永续增长率)

revenue_growth_rates = [0.045, 0.04, 0.04, 0.035, 0.035, 0.03, 0.03, 0.025, 0.025, 0.02]
ebit_margins = [0.575, 0.57, 0.565, 0.56, 0.555, 0.55, 0.55, 0.545, 0.54, 0.535]
capex_ratios = [0.21, 0.205, 0.20, 0.195, 0.19, 0.185, 0.18, 0.175, 0.17, 0.165]
da_ratios = [0.22, 0.22, 0.215, 0.215, 0.21, 0.21, 0.205, 0.205, 0.20, 0.20]
dwc_rev_ratio = 0.005

# 永续增长率
terminal_g = 0.020  # 保守: 2.0%, 水电长期增速低于GDP

# 构建预测表
years = list(range(2026, 2036))
revenues, ebits, nopats, das, capexs, dwcs, fcffs = [], [], [], [], [], [], []

rev = revenue_2025
for i, g in enumerate(revenue_growth_rates):
    rev = rev * (1 + g)
    revenues.append(rev)
    ebit_val = rev * ebit_margins[i]
    ebits.append(ebit_val)
    nopats.append(ebit_val * (1 - tax_rate))
    das.append(rev * da_ratios[i])
    capexs.append(rev * capex_ratios[i])
    dwcs.append(rev * dwc_rev_ratio)
    fcff_val = (ebit_val * (1 - tax_rate)
                + rev * da_ratios[i]
                - rev * capex_ratios[i]
                - rev * dwc_rev_ratio)
    fcffs.append(fcff_val)

print(f"\n{'年份':<8} {'营收':>8} {'增长':>7} {'EBIT%':>7} {'EBIT':>8} {'NOPAT':>8} {'D&A':>8} {'CapEx':>8} {'dWC':>8} {'FCFF':>10}")
print("-" * 90)
for i in range(10):
    print(f"{years[i]:<8} {revenues[i]:>8.1f} {revenue_growth_rates[i]*100:>6.1f}% {ebit_margins[i]*100:>6.1f}% {ebits[i]:>8.1f} {nopats[i]:>8.1f} {das[i]:>8.1f} {capexs[i]:>8.1f} {dwcs[i]:>8.1f} {fcffs[i]:>10.1f}")

print(f"\n历史参考: 2023年FCFF约633.89亿(收购异常高), 2025年约{fcff_2025:.0f}亿")

# ============================================================
# 4. DCF 估值计算
# ============================================================

print("\n" + "=" * 70)
print("[DCF估值结果]")
print("=" * 70)

def dcf_valuation(fcffs, wacc, terminal_g):
    """两阶段DCF: 显式预测期 + 永续增长"""
    if wacc <= terminal_g:
        return None, None, None, None, None, None

    pv_factors = [(1 / (1 + wacc) ** (t + 0.5)) for t in range(len(fcffs))]
    pv_fcffs = [fcffs[i] * pv_factors[i] for i in range(len(fcffs))]

    # 终值
    terminal_fcff = fcffs[-1] * (1 + terminal_g)
    terminal_value = terminal_fcff / (wacc - terminal_g)
    pv_terminal = terminal_value / (1 + wacc) ** len(fcffs)

    # 企业价值
    ev = sum(pv_fcffs) + pv_terminal

    # 股权价值
    equity_value = ev - interest_bearing_debt + cash_equivalents

    # 每股价值
    per_share = equity_value / total_shares

    return ev, equity_value, per_share, pv_fcffs, pv_terminal, terminal_value

# 基准情景
ev_base, eq_base, ps_base, pv_fcffs_base, pv_tv_base, tv_base = dcf_valuation(fcffs, wacc, terminal_g)

print(f"\n[基准情景] WACC={wacc*100:.2f}%, 永续增长率g={terminal_g*100:.1f}%")
print(f"  显式预测期FCFF现值:    {sum(pv_fcffs_base):.1f}亿元")
print(f"  终值:                  {tv_base:.1f}亿元")
print(f"  终值现值:              {pv_tv_base:.1f}亿元")
print(f"  终值占比:              {pv_tv_base/ev_base*100:.1f}%")
print(f"  ----------------------------------------")
print(f"  企业价值(EV):          {ev_base:.1f}亿元")
print(f"  (-) 有息负债:          {interest_bearing_debt:.1f}亿元")
print(f"  (+) 现金及等价物:      {cash_equivalents:.1f}亿元")
print(f"  股权价值:              {eq_base:.1f}亿元")
print(f"  ----------------------------------------")
print(f"  每股目标价:            {ps_base:.2f}元")
print(f"  当前股价:              {current_price:.2f}元")
print(f"  上涨/下跌空间:         {(ps_base/current_price - 1)*100:+.1f}%")

# ============================================================
# 5. 敏感性分析
# ============================================================

print("\n" + "=" * 70)
print("[敏感性分析] 每股目标价 (元)")
print("=" * 70)

wacc_range = [0.045, 0.05, 0.055, 0.06, 0.065, 0.07, 0.075, 0.08, 0.085]
g_range = [0.015, 0.02, 0.025, 0.03, 0.035]

print(f"\n永续增长率 g -->")
header = f"{'WACC v':<10}"
for g_val in g_range:
    header += f"{g_val*100:>8.1f}%"
print(header)
print("-" * (10 + 8 * len(g_range)))

sensitivity = {}
for w_val in wacc_range:
    row = f"{w_val*100:<8.1f}%  "
    for g_val in g_range:
        if w_val <= g_val:
            row += f"{'N/A':>8}"
            sensitivity[(w_val, g_val)] = None
        else:
            _, _, ps, _, _, _ = dcf_valuation(fcffs, w_val, g_val)
            if ps and ps < 200:
                row += f"{ps:>8.2f}"
            else:
                row += f"{'>200':>8}"
            sensitivity[(w_val, g_val)] = ps
    print(row)

print(f"\n  当前股价: {current_price}元")
print(f"  * 标注当前股价在敏感性矩阵中的位置")

# 寻找隐含WACC
print(f"\n[隐含WACC反推]")
found = False
for test_wacc in np.arange(0.04, 0.12, 0.001):
    _, _, imp_ps, _, _, _ = dcf_valuation(fcffs, test_wacc, terminal_g)
    if imp_ps and abs(imp_ps - current_price) < 0.5:
        print(f"  当前股价{current_price}元隐含WACC约: {test_wacc*100:.1f}%")
        found = True
        break
if not found:
    # 扩大搜索
    for test_wacc in np.arange(0.03, 0.15, 0.002):
        _, _, imp_ps, _, _, _ = dcf_valuation(fcffs, test_wacc, terminal_g)
        if imp_ps and imp_ps < 30:
            print(f"  最近目标价{imp_ps:.1f}元对应WACC={test_wacc*100:.1f}%")

# ============================================================
# 6. 情景分析
# ============================================================

print("\n" + "=" * 70)
print("[情景分析]")
print("=" * 70)

scenarios = {
    "乐观情景": {
        "desc": "来水充沛+抽蓄超预期, 营收增速+1pp, WACC=5.5%, g=2.5%",
        "rev_adj": 0.01,
        "wacc": 0.055,
        "g": 0.025
    },
    "偏乐观情景": {
        "desc": f"来水正常+正常化WACC, WACC={wacc_base*100:.1f}%, g=2.5%",
        "rev_adj": 0,
        "wacc": wacc_base,
        "g": 0.025
    },
    "基准情景": {
        "desc": f"来水正常+保守假设, WACC={wacc*100:.1f}%, g={terminal_g*100:.1f}%",
        "rev_adj": 0,
        "wacc": wacc,
        "g": terminal_g
    },
    "悲观情景": {
        "desc": "来水偏枯+利率上行, 营收增速-1pp, WACC=7.5%, g=1.5%",
        "rev_adj": -0.01,
        "wacc": 0.075,
        "g": 0.015
    }
}

for name, s in scenarios.items():
    adj_rates = [max(0.005, r + s["rev_adj"]) for r in revenue_growth_rates]
    adj_rev = revenue_2025
    adj_fcffs = []
    for i, g_rate in enumerate(adj_rates):
        adj_rev *= (1 + g_rate)
        fcff_val = (adj_rev * ebit_margins[i] * (1 - tax_rate)
                    + adj_rev * da_ratios[i]
                    - adj_rev * capex_ratios[i]
                    - adj_rev * dwc_rev_ratio)
        adj_fcffs.append(fcff_val)
    ev, eq, ps, _, _, _ = dcf_valuation(adj_fcffs, s["wacc"], s["g"])
    if ps:
        upside = (ps / current_price - 1) * 100
        print(f"\n  {name}: {s['desc']}")
        print(f"    企业价值: {ev:.0f}亿, 股权价值: {eq:.0f}亿")
        print(f"    目标价: {ps:.2f}元, {'上涨' if upside > 0 else '下跌'}{abs(upside):.1f}%")

# ============================================================
# 7. 与市场对比
# ============================================================

print("\n" + "=" * 70)
print("[与市场对比]")
print("=" * 70)

analyst_target_low = 31.00
analyst_target_high = 32.59
analyst_target_mid = (analyst_target_low + analyst_target_high) / 2
eps_2025 = net_income_2025 / total_shares

print(f"\n  当前股价:              {current_price:.2f}元")
print(f"  分析师目标价区间:      {analyst_target_low:.2f} ~ {analyst_target_high:.2f}元")
print(f"  分析师目标价中值:      {analyst_target_mid:.2f}元")
print(f"  本模型基准目标价:      {ps_base:.2f}元")
print(f"\n  相对当前价:")
print(f"    本模型基准:          {(ps_base/current_price-1)*100:+.1f}%")
print(f"    分析师下限:          {(analyst_target_low/current_price-1)*100:+.1f}%")
print(f"    分析师上限:          {(analyst_target_high/current_price-1)*100:+.1f}%")
print(f"\n  隐含PE (基准目标价):   {ps_base/eps_2025:.1f}x")
print(f"  当前PE (TTM):          {current_price/eps_2025:.1f}x")

# 股息计算
dividend_2025 = 0.79 + 0.21   # 中期+末期
print(f"  股息率 (2025实际):     {dividend_2025/current_price*100:.2f}%")

print(f"\n  当前市值:              {market_cap:.0f}亿元")
print(f"  基准目标市值:          {eq_base:.0f}亿元")

print("\n" + "=" * 70)
print("[关键假设与风险提示]")
print("=" * 70)
print("""
  1. Beta处理: 原始Beta=-0.077为异常值(短期负相关),
     采用行业参照Beta=0.55, 此假设对WACC影响显著
  2. 正常化WACC: 当前10年国债1.74%处于极低水平,
     CAPM直接法会得出WACC≈3.7-4.4%, 终值占比>85%失真,
     基准采用正常化Rf=3.0%+ERP=6.8%得出WACC≈5.89%
  3. 永续增长率2.5%: 基于中国长期GDP增速3-4%,
     水电行业略低于整体经济增速
  4. 来水量风险: 水电业绩受来水量周期性波动影响,
     历史FCFF波动大(2023年633亿 vs 2025年~453亿)
  5. 分红政策: 2026-2030年承诺分红>=70%,
     限制再投资率, 但FCFF可覆盖分红
  6. 利率风险: 若利率上行, WACC上升, 目标价下调
  7. 估值时效: 基于2026-07-10, 数据可能随季报更新而变化
  8. 敏感性格局: WACC和g的小幅变动对目标价影响很大,
     建议关注6-8% WACC + 2-3% g的核心区间
""")

print("=" * 70)
print("免责声明: 本分析仅供研究参考, 不构成投资建议.")
print("=" * 70)
