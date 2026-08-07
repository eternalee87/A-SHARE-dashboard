"""
黄金交易机会看板 — HTML原型生成 v2
趋势跟踪框架 + 分层离场方案
"""

import json
from pathlib import Path
from datetime import datetime

OUTPUT_DIR = Path(__file__).parent / "data"
SIGNALS_FILE = OUTPUT_DIR / "gold_signals.json"
HTML_FILE = Path(__file__).parent / "gold_dashboard.html"


def load_signals():
    with open(SIGNALS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def generate_html():
    data = load_signals()
    qual = data["qualitative"]
    quant = data["quantitative"]
    combined = data["combined"]
    exit_plan = data.get("exit_strategy", {})
    backtest = data["backtest"]
    snapshot = data["market_snapshot"]

    def s_color(direction):
        if "利多" in direction or "看多" in direction:
            return "#22c55e"
        elif "利空" in direction or "看空" in direction:
            return "#ef4444"
        return "#f59e0b"

    def s_icon(direction):
        if "利多" in direction or "看多" in direction:
            return "&#9650;"
        elif "利空" in direction or "看空" in direction:
            return "&#9660;"
        return "&#8212;"

    # 定性信号表
    qual_rows = ""
    for s in qual["signals"]:
        acc = s.get("accuracy", 0)
        acc_label = f"{acc*100:.0f}%"
        acc_color = "#22c55e" if acc >= 0.7 else "#f59e0b" if acc >= 0.5 else "#ef4444"
        qual_rows += f"""
        <tr>
            <td class="dim-name">{s['dimension']}</td>
            <td style="color:{s_color(s['direction'])};font-weight:700">{s_icon(s['direction'])} {s['direction']}</td>
            <td>{s['signal']:+d}</td>
            <td>{s['weight']*100:.0f}%</td>
            <td><span class="badge" style="background:{acc_color}">{acc_label}</span></td>
            <td class="dim-detail">{s['detail']}</td>
        </tr>"""

    # 定量信号表 v2
    quant_rows = ""
    for s in quant["signals"]:
        quant_rows += f"""
        <tr>
            <td class="dim-name">{s['dimension']}</td>
            <td style="color:{s_color(s['direction'])};font-weight:700">{s_icon(s['direction'])} {s['direction']}</td>
            <td>{s['signal']:+.1f}</td>
            <td>{s['weight']*100:.0f}%</td>
            <td class="dim-meta"></td>
            <td class="dim-detail">{s['detail']}</td>
        </tr>"""

    # 离场方案面板
    exit_rows = ""
    if exit_plan.get("layers"):
        for layer in exit_plan["layers"]:
            active = layer["triggered"]
            bg = "#450a0a" if active and "红色" in layer["severity"] else "#1e293b"
            border = "#ef4444" if active and "红色" in layer["severity"] else ("#f59e0b" if active else "#334155")
            exit_rows += f"""
            <div class="exit-layer" style="background:{bg};border-left:3px solid {border}">
                <div class="exit-level">
                    <span class="exit-num">{'&#9888;' if active else '&#10003;'}</span>
                    <span>L{layer['level']}: {layer['name']}</span>
                    <span class="exit-severity" style="color:{'#ef4444' if active else '#22c55e'}">{layer['severity']}</span>
                </div>
                <div class="exit-condition">{layer['condition']}</div>
                <div class="exit-action" style="color:{'#fca5a5' if active else '#94a3b8'}">{layer['action']}</div>
            </div>"""

    # 回测统计
    backtest_rows = ""
    if "signal_stats" in backtest:
        for sig, stats in backtest["signal_stats"].items():
            bg = "#0f2b1a" if sig == "看多" else "#1e1e0f" if sig == "中性" else "#2b0f0f"
            backtest_rows += f"""
            <tr style="background:{bg}">
                <td class="dim-name">{sig}</td>
                <td>{stats['probability']}%</td>
                <td>{stats['count']}个月</td>
                <td style="color:{'#22c55e' if stats['avg_3m_return']>0 else '#ef4444'}">{stats['avg_3m_return']:+.2f}%</td>
                <td>{stats['positive_rate']:.0f}%</td>
            </tr>"""

    period_items = ""
    if "periods" in backtest:
        for p in backtest["periods"][-8:]:
            c = "#22c55e" if p["signal"] == "看多" else "#f59e0b" if p["signal"] == "中性" else "#ef4444"
            period_items += f'<span class="period-tag" style="border-color:{c};color:{c}">{p["signal"]}: {p["start"]} ~ {p["end"]}</span>'

    # 综合研判
    verdict_color = "#22c55e" if "看多" in combined["direction"] else "#ef4444" if "看空" in combined["direction"] else "#f59e0b"
    verdict_size = "3em" if combined["confidence"] == "高" else "2em" if combined["confidence"] == "中" else "1.5em"
    conf_color = "#22c55e" if combined["confidence"] == "高" else "#f59e0b" if combined["confidence"] == "中" else "#94a3b8"

    # 离场总结
    exit_verdict = exit_plan.get("verdict", "--")
    exit_detail = exit_plan.get("detail", "")
    exit_triggered = exit_plan.get("triggered_count", 0)
    exit_verdict_color = "#ef4444" if exit_triggered >= 2 else "#f59e0b" if exit_triggered >= 1 else "#22c55e"

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>黄金交易机会看板 v2 — 趋势跟踪 + 分层离场</title>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 'Microsoft YaHei', sans-serif;
    background: #0f172a;
    color: #e2e8f0;
    min-height: 100vh;
    line-height: 1.6;
}}
.container {{ max-width: 1440px; margin: 0 auto; padding: 20px; }}
.header {{
    text-align: center;
    padding: 40px 20px 30px;
    border-bottom: 1px solid #1e293b;
    margin-bottom: 30px;
}}
.header h1 {{
    font-size: 2em;
    background: linear-gradient(135deg, #fbbf24, #f59e0b);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    margin-bottom: 8px;
}}
.header .subtitle {{ color: #94a3b8; font-size: 0.9em; }}
.header .updated {{ color: #64748b; font-size: 0.8em; margin-top: 6px; }}
.header .version {{ color: #22c55e; font-size: 0.75em; margin-top: 4px; }}

.overview-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
    gap: 16px;
    margin-bottom: 30px;
}}
.card {{
    background: #1e293b;
    border-radius: 12px;
    padding: 20px 24px;
    border: 1px solid #334155;
    transition: border-color 0.3s;
}}
.card:hover {{ border-color: #475569; }}
.card-title {{ font-size: 0.85em; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 12px; }}
.card-value {{ font-size: 2em; font-weight: 700; margin-bottom: 4px; }}
.card-sub {{ color: #64748b; font-size: 0.85em; }}

/* 综合研判 + 离场 */
.top-row {{
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 20px;
    margin-bottom: 30px;
}}
@media (max-width: 900px) {{ .top-row {{ grid-template-columns: 1fr; }} }}

.verdict-card {{
    background: linear-gradient(135deg, #1e293b, #0f172a);
    border: 2px solid {verdict_color};
    border-radius: 16px;
    padding: 24px 30px;
    display: flex;
    align-items: center;
    gap: 24px;
}}
.verdict-badge {{
    font-size: {verdict_size};
    font-weight: 900;
    color: {verdict_color};
    white-space: nowrap;
}}
.verdict-info {{ flex: 1; }}
.verdict-info h2 {{ font-size: 1.2em; margin-bottom: 6px; }}
.verdict-info .conf {{ color: {conf_color}; font-weight: 600; font-size: 0.9em; }}
.verdict-info .detail {{ color: #94a3b8; font-size: 0.9em; margin-top: 8px; line-height: 1.5; }}
.verdict-scores {{
    display: flex;
    gap: 20px;
    align-items: center;
}}
.score-item {{ text-align: center; }}
.score-item .label {{ color: #64748b; font-size: 0.75em; }}
.score-item .value {{ font-size: 1.4em; font-weight: 700; }}

.exit-card {{
    background: #1e293b;
    border: 2px solid {exit_verdict_color};
    border-radius: 16px;
    padding: 24px 30px;
}}
.exit-card h3 {{ font-size: 1.1em; margin-bottom: 4px; }}
.exit-card .exit-summary {{ color: {exit_verdict_color}; font-weight: 700; font-size: 1.3em; margin-bottom: 6px; }}
.exit-card .exit-detail {{ color: #94a3b8; font-size: 0.85em; line-height: 1.5; }}

.exit-layers {{
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 10px;
    margin-top: 16px;
}}
@media (max-width: 900px) {{ .exit-layers {{ grid-template-columns: 1fr; }} }}
.exit-layer {{
    padding: 12px 16px;
    border-radius: 10px;
}}
.exit-level {{
    display: flex;
    align-items: center;
    gap: 8px;
    font-weight: 600;
    font-size: 0.9em;
    margin-bottom: 4px;
}}
.exit-num {{ font-size: 1.1em; }}
.exit-severity {{ font-size: 0.8em; font-weight: 500; margin-left: auto; }}
.exit-condition {{ color: #94a3b8; font-size: 0.78em; margin-bottom: 4px; }}
.exit-action {{ font-size: 0.82em; font-weight: 500; }}

/* 信号面板 */
.panels {{
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 20px;
    margin-bottom: 30px;
}}
@media (max-width: 900px) {{ .panels {{ grid-template-columns: 1fr; }} }}
.panel {{
    background: #1e293b;
    border-radius: 12px;
    border: 1px solid #334155;
    overflow: hidden;
}}
.panel-header {{
    padding: 16px 20px;
    font-weight: 700;
    font-size: 1.05em;
    border-bottom: 1px solid #334155;
    display: flex;
    justify-content: space-between;
    align-items: center;
}}
.panel-header .score-summary {{ font-size: 0.85em; font-weight: 500; }}

table {{ width: 100%; border-collapse: collapse; }}
th {{
    text-align: left;
    padding: 10px 20px;
    color: #64748b;
    font-weight: 500;
    font-size: 0.78em;
    text-transform: uppercase;
    letter-spacing: 0.03em;
    border-bottom: 1px solid #334155;
}}
td {{
    padding: 10px 20px;
    font-size: 0.88em;
    border-bottom: 1px solid #1e293b;
    vertical-align: middle;
}}
.dim-name {{ font-weight: 600; white-space: nowrap; }}
.dim-detail {{ color: #94a3b8; font-size: 0.82em; max-width: 280px; }}
.dim-meta {{ color: #64748b; font-size: 0.8em; }}

.backtest-section {{ margin-bottom: 30px; }}
.periods {{ display: flex; flex-wrap: wrap; gap: 8px; margin-top: 10px; }}
.period-tag {{
    padding: 3px 10px;
    border-radius: 12px;
    border: 1px solid;
    font-size: 0.78em;
    white-space: nowrap;
}}
.badge {{
    padding: 2px 8px;
    border-radius: 10px;
    font-size: 0.75em;
    color: #fff;
    font-weight: 600;
}}

.model-note {{
    background: #1e293b;
    border: 1px solid #334155;
    border-radius: 12px;
    padding: 20px 24px;
    margin-bottom: 30px;
}}
.model-note h3 {{ color: #fbbf24; font-size: 1em; margin-bottom: 10px; }}
.model-note p {{ color: #94a3b8; font-size: 0.85em; line-height: 1.7; }}

.footer {{
    text-align: center;
    padding: 30px 20px;
    color: #475569;
    font-size: 0.8em;
    border-top: 1px solid #1e293b;
    margin-top: 20px;
}}
.footer a {{ color: #64748b; }}

.compare-table {{ margin-top: 10px; }}
.compare-table th {{ font-size: 0.75em; }}
.compare-table td {{ font-size: 0.82em; }}
</style>
</head>
<body>
<div class="container">

    <!-- 标题 -->
    <div class="header">
        <h1> Gold Trading Dashboard</h1>
        <div class="subtitle">中金李昭定价框架 + 趋势跟踪量价 + 分层离场方案</div>
        <div class="version">v2 · 趋势跟踪框架 (2026-08-06)</div>
        <div class="updated">数据更新: {data['generated_at'][:19]}</div>
    </div>

    <!-- 市场快照 -->
    <div class="overview-grid">
        <div class="card">
            <div class="card-title">Comex Gold (GC=F)</div>
            <div class="card-value" style="color:#fbbf24">${snapshot.get('gold_usd', '--'):,.0f}</div>
            <div class="card-sub">MA20: ${snapshot['gold_stats'].get('ma50', 0):,.0f} | MA200: ${snapshot['gold_stats'].get('ma200', 0):,.0f}</div>
        </div>
        <div class="card">
            <div class="card-title">DXY (美元指数)</div>
            <div class="card-value">{snapshot.get('dxy', '--')}</div>
            <div class="card-sub">USD/CNY: {snapshot.get('usdcny', '--')}</div>
        </div>
        <div class="card">
            <div class="card-title">10Y TIPS 实际利率</div>
            <div class="card-value">{snapshot.get('tips', '--')}%</div>
            <div class="card-sub">名义10Y: {snapshot.get('us10y', '--')}% | Fed: {snapshot.get('fed_rate', '--')}%</div>
        </div>
        <div class="card">
            <div class="card-title">VIX</div>
            <div class="card-value">{snapshot.get('vix', '--')}</div>
            <div class="card-sub">1Y高${snapshot['gold_stats'].get('max_1y', 0):,.0f} | 回撤{snapshot['gold_stats'].get('pct_from_1y_high', 0):+.1f}%</div>
        </div>
    </div>

    <!-- 综合研判 + 离场方案 (并排) -->
    <div class="top-row">
        <div class="verdict-card">
            <div class="verdict-badge">{combined['verdict']}</div>
            <div class="verdict-info">
                <h2>综合研判: {combined['verdict']}</h2>
                <div class="conf">置信度: {combined['confidence']} | 定性{combined['qual_direction']} + 定量{combined['quant_direction']}</div>
                <div class="detail">{combined['detail']}</div>
            </div>
            <div class="verdict-scores">
                <div class="score-item">
                    <div class="label">定性</div>
                    <div class="value" style="color:{s_color(combined['qual_direction'])}">{combined['qual_score']:+.0%}</div>
                </div>
                <div class="score-item">
                    <div class="label">定量</div>
                    <div class="value" style="color:{s_color(combined['quant_direction'])}">{combined['quant_score']:+.0%}</div>
                </div>
            </div>
        </div>

        <div class="exit-card">
            <h3>Exit Strategy</h3>
            <div class="exit-summary">{exit_verdict} ({exit_triggered}/4层触发)</div>
            <div class="exit-detail">{exit_detail}</div>
            <div class="exit-layers">{exit_rows}</div>
        </div>
    </div>

    <!-- 模型说明 -->
    <div class="model-note">
        <h3>Framework</h3>
        <p>
            <strong>定性(基本面):</strong> 美联储政策 + 经济象限(滞胀/复苏) + 美元趋势 + 实际利率 + 财政赤字 + 央行购金<br>
            <strong>定量(趋势跟踪 v2):</strong> MA20趋势线(短期) + MA50/200金叉死叉(中期) + 最大回撤(风险) + 定价框架有效性(结构) + 上海金溢价<br>
            <strong>离场方案:</strong> L1 MA20失守(减1/3) → L2 死叉确认(再减1/3) → L3 回撤>15%(清仓) → L4 定性反转(最终确认·80%准确率)<br>
            <strong>v2改进:</strong> 均值回归→趋势跟踪，看空占比64.6%→8.3%，消除"牛市全程喊空"的问题
        </p>
    </div>

    <!-- 定性/定量面板 -->
    <div class="panels">
        <div class="panel">
            <div class="panel-header">
                <span>Qualitative (Research Framework)</span>
                <span class="score-summary" style="color:{s_color(qual['direction'])}">
                    {qual['direction']} {qual['normalized']:+.0%} | acc {qual['weighted_accuracy']*100:.0f}%
                </span>
            </div>
            <div class="panel-body">
                <table>
                    <thead><tr><th>Dimension</th><th>Direction</th><th>Score</th><th>Weight</th><th>Accuracy</th><th>Detail</th></tr></thead>
                    <tbody>{qual_rows}</tbody>
                </table>
            </div>
        </div>

        <div class="panel">
            <div class="panel-header">
                <span>Quantitative (Trend Following v2)</span>
                <span class="score-summary" style="color:{s_color(quant['direction'])}">
                    {quant['direction']} {quant['normalized']:+.0%}
                </span>
            </div>
            <div class="panel-body">
                <table>
                    <thead><tr><th>Dimension</th><th>Direction</th><th>Score</th><th>Weight</th><th></th><th>Detail</th></tr></thead>
                    <tbody>{quant_rows}</tbody>
                </table>
            </div>
        </div>
    </div>

    <!-- 历史回测 -->
    <div class="backtest-section">
        <div class="panel">
            <div class="panel-header">
                <span>Backtest ({backtest.get('total_months', '--')} months, v2 framework)</span>
                <span class="score-summary" style="color:#94a3b8">3M forward return stats</span>
            </div>
            <div class="panel-body">
                <table>
                    <thead><tr><th>Signal</th><th>Probability</th><th>Count</th><th>Avg 3M Return</th><th>Win Rate</th></tr></thead>
                    <tbody>{backtest_rows}</tbody>
                </table>
                <div style="padding:12px 20px">
                    <div style="color:#94a3b8;font-size:0.82em;margin-bottom:6px">Signal Periods:</div>
                    <div class="periods">{period_items}</div>
                </div>
            </div>
        </div>
    </div>

    <!-- v1 vs v2 对比 -->
    <div class="model-note">
        <h3>v1 (Mean-Reversion) vs v2 (Trend-Following) Comparison</h3>
        <table class="compare-table">
            <thead><tr><th>Metric</th><th>v1 (MA200 Percentile)</th><th>v2 (Trend Following)</th><th>Improvement</th></tr></thead>
            <tbody>
                <tr><td>Bullish %</td><td style="color:#22c55e">10.4%</td><td style="color:#22c55e">52.1%</td><td style="color:#22c55e">+5x</td></tr>
                <tr><td>Neutral %</td><td>25.0%</td><td>39.6%</td><td>+58%</td></tr>
                <tr><td>Bearish %</td><td style="color:#ef4444">64.6%</td><td style="color:#22c55e">8.3%</td><td style="color:#22c55e">-87%</td></tr>
                <tr><td>Bull 3M return</td><td>+6.5%</td><td>+5.4%</td><td>broadly consistent</td></tr>
                <tr><td>Core problem</td><td style="color:#ef4444">Screamed SELL through entire 2025 rally</td><td style="color:#22c55e">Correctly stayed bullish during uptrend</td><td style="color:#22c55e">Fixed</td></tr>
            </tbody>
        </table>
    </div>

    <div class="footer">
        Gold Trading Dashboard v2 · Li Zhao CICC Framework + Trend Following · Prototype<br>
        Data: Yahoo Finance / FRED | Updated: {data['generated_at'][:19]}<br>
        <span style="color:#475569">Not financial advice. Gold investment carries risk.</span>
    </div>

</div>
</body>
</html>"""

    with open(HTML_FILE, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"HTML (v2) generated: {HTML_FILE}")
    print(f"Size: {HTML_FILE.stat().st_size / 1024:.1f} KB")


if __name__ == "__main__":
    generate_html()
