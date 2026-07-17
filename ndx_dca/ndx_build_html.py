"""
纳斯达克100定投仪表盘 — HTML 生成脚本
生成单文件 HTML 仪表盘，使用 Chart.js 图表
"""
import sys, io, os, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

BASE = os.path.dirname(os.path.abspath(__file__))
DATA_JSON = os.path.join(BASE, 'data', 'ndx_dashboard_data.json')
OUTPUT_HTML = os.path.join(BASE, 'ndx_dashboard.html')

with open(DATA_JSON, 'r', encoding='utf-8') as f:
    d = json.load(f)

def fmt(n, decimals=0):
    if n is None: return '—'
    if decimals == 0:
        return f"{n:,.0f}"
    return f"{n:,.{decimals}f}"

def pct(n, decimals=2):
    if n is None: return '—'
    return f"{n:+.{decimals}f}%"

def color_pct(n):
    if n is None: return '#888'
    if n > 0: return '#ff4444' if n > 2 else '#ff6666'  # NDX up = red (Chinese convention) or green
    if n < 0: return '#00cc66' if n < -2 else '#33cc33'
    return '#888'

# NDX convention: green up, red down (US convention for this dashboard)
def ndx_color(v):
    if v is None: return '#888'
    return '#22c55e' if v >= 0 else '#ef4444'

html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate">
<meta http-equiv="Pragma" content="no-cache">
<meta http-equiv="Expires" content="0">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>纳斯达克100定投指示板 | NDX DCA Dashboard</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 'Microsoft YaHei', sans-serif;
    background: #0a0e17;
    color: #e2e8f0;
    min-height: 100vh;
    padding: 0;
}}
.header {{
    background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
    border-bottom: 1px solid #334155;
    padding: 16px 24px;
    display: flex; justify-content: space-between; align-items: center;
    flex-wrap: wrap; gap: 8px;
}}
.header h1 {{
    font-size: 1.5rem; font-weight: 700;
    background: linear-gradient(135deg, #60a5fa, #a78bfa);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    background-clip: text;
}}
.header .subtitle {{ font-size: 0.8rem; color: #94a3b8; }}
.header .update {{ font-size: 0.75rem; color: #64748b; }}

.container {{ max-width: 1200px; margin: 0 auto; padding: 16px; }}

/* DCA Hero Card */
.dca-hero {{
    background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
    border: 2px solid #334155;
    border-radius: 16px;
    padding: 28px 32px;
    text-align: center;
    margin-bottom: 20px;
    position: relative;
    overflow: hidden;
}}
.dca-hero::before {{
    content: ''; position: absolute; top: -50%; left: -50%; width: 200%; height: 200%;
    background: radial-gradient(circle at 50% 50%, {d['valuation_color']}15 0%, transparent 70%);
    animation: pulse 3s ease-in-out infinite;
}}
@keyframes pulse {{
    0%, 100% {{ opacity: 0.3; }}
    50% {{ opacity: 0.7; }}
}}
.dca-hero .label {{ font-size: 0.9rem; color: #94a3b8; text-transform: uppercase; letter-spacing: 2px; margin-bottom: 8px; }}
.dca-hero .amount {{
    font-size: 4rem; font-weight: 800; color: {d['valuation_color']};
    text-shadow: 0 0 40px {d['valuation_color']}44;
    line-height: 1.1;
}}
.dca-hero .amount .unit {{ font-size: 1.5rem; font-weight: 500; color: #94a3b8; }}
.dca-hero .val-label {{
    display: inline-block; margin-top: 12px; padding: 6px 20px;
    background: {d['valuation_color']}22; color: {d['valuation_color']};
    border: 1px solid {d['valuation_color']}44;
    border-radius: 20px; font-size: 0.95rem; font-weight: 600;
}}
.dca-hero .base-info {{ font-size: 0.8rem; color: #64748b; margin-top: 10px; }}

/* Metric Cards Row */
.metrics-row {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
    gap: 14px;
    margin-bottom: 20px;
}}
.metric-card {{
    background: #111827;
    border: 1px solid #1e293b;
    border-radius: 12px;
    padding: 18px 20px;
    transition: border-color 0.3s;
}}
.metric-card:hover {{ border-color: #3b82f6; }}
.metric-card .metric-header {{
    display: flex; justify-content: space-between; align-items: center;
    margin-bottom: 10px;
}}
.metric-card .metric-name {{ font-size: 0.8rem; color: #94a3b8; text-transform: uppercase; letter-spacing: 1px; }}
.metric-card .metric-score {{
    font-size: 0.75rem; font-weight: 700; padding: 2px 10px; border-radius: 10px;
}}
.metric-card .metric-value {{ font-size: 1.8rem; font-weight: 700; }}
.metric-card .metric-detail {{ font-size: 0.75rem; color: #64748b; margin-top: 4px; }}

/* Score badge colors */
.score-neg3 {{ background: #00640033; color: #00cc66; }}
.score-neg2 {{ background: #228B2233; color: #33cc33; }}
.score-neg1 {{ background: #32CD3233; color: #66cc66; }}
.score-0 {{ background: #80808033; color: #aaa; }}
.score-pos1 {{ background: #FFA50033; color: #ffa500; }}
.score-pos2 {{ background: #FF450033; color: #ff6347; }}
.score-pos3 {{ background: #FF000033; color: #ff4444; }}

/* Charts Row */
.charts-row {{
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 16px;
    margin-bottom: 20px;
}}
@media (max-width: 768px) {{
    .charts-row {{ grid-template-columns: 1fr; }}
    .dca-hero .amount {{ font-size: 2.5rem; }}
}}
.chart-card {{
    background: #111827;
    border: 1px solid #1e293b;
    border-radius: 12px;
    padding: 16px;
}}
.chart-card.full-width {{ grid-column: 1 / -1; }}
.chart-card h3 {{ font-size: 0.85rem; color: #94a3b8; margin-bottom: 12px; text-transform: uppercase; letter-spacing: 1px; }}
.chart-card .chart-wrap {{ position: relative; width: 100%; height: 260px; }}
.chart-card .chart-wrap canvas {{ width: 100% !important; height: 100% !important; }}

/* Summary Panel */
.summary-panel {{
    background: #111827;
    border: 1px solid #1e293b;
    border-radius: 12px;
    padding: 24px;
    margin-bottom: 20px;
}}
.summary-panel h2 {{
    font-size: 1rem; color: #94a3b8; margin-bottom: 16px;
    text-transform: uppercase; letter-spacing: 1px;
}}
.summary-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 16px;
}}
.summary-item {{
    text-align: center; padding: 12px;
    border: 1px solid #1e293b; border-radius: 8px;
    background: #0f172a;
}}
.summary-item .s-label {{ font-size: 0.7rem; color: #64748b; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 4px; }}
.summary-item .s-value {{ font-size: 1.4rem; font-weight: 700; }}
.summary-item .s-sub {{ font-size: 0.7rem; color: #64748b; margin-top: 2px; }}

/* All-time chart */
.alltime-chart {{
    background: #111827;
    border: 1px solid #1e293b;
    border-radius: 12px;
    padding: 16px;
    margin-bottom: 20px;
}}
.alltime-chart h3 {{ font-size: 0.85rem; color: #94a3b8; margin-bottom: 12px; }}

.footer {{ text-align: center; padding: 16px; color: #475569; font-size: 0.7rem; }}
.footer a {{ color: #64748b; text-decoration: none; }}

/* Gauge */
.gauge-wrap {{
    display: flex; align-items: center; gap: 10px;
    margin-top: 8px;
}}
.gauge-bar {{
    flex: 1; height: 6px; background: #1e293b; border-radius: 3px;
    overflow: hidden; position: relative;
}}
.gauge-bar .fill {{
    height: 100%; border-radius: 3px; transition: width 0.5s ease;
}}
.gauge-val {{ font-size: 0.75rem; font-weight: 600; min-width: 45px; text-align: right; }}

/* Tooltip */
.tooltip-note {{
    font-size: 0.7rem; color: #64748b; font-style: italic; margin-top: 6px;
}}
</style>
</head>
<body>

<div class="header">
    <div>
        <h1>📊 纳斯达克100 定投指示板</h1>
        <div class="subtitle">目标 {d['target_total']/10000:.0f}万 · {d['target_years']}年定投 · 起始 {d['start_date']} · 为小朋友的未来 ❤️</div>
    </div>
    <div class="update">
        最后交易日: {d['last_trading_day']}<br>
        生成时间: {d['generated_at']}
    </div>
</div>

<div class="container">
    <!-- Data freshness warning -->
    <div id="freshness-warning" style="display:none;background:#7f1d1d;border:1px solid #ef4444;border-radius:8px;padding:10px 16px;margin-bottom:16px;text-align:center;color:#fca5a5;font-size:0.85rem;">
        ⚠️ 数据最后更新于 <strong>{d['last_trading_day']}</strong>，可能已过期。请检查网络或等待自动更新。
    </div>

    <!-- DCA Hero -->
    <div class="dca-hero">
        <div class="label">📌 今日建议定投金额</div>
        <div class="amount">{fmt(d['dca_amount'], 0)} <span class="unit">CNY</span></div>
        <div class="val-label">{d['valuation_label']} · 倍数 {d['multiplier']}x</div>
        <div class="base-info">基础日投 {fmt(d['base_daily'], 0)} 元 × {d['multiplier']}x · 最小单位 {d['min_unit']} 元 · 向下取整</div>
    </div>

    <!-- 4 Indicator Cards -->
    <div class="metrics-row">
        <div class="metric-card">
            <div class="metric-header">
                <span class="metric-name">📈 NDX 100 指数</span>
                <span style="font-size:0.75rem;color:{ndx_color(d['ndx_change_pct'])};font-weight:700;">日变动 {d['ndx_change_pct']:+.2f}%</span>
            </div>
            <div class="metric-value" style="color: {ndx_color(d['ndx_change_pct'])};">{fmt(d['ndx'], 2)}</div>
            <div class="metric-detail">MA200: {fmt(d['ndx_ma200'], 2)} · 比率: {d['ndx_ma200_ratio']:.4f}</div>
            <div class="gauge-wrap">
                <span style="font-size:0.7rem;color:#64748b;">MA200</span>
                <div class="gauge-bar">
                    <div class="fill" style="width:{min(100, max(0, (d['ndx_ma200_ratio']-0.7)/0.6*100))}%; background: {d['valuation_color']};"></div>
                </div>
                <span class="gauge-val">{d['ndx_ma200_ratio']:.4f}</span>
            </div>
        </div>

        <div class="metric-card">
            <div class="metric-header">
                <span class="metric-name">😰 VIX 恐慌指数</span>
                <span style="font-size:0.7rem;color:#64748b;">参考</span>
            </div>
            <div class="metric-value" style="color: {('#ef4444' if d['vix']>28 else '#f59e0b' if d['vix']>20 else '#22c55e')};">{fmt(d['vix'], 2)}</div>
            <div class="metric-detail">{'🔴 极度恐慌' if d['vix']>35 else '🟠 恐慌偏高' if d['vix']>28 else '🟡 轻微不安' if d['vix']>20 else '🟢 市场平稳' if d['vix']>14 else '⚠️ 过度安逸'}</div>
            <div class="gauge-wrap">
                <span style="font-size:0.7rem;color:#64748b;">10</span>
                <div class="gauge-bar">
                    <div class="fill" style="width:{min(100, max(0, (d['vix']-10)/40*100))}%; background: linear-gradient(90deg, #22c55e, #f59e0b, #ef4444);"></div>
                </div>
                <span style="font-size:0.7rem;color:#64748b;">50</span>
            </div>
        </div>

        <div class="metric-card">
            <div class="metric-header">
                <span class="metric-name">📉 NDX / MA200</span>
                <span class="metric-score score-{'neg' if d['score_ma200']<0 else 'pos'}{abs(d['score_ma200'])}">得分 {d['score_ma200']:+d}</span>
            </div>
            <div class="metric-value" style="color: {d['valuation_color']};">{d['ndx_ma200_ratio']:.4f}</div>
            <div class="metric-detail">{'深跌超20%' if d['ndx_ma200_ratio']<0.80 else '跌穿长期均线' if d['ndx_ma200_ratio']<0.88 else '偏弱运行' if d['ndx_ma200_ratio']<0.95 else '合理区间' if d['ndx_ma200_ratio']<=1.05 else '温和偏强' if d['ndx_ma200_ratio']<=1.15 else '显著高估' if d['ndx_ma200_ratio']<=1.25 else '泡沫区域'}</div>
            <div class="gauge-wrap">
                <span style="font-size:0.7rem;color:#64748b;">0.7</span>
                <div class="gauge-bar">
                    <div class="fill" style="width:{min(100, max(0, (d['ndx_ma200_ratio']-0.7)/0.6*100))}%; background: linear-gradient(90deg, #006400, #808080, #ff0000);"></div>
                </div>
                <span style="font-size:0.7rem;color:#64748b;">1.3</span>
            </div>
        </div>

        <div class="metric-card">
            <div class="metric-header">
                <span class="metric-name">🧠 CNN 恐慌贪婪指数</span>
                <span style="font-size:0.7rem;color:#64748b;">参考</span>
            </div>
            <div class="metric-value" style="color: {('#ef4444' if d['cnn_fng_score'] and d['cnn_fng_score']<25 else '#f59e0b' if d['cnn_fng_score'] and d['cnn_fng_score']<45 else '#22c55e' if d['cnn_fng_score'] and d['cnn_fng_score']>75 else '#94a3b8')};">{fmt(d['cnn_fng_score'], 1) if d['cnn_fng_score'] else '—'}</div>
            <div class="metric-detail">{d['cnn_fng_rating'].upper() if d['cnn_fng_rating'] else '—'}</div>
            <div class="gauge-wrap">
                <span style="font-size:0.7rem;color:#64748b;">0 极度恐慌</span>
                <div class="gauge-bar">
                    <div class="fill" style="width:{min(100, max(0, (d['cnn_fng_score'] or 50))) if d['cnn_fng_score'] else 50}%; background: linear-gradient(90deg, #ef4444, #f59e0b, #94a3b8, #22c55e);"></div>
                </div>
                <span style="font-size:0.7rem;color:#64748b;">100 极度贪婪</span>
            </div>
        </div>
    </div>

    <!-- Composite Score Bar -->
    <div style="background:#111827;border:1px solid #1e293b;border-radius:12px;padding:18px 20px;margin-bottom:20px;text-align:center;">
        <div style="font-size:0.8rem;color:#94a3b8;text-transform:uppercase;letter-spacing:1px;margin-bottom:8px;">🎯 综合估值评分</div>
        <div style="display:flex;align-items:center;justify-content:center;gap:12px;">
            <span style="font-size:0.75rem;color:#006400;">极度低估<br>-3</span>
            <div style="flex:1;max-width:500px;height:10px;background:linear-gradient(90deg,#006400,#228B22,#32CD32,#808080,#FFA500,#FF4500,#FF0000);border-radius:5px;position:relative;">
                <div style="position:absolute;top:-4px;width:16px;height:18px;background:white;border-radius:4px;left:{min(98, max(0, (d['composite_score']+3)/6*100))}%;transform:translateX(-50%);border:2px solid #333;box-shadow:0 0 8px rgba(255,255,255,0.3);"></div>
            </div>
            <span style="font-size:0.75rem;color:#FF0000;">严重高估<br>+3</span>
        </div>
        <div style="margin-top:10px;font-size:1.2rem;font-weight:700;color:{d['valuation_color']};">{d['composite_score']:+.2f} — {d['valuation_label']}</div>
        <div style="font-size:0.7rem;color:#64748b;margin-top:4px;">
            NDX/MA200({d['score_ma200']:+d}) → 定投 {d['dca_amount']:,} CNY
        </div>
    </div>

    <!-- Charts Row 1 -->
    <div class="charts-row">
        <div class="chart-card">
            <h3>📈 NDX 100 指数 + MA200 (近180交易日)</h3>
            <div class="chart-wrap"><canvas id="chartNdx"></canvas></div>
        </div>
        <div class="chart-card">
            <h3>📊 NDX/MA200 比率趋势 (近360交易日)</h3>
            <div class="chart-wrap"><canvas id="chartRatio"></canvas></div>
        </div>
    </div>

    <!-- Charts Row 2 -->
    <div class="charts-row">
        <div class="chart-card">
            <h3>😰 VIX 恐慌指数 (近180交易日)</h3>
            <div class="chart-wrap"><canvas id="chartVix"></canvas></div>
        </div>
        <div class="chart-card">
            <h3>🧠 CNN 恐慌贪婪指数 (历史)</h3>
            <div class="chart-wrap"><canvas id="chartCnn"></canvas></div>
        </div>
    </div>

    <!-- Investment Performance Chart -->
    <div class="alltime-chart">
        <h3>💰 定投绩效: 累计投入 vs 当前市值</h3>
        <div class="chart-wrap" style="height:320px;"><canvas id="chartPerf"></canvas></div>
        {f'<div class="tooltip-note">⚠️ 定投自 {d["start_date"]} 开始，尚无历史记录</div>' if len(d.get('hist_ts',[]))==0 else ''}
    </div>

    <!-- Summary Panel -->
    <div class="summary-panel">
        <h2>📋 投资汇总 · 自 {d['start_date']} 起</h2>
        <div class="summary-grid">
            <div class="summary-item">
                <div class="s-label">📅 起始日期</div>
                <div class="s-value" style="font-size:1rem;">{d['start_date']}</div>
            </div>
            <div class="summary-item">
                <div class="s-label">💰 总投入金额</div>
                <div class="s-value" style="color:#60a5fa;">{fmt(d['total_invested'], 0)} <span style="font-size:0.8rem;">CNY</span></div>
                <div class="s-sub">目标 {d['target_total']/10000:.0f}万 · 进度 {d['total_invested']/d['target_total']*100:.1f}%</div>
            </div>
            <div class="summary-item">
                <div class="s-label">📊 当前市值</div>
                <div class="s-value" style="color:#a78bfa;">{fmt(d['current_value'], 0)} <span style="font-size:0.8rem;">CNY</span></div>
                <div class="s-sub">{fmt(d['total_shares'], 4)} 份 NDX</div>
            </div>
            <div class="summary-item">
                <div class="s-label">📈 盈亏 (P&L)</div>
                <div class="s-value" style="color:{'#22c55e' if d['pnl']>=0 else '#ef4444'};">{fmt(d['pnl'], 0)} <span style="font-size:0.8rem;">CNY</span></div>
            </div>
            <div class="summary-item">
                <div class="s-label">📊 投入至今总收益率</div>
                <div class="s-value" style="color:{'#22c55e' if d['return_rate']>=0 else '#ef4444'};">{pct(d['return_rate'])}</div>
            </div>
            <div class="summary-item">
                <div class="s-label">📉 NDX 自起投日收益率</div>
                <div class="s-value" style="color:{'#22c55e' if (d['ndx_return_since_start'] or 0)>=0 else '#ef4444'};">{pct(d['ndx_return_since_start'])}</div>
                <div class="s-sub">起投日 NDX: {fmt(d['ndx_start_value'], 2)}</div>
            </div>
            <div class="summary-item">
                <div class="s-label">⚠️ 组合最大回撤</div>
                <div class="s-value" style="color:#ef4444;">{pct(d['portfolio_max_dd']*100)}</div>
            </div>
            <div class="summary-item">
                <div class="s-label">⚠️ NDX 最大回撤</div>
                <div class="s-value" style="color:#ef4444;">{pct(d['ndx_max_dd_since_start']*100)}</div>
                <div class="s-sub">自起投日起</div>
            </div>
        </div>
    </div>

    <!-- Disclaimer -->
    <div style="background:#111827;border:1px solid #1e293b;border-radius:12px;padding:16px 20px;margin-bottom:20px;">
        <h3 style="font-size:0.8rem;color:#94a3b8;margin-bottom:6px;">📝 模型说明</h3>
        <p style="font-size:0.7rem;color:#64748b;line-height:1.6;">
            <strong>MA200 分位值单因子模型：</strong>计算 NDX/MA200 比率在 1990 年至今全历史中的分位值排名，按分位映射到 [-3, +3] 评分，根据评分确定定投倍数。均线下方多投、上方少投，简单有效。VIX 和 CNN 恐慌贪婪指数作为参考显示。<br>
            <strong>定投倍数：</strong>极度低估 2.5x → 中度低估 2.0x → 轻度低估 1.5x → 中性 1.0x → 轻度高估 0.75x → 中度高估 0.5x → 严重高估 0.25x。<br>
            <strong>基础日投：</strong>500万 ÷ 10年 ÷ 250交易日 ≈ 2,000 CNY/日。实际金额 = 基础日投 × 倍数，向下取整至 500 元。<br>
            <strong>⚠️ 免责声明：</strong>本系统仅供学习参考，不构成任何投资建议。投资有风险，入市需谨慎。历史表现不代表未来收益。
        </p>
    </div>

    <div class="footer">
        NDX DCA Dashboard · 为小朋友的未来 · {d['generated_at']} · Powered by yfinance & CNN
    </div>

</div>

<script>
// ===== CHART CONFIG =====
const gridColor = '#1e293b';
const textColor = '#64748b';

Chart.defaults.color = textColor;
Chart.defaults.borderColor = gridColor;
Chart.defaults.font.family = "-apple-system,BlinkMacSystemFont,'PingFang SC','Microsoft YaHei',sans-serif";

// ===== 1. NDX + MA200 Chart =====
new Chart(document.getElementById('chartNdx'), {{
    type: 'line',
    data: {{
        labels: {json.dumps(d['ts_180'])},
        datasets: [{{
            label: 'NDX 100',
            data: {json.dumps(d['ndx_180'])},
            borderColor: '#60a5fa',
            backgroundColor: 'rgba(96,165,250,0.05)',
            borderWidth: 2,
            pointRadius: 0,
            fill: true,
            tension: 0.3,
        }}, {{
            label: 'MA200',
            data: {json.dumps(d['ma200_180'])},
            borderColor: '#f59e0b',
            borderWidth: 1.5,
            borderDash: [6, 3],
            pointRadius: 0,
            fill: false,
            tension: 0.3,
        }}]
    }},
    options: {{
        responsive: true,
        maintainAspectRatio: false,
        plugins: {{ legend: {{ labels: {{ usePointStyle: true, boxWidth: 8 }} }} }},
        scales: {{
            x: {{ display: true, ticks: {{ maxTicksLimit: 8, maxRotation: 0 }} }},
            y: {{ display: true, ticks: {{ callback: v => v.toLocaleString() }} }}
        }},
        interaction: {{ intersect: false, mode: 'index' }}
    }}
}});

// ===== 2. NDX/MA200 Ratio Chart =====
new Chart(document.getElementById('chartRatio'), {{
    type: 'line',
    data: {{
        labels: {json.dumps(d['ratio_ts'])},
        datasets: [{{
            label: 'NDX/MA200',
            data: {json.dumps(d['ratio_vals'])},
            borderColor: '#a78bfa',
            backgroundColor: 'rgba(167,139,250,0.05)',
            borderWidth: 2,
            pointRadius: 0,
            fill: true,
            tension: 0.3,
        }}]
    }},
    options: {{
        responsive: true,
        maintainAspectRatio: false,
        plugins: {{
            legend: {{ display: false }},
        }},
        scales: {{
            x: {{ display: true, ticks: {{ maxTicksLimit: 8, maxRotation: 0 }} }},
            y: {{ display: true, ticks: {{ callback: v => v.toFixed(2) }} }}
        }},
        interaction: {{ intersect: false, mode: 'index' }}
    }}
}});

// ===== 3. VIX Chart =====
new Chart(document.getElementById('chartVix'), {{
    type: 'line',
    data: {{
        labels: {json.dumps(d['ts_180'])},
        datasets: [{{
            label: 'VIX',
            data: {json.dumps(d['vix_180'])},
            borderColor: '#f97316',
            backgroundColor: 'rgba(249,115,22,0.08)',
            borderWidth: 2,
            pointRadius: 0,
            fill: true,
            tension: 0.3,
        }}]
    }},
    options: {{
        responsive: true,
        maintainAspectRatio: false,
        plugins: {{ legend: {{ display: false }} }},
        scales: {{
            x: {{ display: true, ticks: {{ maxTicksLimit: 8, maxRotation: 0 }} }},
            y: {{ display: true, min: 0 }}
        }},
        interaction: {{ intersect: false, mode: 'index' }}
    }}
}});

// ===== 4. CNN Fear & Greed Chart =====
new Chart(document.getElementById('chartCnn'), {{
    type: 'line',
    data: {{
        labels: {json.dumps(d['cnn_ts'])},
        datasets: [{{
            label: 'CNN F&G',
            data: {json.dumps(d['cnn_vals'])},
            borderColor: '#22c55e',
            backgroundColor: function(context) {{
                const chart = context.chart;
                const {{ctx, chartArea}} = chart;
                if (!chartArea) return null;
                const gradient = ctx.createLinearGradient(0, chartArea.bottom, 0, chartArea.top);
                gradient.addColorStop(0, 'rgba(239,68,68,0.3)');
                gradient.addColorStop(0.25, 'rgba(245,158,11,0.2)');
                gradient.addColorStop(0.5, 'rgba(148,163,184,0.1)');
                gradient.addColorStop(0.75, 'rgba(34,197,94,0.2)');
                gradient.addColorStop(1, 'rgba(34,197,94,0.3)');
                return gradient;
            }},
            borderWidth: 2,
            pointRadius: 0,
            fill: true,
            tension: 0.4,
        }}]
    }},
    options: {{
        responsive: true,
        maintainAspectRatio: false,
        plugins: {{ legend: {{ display: false }} }},
        scales: {{
            x: {{ display: true, ticks: {{ maxTicksLimit: 8, maxRotation: 0 }} }},
            y: {{ display: true, min: 0, max: 100,
                ticks: {{ callback: v => v + ' ' + (v < 25 ? '(极度恐慌)' : v < 35 ? '(恐慌)' : v < 55 ? '(中性)' : v < 65 ? '(贪婪)' : '(极度贪婪)') }}
            }}
        }},
        interaction: {{ intersect: false, mode: 'index' }}
    }}
}});

// ===== 5. Investment Performance Chart =====
const histTs = {json.dumps(d['hist_ts'])};
const histInvested = {json.dumps(d['hist_invested'])};
const histValues = {json.dumps(d['hist_values'])};

if (histTs.length > 0) {{
    new Chart(document.getElementById('chartPerf'), {{
        type: 'line',
        data: {{
            labels: histTs,
            datasets: [{{
                label: '累计投入',
                data: histInvested,
                borderColor: '#60a5fa',
                backgroundColor: 'rgba(96,165,250,0.08)',
                borderWidth: 2,
                pointRadius: 0,
                fill: true,
                tension: 0.3,
            }}, {{
                label: '当前市值',
                data: histValues,
                borderColor: '#a78bfa',
                backgroundColor: 'rgba(167,139,250,0.08)',
                borderWidth: 2,
                pointRadius: 0,
                fill: true,
                tension: 0.3,
            }}]
        }},
        options: {{
            responsive: true,
            maintainAspectRatio: false,
            plugins: {{ legend: {{ labels: {{ usePointStyle: true, boxWidth: 8 }} }} }},
            scales: {{
                x: {{ display: true, ticks: {{ maxTicksLimit: 10, maxRotation: 0 }} }},
                y: {{ display: true, ticks: {{ callback: v => (v/10000).toFixed(0) + '万' }} }}
            }},
            interaction: {{ intersect: false, mode: 'index' }}
        }}
    }});
}} else {{
    document.querySelector('.alltime-chart').innerHTML = '<h3>💰 定投绩效: 累计投入 vs 当前市值</h3><div style="text-align:center;padding:60px;color:#64748b;">📅 定投将于 {d["start_date"]} 开始，届时将展示绩效图表</div>';
}}

// Auto-refresh hint
// Data freshness check
const lastTradingDay = '{d["last_trading_day"]}';
const lastDate = new Date(lastTradingDay + 'T00:00:00');
const now = new Date();
const daysSince = Math.floor((now - lastDate) / (1000 * 60 * 60 * 24));
if (daysSince > 1) {{
  const warn = document.getElementById('freshness-warning');
  if (warn) warn.style.display = 'block';
}}

console.log('NDX DCA Dashboard loaded | Last trading day: {d["last_trading_day"]} | DCA: {d["dca_amount"]} CNY | {d["valuation_label"]}');

</script>
</body>
</html>'''

with open(OUTPUT_HTML, 'w', encoding='utf-8') as f:
    f.write(html)

print(f"HTML generated: {OUTPUT_HTML}")
print(f"  Size: {len(html):,} bytes")

# Also copy to index.html for GitHub Pages
index_path = os.path.join(BASE, 'index.html')
with open(index_path, 'w', encoding='utf-8') as f:
    f.write(html)
print(f"Copied to: {index_path}")
