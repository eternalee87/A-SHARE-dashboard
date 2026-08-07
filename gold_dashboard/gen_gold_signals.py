"""
黄金交易机会看板 — 信号引擎 v2
基于中金李昭博士研报框架 + 趋势跟踪量价分析

定性信号：基于研报逻辑（6个维度，不变）
定量信号：趋势跟踪框架（5个维度，均值回归→趋势跟踪）
  - MA20趋势线：站上做多，之下不做多
  - MA50/MA200金叉死叉：中期趋势方向
  - 趋势强度(ADX代理)：强趋势顺势，弱趋势观望
  - 最大回撤：从1年高点回撤幅度
  - 相关性崩坏：传统框架失效检测
离场方案：分层信号（MA20跌破→死叉确认→回撤加深→定性反转）
"""

import json
import os
from pathlib import Path
from datetime import datetime, timedelta

OUTPUT_DIR = Path(__file__).parent / "data"
DATA_FILE = OUTPUT_DIR / "gold_data.json"
SIGNALS_FILE = OUTPUT_DIR / "gold_signals.json"


def load_data():
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def _ma(values, period):
    """移动均线"""
    if len(values) < period:
        return None
    return sum(values[-period:]) / period


def _rolling_max(values, period):
    """滚动最高"""
    if len(values) < period:
        return max(values) if values else None
    return max(values[-period:])


def _rolling_min(values, period):
    if len(values) < period:
        return min(values) if values else None
    return min(values[-period:])


def calc_qualitative_signals(daily, history, fred):
    """
    定性信号：基于李昭研报框架的6个维度（保持不变）
    """
    signals = []

    # ========== 维度1: 美联储货币政策 (准确率80%) ==========
    fed_rate = daily.get("fed_rate", 4.0)
    if fed_rate and fed_rate < 4.0:
        fed_signal = +1
        fed_detail = f"联邦基金利率 {fed_rate}%，处于降息周期中，宽松货币政策利多黄金"
    elif fed_rate and fed_rate < 5.0:
        fed_signal = +1
        fed_detail = f"联邦基金利率 {fed_rate}%，从高点回落，仍偏宽松"
    else:
        fed_signal = 0
        fed_detail = f"联邦基金利率 {fed_rate}%"
    signals.append({
        "dimension": "美联储货币政策", "signal": fed_signal,
        "direction": "利多" if fed_signal > 0 else ("利空" if fed_signal < 0 else "中性"),
        "detail": fed_detail, "accuracy": 0.80, "weight": 0.25,
    })

    # ========== 维度2: 美国经济象限 (准确率80%) ==========
    tips_val = daily.get("tips_trend", {})
    dxy_val = daily.get("dxy_stats", {})
    tips_direction = tips_val.get("direction", "flat")
    dxy_current = dxy_val.get("current", 100)
    dxy_ma200 = dxy_val.get("ma200", 103)

    if tips_direction == "up" and dxy_current and dxy_ma200 and dxy_current < dxy_ma200:
        regime_signal = +1
        regime_detail = "滞胀象限（通胀上行+增长承压），黄金最友好环境"
    elif tips_direction == "down" and dxy_current and dxy_ma200 and dxy_current < dxy_ma200:
        regime_signal = 0
        regime_detail = "衰退象限（通胀下行+增长承压），黄金偏利好但弹性减弱"
    elif tips_direction == "up" and dxy_current and dxy_ma200 and dxy_current > dxy_ma200:
        regime_signal = 0
        regime_detail = "过热象限（通胀上行+增长走强），黄金中性"
    else:
        regime_signal = -1
        regime_detail = "复苏象限（通胀下行+增长走强），黄金面临压力"
    signals.append({
        "dimension": "美国经济象限", "signal": regime_signal,
        "direction": "利多" if regime_signal > 0 else ("利空" if regime_signal < 0 else "中性"),
        "detail": regime_detail, "accuracy": 0.80, "weight": 0.25,
    })

    # ========== 维度3: 美元趋势 ==========
    dxy_signal = 0
    if dxy_current and dxy_ma200:
        dxy_ratio = dxy_current / dxy_ma200
        if dxy_ratio < 0.97:
            dxy_signal = +1
            dxy_detail = f"DXY {dxy_current}，显著低于MA200({dxy_ma200})，美元贬值趋势利多黄金"
        elif dxy_ratio < 1.0:
            dxy_signal = +1
            dxy_detail = f"DXY {dxy_current}，低于MA200({dxy_ma200})，美元偏弱"
        elif dxy_ratio < 1.03:
            dxy_signal = 0
            dxy_detail = f"DXY {dxy_current}，接近MA200({dxy_ma200})，美元中性"
        else:
            dxy_signal = -1
            dxy_detail = f"DXY {dxy_current}，高于MA200({dxy_ma200})，美元走强利空黄金"
    else:
        dxy_detail = f"DXY {dxy_current}"
    signals.append({
        "dimension": "美元趋势", "signal": dxy_signal,
        "direction": "利多" if dxy_signal > 0 else ("利空" if dxy_signal < 0 else "中性"),
        "detail": dxy_detail, "accuracy": 0.65, "weight": 0.15,
    })

    # ========== 维度4: 实际利率趋势 ==========
    tips_current = tips_val.get("current", 2.0)
    tips_ma3m = tips_val.get("ma_3m", 2.0)
    tips_signal = 0
    if tips_current < tips_ma3m - 0.1:
        tips_signal = +1
        tips_detail = f"TIPS {tips_current}%，低于3月均线({tips_ma3m}%)，实际利率下行利多黄金"
    elif tips_current > tips_ma3m + 0.1:
        tips_signal = -1
        tips_detail = f"TIPS {tips_current}%，高于3月均线({tips_ma3m}%)，实际利率上行利空黄金"
    else:
        tips_detail = f"TIPS {tips_current}%，接近3月均线({tips_ma3m}%)，方向不明"
    signals.append({
        "dimension": "实际利率趋势", "signal": tips_signal,
        "direction": "利多" if tips_signal > 0 else ("利空" if tips_signal < 0 else "中性"),
        "detail": tips_detail, "accuracy": 0.60, "weight": 0.15,
    })

    # ========== 维度5: 美国财政赤字 (准确率40%) ==========
    signals.append({
        "dimension": "美国财政赤字", "signal": +1, "direction": "利多",
        "detail": "美国财政赤字率约6%，远高于疫情前~3%中枢，债务扩张支撑黄金长期逻辑",
        "accuracy": 0.40, "weight": 0.10,
    })

    # ========== 维度6: 央行购金 (准确率40%) ==========
    signals.append({
        "dimension": "央行购金", "signal": +1, "direction": "利多",
        "detail": "全球央行持续净购金（年均>1000吨），结构性去美元化支撑黄金",
        "accuracy": 0.40, "weight": 0.10,
    })

    total_qual = sum(s["signal"] * s["weight"] for s in signals)
    return {
        "signals": signals,
        "total_score": round(total_qual, 2),
        "max_score": sum(abs(s["weight"]) for s in signals),
        "normalized": round(total_qual / sum(abs(s["weight"]) for s in signals), 2),
        "weighted_accuracy": round(sum(s["accuracy"] * s["weight"] for s in signals), 2),
        "direction": "看多" if total_qual > 0.2 else ("看空" if total_qual < -0.2 else "中性"),
        "intensity": abs(round(total_qual / sum(abs(s["weight"]) for s in signals), 2)),
    }


def calc_quantitative_signals(daily, history):
    """
    定量信号 v2：趋势跟踪框架（不再是均值回归）
    
    维度设计原则：
    - 不判断"贵不贵"，判断"趋势是否还在"
    - 每维度独立给出 +1(趋势向上/利多), 0(中性/震荡), -1(趋势向下/利空)
    """
    signals = []

    gold_prices = [r["close"] for r in history.get("XAU", []) if r.get("close")]
    gold_dates = [r["date"] for r in history.get("XAU", []) if r.get("close")]
    current_price = gold_prices[-1] if gold_prices else 4000
    n = len(gold_prices)

    # ========== 定量1: MA20趋势线（用户指定） ==========
    # 逻辑：站上MA20=做多，之下=不做多
    # 这是短期趋势过滤器，权重最高
    if n >= 20:
        ma20 = _ma(gold_prices, 20)
        ratio_20 = current_price / ma20

        if ratio_20 > 1.02:
            ma20_signal = +1
            ma20_detail = f"金价${current_price:,.0f} 站上MA20(${ma20:,.0f})，比率{ratio_20:.3f}(>1.02)，短期趋势向上，可以持仓/做多"
        elif ratio_20 > 1.00:
            ma20_signal = +0.5
            ma20_detail = f"金价${current_price:,.0f} 在MA20(${ma20:,.0f})附近，比率{ratio_20:.3f}，勉强站稳，谨慎持有"
        elif ratio_20 > 0.98:
            ma20_signal = -0.5
            ma20_detail = f"金价${current_price:,.0f} 在MA20(${ma20:,.0f})下方但接近，比率{ratio_20:.3f}，不宜新建多仓"
        else:
            ma20_signal = -1
            ma20_detail = f"金价${current_price:,.0f} 跌破MA20(${ma20:,.0f})，比率{ratio_20:.3f}(<0.98)，短期趋势向下，不做多"
    else:
        ma20_signal = 0
        ma20_detail = "数据不足20日"

    signals.append({
        "dimension": "MA20趋势线",
        "signal": ma20_signal,
        "direction": "看多" if ma20_signal > 0 else ("看空" if ma20_signal < 0 else "中性"),
        "detail": ma20_detail,
        "weight": 0.30,  # 最高权重：核心短期信号
    })

    # ========== 定量2: MA50/MA200金叉死叉 ==========
    # 逻辑：金叉(MA50>MA200)=中期趋势向上，死叉=中期趋势向下
    if n >= 200:
        ma50 = _ma(gold_prices, 50)
        ma200 = _ma(gold_prices, 200)

        # 当前金叉/死叉状态
        is_golden = ma50 > ma200

        # 过去20日的MA50-MA200差距变化（判断交叉方向）
        ma50_20d = _ma(gold_prices[:-20], 50) if n >= 70 else ma50
        ma200_20d = _ma(gold_prices[:-20], 200) if n >= 220 else ma200
        if ma50_20d and ma200_20d:
            gap_now = ma50 - ma200
            gap_20d = ma50_20d - ma200_20d
            gap_widening = gap_now > gap_20d  # 差距在扩大
        else:
            gap_widening = False

        gap_pct = (ma50 / ma200 - 1) * 100

        if is_golden and gap_widening:
            xover_signal = +1
            xover_detail = f"金叉(MA50 ${ma50:,.0f} > MA200 ${ma200:,.0f})，差距扩大(+{gap_pct:.1f}%)，中期趋势确认向上"
        elif is_golden and not gap_widening:
            xover_signal = +0.5
            xover_detail = f"金叉但差距收窄(MA50 ${ma50:,.0f} > MA200 ${ma200:,.0f}, +{gap_pct:.1f}%)，趋势可能减弱，保持警惕"
        elif not is_golden and gap_widening:  # 死叉扩大
            xover_signal = -1
            xover_detail = f"死叉(MA50 ${ma50:,.0f} < MA200 ${ma200:,.0f})，差距扩大({gap_pct:.1f}%)，中期趋势向下，不应做多"
        else:  # 死叉收窄
            xover_signal = -0.5
            xover_detail = f"死叉但差距收窄(MA50 ${ma50:,.0f} < MA200 ${ma200:,.0f}, {gap_pct:.1f}%)，可能筑底，观望"
    else:
        xover_signal = 0
        xover_detail = "数据不足200日"

    signals.append({
        "dimension": "MA50/200交叉",
        "signal": xover_signal,
        "direction": "看多" if xover_signal > 0 else ("看空" if xover_signal < 0 else "中性"),
        "detail": xover_detail,
        "weight": 0.25,  # 第二权重：中期趋势
    })

    # ========== 定量3: 最大回撤（趋势风险管理） ==========
    # 逻辑：回撤幅度反映趋势受损程度
    # 回撤<5%: healthy pullback (+1), 5-10%: normal (0), 
    # 10-15%: warning (-0.5), 15-25%: significant (-1), >25%: trend broken (-1)
    if n >= 252:
        y1_high = _rolling_max(gold_prices, 252)
        if y1_high and y1_high > 0:
            dd_pct = (current_price / y1_high - 1) * 100

            if dd_pct > -5:
                dd_signal = +1
                dd_detail = f"距1年高${y1_high:,.0f} 回撤{dd_pct:+.1f}%(<5%)，趋势完好，健康调整"
            elif dd_pct > -10:
                dd_signal = 0
                dd_detail = f"距1年高${y1_high:,.0f} 回撤{dd_pct:+.1f}%(5-10%)，正常波动区间"
            elif dd_pct > -15:
                dd_signal = -0.5
                dd_detail = f"距1年高${y1_high:,.0f} 回撤{dd_pct:+.1f}%(10-15%)，回调加深，趋势可能受损，需警惕"
            elif dd_pct > -25:
                dd_signal = -1
                dd_detail = f"距1年高${y1_high:,.0f} 回撤{dd_pct:+.1f}%(15-25%)，深度回调，趋势严重受损，不建议做多"
            else:
                dd_signal = -1
                dd_detail = f"距1年高${y1_high:,.0f} 回撤{dd_pct:+.1f}%(>25%)，可能已入熊市，坚决不做多"
        else:
            dd_signal = 0
            dd_detail = "无法计算回撤"
    else:
        dd_signal = 0
        dd_detail = "数据不足1年"

    signals.append({
        "dimension": "最大回撤",
        "signal": dd_signal,
        "direction": "看多" if dd_signal > 0 else ("看空" if dd_signal < 0 else "中性"),
        "detail": dd_detail,
        "weight": 0.20,
    })

    # ========== 定量4: 相关性崩坏检测（结构信号） ==========
    # 研报指出传统框架（实际利率↑→金价↓）正失效
    # 如果金价与利率长期同向变动，说明结构性因素主导 → 利多
    if n >= 252:
        y10_prices = [r["close"] for r in history.get("US10Y", []) if r.get("close")]
        if len(y10_prices) >= 252:
            g_prices = gold_prices[-252:]
            y_prices = y10_prices[-252:]

            g_dir = [1 if g_prices[i] > g_prices[i-1] else 0 for i in range(1, len(g_prices))]
            y_dir = [1 if y_prices[i] > y_prices[i-1] else 0 for i in range(1, len(y_prices))]
            min_len = min(len(g_dir), len(y_dir))
            if min_len > 0:
                same = sum(1 for i in range(min_len) if g_dir[i] == y_dir[i])
                same_pct = same / min_len

                if same_pct > 0.55:
                    corr_signal = +1
                    corr_detail = f"金价与利率同向变动{same_pct*100:.0f}%交易日(>55%)，传统框架失效，结构性资金主导，利多"
                elif same_pct > 0.45:
                    corr_signal = 0
                    corr_detail = f"金价与利率同向变动{same_pct*100:.0f}%交易日(45-55%)，关系不稳定"
                else:
                    corr_signal = -0.5
                    corr_detail = f"金价与利率反向变动{(1-same_pct)*100:.0f}%交易日，传统负相关仍有效，利率上行或压制金价"
            else:
                corr_signal = 0; corr_detail = "数据不足"
        else:
            corr_signal = 0; corr_detail = "利率数据不足"
    else:
        corr_signal = 0; corr_detail = "黄金历史数据不足"

    signals.append({
        "dimension": "定价框架有效性",
        "signal": corr_signal,
        "direction": "看多" if corr_signal > 0 else ("看空" if corr_signal < 0 else "中性"),
        "detail": corr_detail,
        "weight": 0.15,
    })

    # ========== 定量5: 上海金溢价趋势 ==========
    premium_data = daily.get("gold_premium", {})
    premium_pct = premium_data.get("premium_pct")
    if premium_pct is not None and abs(premium_pct) < 50:
        if premium_pct > 3:
            prem_signal = +1
            prem_detail = f"上海金溢价+{premium_pct:.1f}%(>3%)，国内需求强劲，看多"
        elif premium_pct > 1:
            prem_signal = +0.5
            prem_detail = f"上海金溢价+{premium_pct:.1f}%(1-3%)，国内需求偏强"
        elif premium_pct < -3:
            prem_signal = -0.5
            prem_detail = f"上海金折价{premium_pct:.1f}%(<-3%)，国内需求疲弱"
        else:
            prem_signal = 0
            prem_detail = f"上海金溢价{premium_pct:+.1f}%，正常区间"
    else:
        prem_signal = 0
        prem_detail = "上海金数据暂缺"

    signals.append({
        "dimension": "上海金溢价",
        "signal": prem_signal,
        "direction": "看多" if prem_signal > 0 else ("看空" if prem_signal < 0 else "中性"),
        "detail": prem_detail,
        "weight": 0.10,
    })

    total_quant = sum(s["signal"] * s["weight"] for s in signals)
    return {
        "signals": signals,
        "total_score": round(total_quant, 2),
        "max_score": sum(abs(s["weight"]) for s in signals),
        "normalized": round(total_quant / sum(abs(s["weight"]) for s in signals), 2) if sum(abs(s["weight"]) for s in signals) > 0 else 0,
        "direction": "看多" if total_quant > 0.1 else ("看空" if total_quant < -0.1 else "中性"),
        "intensity": abs(round(total_quant / sum(abs(s["weight"]) for s in signals), 2)) if sum(abs(s["weight"]) for s in signals) > 0 else 0,
    }


def calc_exit_strategy(qual, quant, daily, history):
    """分层离场方案"""
    gold_prices = [r["close"] for r in history.get("XAU", []) if r.get("close")]
    current_price = gold_prices[-1] if gold_prices else 0
    n = len(gold_prices)

    ma20 = _ma(gold_prices, 20) if n >= 20 else None
    ma50 = _ma(gold_prices, 50) if n >= 50 else None
    ma200 = _ma(gold_prices, 200) if n >= 200 else None
    y1_high = _rolling_max(gold_prices, 252) if n >= 252 else current_price

    dd_pct = (current_price / y1_high - 1) * 100 if y1_high and y1_high > 0 else 0

    # 四层离场条件
    layers = []

    # Layer 1: MA20 跌破 → 减仓1/3 或 不做多
    ma20_broken = ma20 and current_price < ma20 * 0.99
    layers.append({
        "level": 1,
        "name": "MA20趋势线失守",
        "condition": f"金价${current_price:,.0f} {'<' if ma20_broken else '>'} MA20(${ma20:,.0f})",
        "triggered": ma20_broken,
        "action": "减仓至2/3 或 平掉新增仓位" if ma20_broken else "暂未触发，可维持仓位",
        "severity": "⚠ 黄色预警" if ma20_broken else "✅ 正常",
    })

    # Layer 2: MA50/MA200 死叉 → 再减1/3
    death_cross = ma50 and ma200 and ma50 < ma200
    layers.append({
        "level": 2,
        "name": "MA50/MA200死叉确认",
        "condition": f"MA50(${ma50:,.0f}) {'<' if death_cross else '>'} MA200(${ma200:,.0f})",
        "triggered": death_cross,
        "action": "再减仓至1/3，转为防御模式" if death_cross else "暂未触发" if not ma20_broken else "等待MA20信号先触发后跟进",
        "severity": "🔴 红色预警" if death_cross else ("⚠ 待观察" if ma20_broken else "✅ 正常"),
    })

    # Layer 3: 回撤 > 15% → 清仓观望
    dd_triggered = dd_pct < -15
    layers.append({
        "level": 3,
        "name": "深度回撤确认",
        "condition": f"距1年高${y1_high:,.0f}回撤{dd_pct:+.1f}% (阈值: <-15%)",
        "triggered": dd_triggered,
        "action": "深度回撤{:.0f}%，趋势可能终结，建议清仓观望".format(abs(dd_pct)) if dd_triggered else "回撤可控" if dd_pct > -10 else "关注回撤加深风险",
        "severity": "🔴 红色预警" if dd_triggered else ("⚠ 黄色预警" if dd_pct < -10 else "✅ 正常"),
    })

    # Layer 4: 定性信号反转（最可靠的顶部信号，80%准确率）→ 最终确认
    qual_reversed = qual["direction"] == "看空"
    layers.append({
        "level": 4,
        "name": "定性信号反转（基本面确认）",
        "condition": f"美联储政策+经济象限: {qual['direction']}",
        "triggered": qual_reversed,
        "action": "结构性利空确认：美联储收紧 + 经济进入复苏象限 → 黄金牛市可能终结" if qual_reversed else "定性仍利多，即使技术面走坏，结构性支撑仍在",
        "severity": "🔴🔴 最终确认" if qual_reversed else "✅ 结构性支撑",
    })

    # 综合离场建议
    triggered_count = sum(1 for l in layers if l["triggered"])
    if triggered_count >= 3:
        exit_verdict = "强烈建议离场/不做多"
        exit_detail = f"已触发{triggered_count}层离场信号，黄金可能已进入熊市或深度调整"
    elif triggered_count >= 2:
        exit_verdict = "建议大幅减仓"
        exit_detail = f"已触发{triggered_count}层离场信号，趋势严重受损"
    elif triggered_count >= 1:
        exit_verdict = "警惕，逐步减仓"
        exit_detail = f"已触发{triggered_count}层离场信号，建议控制风险"
    else:
        exit_verdict = "趋势完好，可持有"
        exit_detail = "未触发任何离场信号，趋势向上"

    return {
        "layers": layers,
        "triggered_count": triggered_count,
        "verdict": exit_verdict,
        "detail": exit_detail,
    }


def calc_combined(qual, quant):
    """综合定性+定量研判"""
    ql_dir = qual["direction"]
    qt_dir = quant["direction"]
    ql_score = qual["normalized"]
    qt_score = quant["normalized"]

    if (ql_dir == "看多" and qt_dir == "看空") or (ql_dir == "看空" and qt_dir == "看多"):
        verdict = "观望"
        direction = "观望"
        detail = "定性信号与定量信号方向矛盾。定性（基本面）看多但定量（技术面）看空，建议等待信号一致。"
        confidence = "低"
    elif ql_dir == "中性" and qt_dir == "中性":
        verdict = "观望"
        direction = "中性"
        detail = "定性定量信号均为中性，无明显方向性机会。"
        confidence = "低"
    elif ql_dir == "中性":
        direction = qt_dir
        if abs(qt_score) > 0.4:
            verdict = f"偏{qt_dir}"; confidence = "中"
            detail = f"定性信号中性，定量信号偏{qt_dir}(强度{abs(qt_score):.0%})，以技术面为主"
        else:
            verdict = "观望"; direction = "中性"; confidence = "低"
            detail = "定性信号中性，定量信号也较弱，无明显机会"
    elif qt_dir == "中性":
        direction = ql_dir
        if abs(ql_score) > 0.4:
            verdict = f"偏{ql_dir}"; confidence = "中"
            detail = f"定性信号偏{ql_dir}(强度{abs(ql_score):.0%})，定量信号中性，可维持现有仓位"
        else:
            verdict = "观望"; direction = "中性"; confidence = "低"
            detail = "定性信号较弱，定量中性，无明显机会"
    elif ql_dir == qt_dir:
        direction = ql_dir
        avg_intensity = (abs(ql_score) + abs(qt_score)) / 2
        if avg_intensity > 0.5:
            verdict = f"强烈{ql_dir}"; confidence = "高"
            detail = f"定性定量信号一致{ql_dir}，强度高({avg_intensity:.0%})。建议积极{'做多' if ql_dir == '看多' else '减仓/做空'}。"
        elif avg_intensity > 0.3:
            verdict = ql_dir; confidence = "中"
            detail = f"定性定量信号一致{ql_dir}，强度中等({avg_intensity:.0%})，可适度参与。"
        else:
            verdict = f"偏{ql_dir}"; confidence = "低"
            detail = f"定性定量信号一致{ql_dir}但强度较弱({avg_intensity:.0%})，小仓位试探。"

    return {
        "verdict": verdict,
        "direction": direction,
        "confidence": confidence,
        "detail": detail,
        "qual_score": ql_score,
        "quant_score": qt_score,
        "qual_direction": ql_dir,
        "quant_direction": qt_dir,
    }


def calc_historical_backtest(history, fred):
    """回测：新框架下各信号状态的3个月预期表现"""
    gold_prices = [r["close"] for r in history.get("XAU", []) if r.get("close")]
    if len(gold_prices) < 252:
        return {"note": "历史数据不足1年"}

    n = len(gold_prices)
    monthly = []

    for i in range(251, n, 21):
        if i >= n:
            break
        current = gold_prices[i]
        window = gold_prices[:i+1]

        # MA20, MA50, MA200
        ma20 = _ma(window, 20)
        ma50 = _ma(window, 50) if len(window) >= 50 else current
        ma200 = _ma(window, 200) if len(window) >= 200 else current

        # 信号判定（简化版）
        ma20_bull = ma20 and current > ma20
        golden_cross = ma50 and ma200 and ma50 > ma200
        death_cross = ma50 and ma200 and ma50 < ma200

        if ma20_bull and golden_cross:
            signal = "看多"
        elif not ma20_bull and death_cross:
            signal = "看空"
        else:
            signal = "中性"

        # 前向3个月收益
        fwd_idx = min(i + 63, n - 1)
        fwd_return = (gold_prices[fwd_idx] / current - 1) * 100

        y1_high = _rolling_max(window, min(252, len(window)))
        dd_pct = (current / y1_high - 1) * 100 if y1_high else 0

        monthly.append({
            "date": gold_dates[i] if i < len(gold_dates) else "",
            "price": round(current, 2),
            "ma20_above": ma20_bull,
            "ma50_200": "金叉" if golden_cross else ("死叉" if death_cross else "震荡"),
            "signal": signal,
            "fwd_3m_return": round(fwd_return, 2),
            "dd_pct": round(dd_pct, 2),
        })

    # 统计
    signal_stats = {}
    for s in ["看多", "中性", "看空"]:
        subset = [m for m in monthly if m["signal"] == s]
        if subset:
            avg_fwd = sum(m["fwd_3m_return"] for m in subset) / len(subset)
            pos_pct = sum(1 for m in subset if m["fwd_3m_return"] > 0) / len(subset) * 100
            signal_stats[s] = {
                "count": len(subset),
                "probability": round(len(subset) / len(monthly) * 100, 1),
                "avg_3m_return": round(avg_fwd, 2),
                "positive_rate": round(pos_pct, 1),
            }

    # 时间段
    periods = []
    current_period = None
    gold_dates_list = gold_dates if gold_dates else []
    for m in monthly:
        dt = str(m["date"])[:10]
        if current_period is None or current_period["signal"] != m["signal"]:
            if current_period:
                current_period["end"] = dt
                periods.append(current_period)
            current_period = {"signal": m["signal"], "start": dt, "end": None}
    if current_period:
        current_period["end"] = str(monthly[-1]["date"])[:10]
        periods.append(current_period)

    return {
        "monthly_signals": monthly[-24:],
        "signal_stats": signal_stats,
        "periods": periods[-12:],
        "total_months": len(monthly),
    }


# 需要gold_dates全局 — 修正一下
gold_dates = []


def generate_signals():
    global gold_dates

    print("=" * 60)
    print(f"黄金信号引擎 v2 (趋势跟踪) 开始: {datetime.now().isoformat()}")
    print("=" * 60)

    data = load_data()
    daily = data["daily"]
    history = data["history"]
    fred = data.get("fred", {})

    global gold_dates
    gold_dates = [r["date"] for r in history.get("XAU", []) if r.get("close")]

    # 1. 定性信号
    print("\n[定性分析] 研报框架...")
    qual = calc_qualitative_signals(daily, history, fred)
    print(f"  方向: {qual['direction']} ({qual['normalized']:+.0%})")

    # 2. 定量信号 v2
    print("\n[定量分析 v2] 趋势跟踪框架...")
    quant = calc_quantitative_signals(daily, history)
    print(f"  方向: {quant['direction']} ({quant['normalized']:+.0%})")
    for s in quant["signals"]:
        print(f"    {s['dimension']}: {s['direction']} (权重{s['weight']:.0%}) — {s['detail'][:60]}...")

    # 3. 综合研判
    print("\n[综合研判]")
    combined = calc_combined(qual, quant)
    print(f"  结论: {combined['verdict']} | 置信度: {combined['confidence']}")

    # 4. 离场方案
    print("\n[离场方案] 分层信号...")
    exit_plan = calc_exit_strategy(qual, quant, daily, history)
    print(f"  触发层数: {exit_plan['triggered_count']}/4")
    print(f"  建议: {exit_plan['verdict']}")
    for layer in exit_plan["layers"]:
        tag = "⚠" if layer["triggered"] else "✓"
        print(f"    {tag} L{layer['level']} {layer['name']}: {layer['severity']} — {layer['action']}")

    # 5. 回测
    print("\n[历史回测 v2]")
    backtest = calc_historical_backtest(history, fred)
    if "note" not in backtest:
        print(f"  统计月份: {backtest['total_months']}")
        for sig, stats in backtest["signal_stats"].items():
            print(f"    {sig}: 占比{stats['probability']}%, 平均3M {stats['avg_3m_return']:+.2f}%, 胜率{stats['positive_rate']:.0f}%")

    result = {
        "generated_at": datetime.now().isoformat(),
        "framework_version": "v2-trend-following",
        "qualitative": qual,
        "quantitative": quant,
        "combined": combined,
        "exit_strategy": exit_plan,
        "backtest": backtest,
        "market_snapshot": {
            "gold_usd": daily.get("XAU", {}).get("close"),
            "gold_stats": daily.get("gold_stats", {}),
            "dxy": daily.get("DXY", {}).get("close"),
            "us10y": daily.get("US10Y", {}).get("close"),
            "tips": daily.get("real_yield", {}).get("value"),
            "fed_rate": daily.get("fed_rate"),
            "usdcny": daily.get("USDCNY", {}).get("close"),
            "vix": daily.get("VIX", {}).get("close"),
        },
    }

    with open(SIGNALS_FILE, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2, default=str)

    print(f"\n信号已保存至: {SIGNALS_FILE}")
    return result


if __name__ == "__main__":
    generate_signals()
