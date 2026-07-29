"""
中证红利质量指数 (931468) 定投仪表盘 — HTML生成
"""
import sys, io, os, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

BASE = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(BASE, 'data', 'dashboard_data.json'), 'r', encoding='utf-8') as f:
    d = json.load(f)

def fmt(n, d=0): return f"{n:,.{d}f}" if n is not None else '—'
def pct(n): return f"{n:+.2f}%" if n is not None else '—'

html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate">
<meta http-equiv="Pragma" content="no-cache">
<meta http-equiv="Expires" content="0">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>中证红利质量定投 | CSI Dividend Quality DCA</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ font-family: -apple-system, BlinkMacSystemFont, 'PingFang SC', 'Microsoft YaHei', sans-serif; background: #0a0e17; color: #e2e8f0; min-height:100vh; }}
.header {{ background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%); border-bottom:1px solid #334155; padding:16px 24px; display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px; }}
.header h1 {{ font-size:1.5rem; font-weight:700; background: linear-gradient(135deg, #f59e0b, #ef4444); -webkit-background-clip:text; -webkit-text-fill-color:transparent; background-clip:text; }}
.header .subtitle {{ font-size:0.8rem; color:#94a3b8; }}
.header .update {{ font-size:0.75rem; color:#64748b; }}
.container {{ max-width:900px; margin:0 auto; padding:16px; }}

.dca-hero {{ background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%); border:2px solid #334155; border-radius:16px; padding:28px 32px; text-align:center; margin-bottom:20px; position:relative; overflow:hidden; }}
.dca-hero::before {{ content:''; position:absolute; top:-50%; left:-50%; width:200%; height:200%; background: radial-gradient(circle at 50% 50%, {d['valuation_color']}15 0%, transparent 70%); }}
.dca-hero .label {{ font-size:0.9rem; color:#94a3b8; text-transform:uppercase; letter-spacing:2px; margin-bottom:8px; }}
.dca-hero .amount {{ font-size:4rem; font-weight:800; color:{d['valuation_color']}; text-shadow:0 0 40px {d['valuation_color']}44; line-height:1.1; }}
.dca-hero .amount .unit {{ font-size:1.5rem; color:#94a3b8; }}
.dca-hero .val-label {{ display:inline-block; margin-top:12px; padding:6px 20px; background:{d['valuation_color']}22; color:{d['valuation_color']}; border:1px solid {d['valuation_color']}44; border-radius:20px; font-size:0.95rem; font-weight:600; }}
.dca-hero .base-info {{ font-size:0.8rem; color:#64748b; margin-top:10px; }}

.metrics-row {{ display:grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap:14px; margin-bottom:20px; }}
.metric-card {{ background:#111827; border:1px solid #1e293b; border-radius:12px; padding:18px 20px; }}
.metric-card .metric-name {{ font-size:0.8rem; color:#94a3b8; text-transform:uppercase; letter-spacing:1px; margin-bottom:8px; }}
.metric-card .metric-value {{ font-size:1.8rem; font-weight:700; }}
.metric-card .metric-detail {{ font-size:0.75rem; color:#64748b; margin-top:4px; }}

.charts-row {{ display:grid; grid-template-columns:1fr 1fr; gap:16px; margin-bottom:20px; }}
@media (max-width:768px) {{ .charts-row {{ grid-template-columns:1fr; }} .dca-hero .amount {{ font-size:2.5rem; }} }}
.chart-card {{ background:#111827; border:1px solid #1e293b; border-radius:12px; padding:16px; }}
.chart-card.full {{ grid-column:1/-1; }}
.chart-card h3 {{ font-size:0.85rem; color:#94a3b8; margin-bottom:12px; }}
.chart-card .chart-wrap {{ position:relative; width:100%; height:260px; }}
.chart-card .chart-wrap canvas {{ width:100%!important; height:100%!important; }}

.summary-panel {{ background:#111827; border:1px solid #1e293b; border-radius:12px; padding:24px; margin-bottom:20px; }}
.summary-panel h2 {{ font-size:1rem; color:#94a3b8; margin-bottom:16px; }}
.summary-grid {{ display:grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap:16px; }}
.summary-item {{ text-align:center; padding:12px; border:1px solid #1e293b; border-radius:8px; background:#0f172a; }}
.summary-item .s-label {{ font-size:0.7rem; color:#64748b; text-transform:uppercase; letter-spacing:1px; }}
.summary-item .s-value {{ font-size:1.3rem; font-weight:700; }}
.summary-item .s-sub {{ font-size:0.7rem; color:#64748b; margin-top:2px; }}

.footer {{ text-align:center; padding:16px; color:#475569; font-size:0.7rem; }}
</style>
</head>
<body>

<div class="header">
    <div>
        <h1>🏦 中证红利质量 定投指示板</h1>
        <div class="subtitle">指数 931468 · ETF 159209 · 目标 {d['target_total']/10000:.0f}万 · {d['target_years']}年 · 起始 {d['start_date']}</div>
    </div>
    <div class="update">最后交易日: {d['last_trading_day']}<br>生成: {d['generated_at']}</div>
</div>

<div class="container">

<div class="dca-hero">
    <div class="label">📌 本周建议定投金额</div>
    <div class="amount">{fmt(d['dca_amount'], 0)} <span class="unit">CNY</span></div>
    <div class="val-label">{d['valuation_label']} · 倍数 {d['multiplier']}x</div>
    <div class="base-info">基础周投 {fmt(d['base_weekly'], 0)} 元 × {d['multiplier']}x · 最小 {d['min_unit']} 元</div>
</div>

<div class="metrics-row">
    <div class="metric-card">
        <div class="metric-name">📈 指数 931468</div>
        <div class="metric-value" style="color:#f59e0b;">{fmt(d['csi'], 2)}</div>
        <div class="metric-detail">MA200: {fmt(d['ma200'], 2)} · 比率: {d['ratio']:.4f} · P{d['pct_rank']:.1f}</div>
    </div>
    <div class="metric-card">
        <div class="metric-name">📊 估值评分</div>
        <div class="metric-value" style="color:{d['valuation_color']};">{d['score']:+d}</div>
        <div class="metric-detail">{d['valuation_label']} · MA200分位 P{d['pct_rank']:.1f}</div>
    </div>
    <div class="metric-card">
        <div class="metric-name">💰 累计投入</div>
        <div class="metric-value" style="color:#60a5fa;">{fmt(d['total_invested'],0)}</div>
        <div class="metric-detail">市值 {fmt(d['current_value'],0)} · 收益 {pct(d['return_rate'])}</div>
    </div>
</div>

<div class="charts-row">
    <div class="chart-card">
        <h3>📈 指数 + MA200 (近180日)</h3>
        <div class="chart-wrap"><canvas id="chCsi"></canvas></div>
    </div>
    <div class="chart-card">
        <h3>📊 MA200 比率趋势 (近360日)</h3>
        <div class="chart-wrap"><canvas id="chRatio"></canvas></div>
    </div>
</div>

<div class="chart-card full" style="margin-bottom:20px;">
    <h3>💰 定投绩效: 累计投入 vs 当前市值</h3>
    <div class="chart-wrap" style="height:300px;"><canvas id="chPerf"></canvas></div>
</div>

<div class="summary-panel">
    <h2>📋 投资汇总 · 自 {d['start_date']} 起</h2>
    <div class="summary-grid">
        <div class="summary-item"><div class="s-label">📅 起始日期</div><div class="s-value" style="font-size:0.9rem;">{d['start_date']}</div></div>
        <div class="summary-item"><div class="s-label">💰 总投入</div><div class="s-value" style="color:#60a5fa;">{fmt(d['total_invested'],0)}</div><div class="s-sub">进度 {d['total_invested']/d['target_total']*100:.1f}%</div></div>
        <div class="summary-item"><div class="s-label">📊 市值</div><div class="s-value" style="color:#a78bfa;">{fmt(d['current_value'],0)}</div><div class="s-sub">{d['total_shares']:.4f} 份</div></div>
        <div class="summary-item"><div class="s-label">📈 盈亏</div><div class="s-value" style="color:{'#22c55e' if d['pnl']>=0 else '#ef4444'};">{fmt(d['pnl'],0)}</div></div>
        <div class="summary-item"><div class="s-label">📊 总收益率</div><div class="s-value" style="color:{'#22c55e' if d['return_rate']>=0 else '#ef4444'};">{pct(d['return_rate'])}</div></div>
        <div class="summary-item"><div class="s-label">📉 指数收益率</div><div class="s-value" style="color:{'#22c55e' if d['csi_return']>=0 else '#ef4444'};">{pct(d['csi_return'])}</div></div>
        <div class="summary-item"><div class="s-label">⚠️ 组合回撤</div><div class="s-value" style="color:#ef4444;">{pct(d['portfolio_max_dd']*100)}</div></div>
        <div class="summary-item"><div class="s-label">⚠️ 指数回撤</div><div class="s-value" style="color:#ef4444;">{pct(d['csi_max_dd']*100)}</div></div>
    </div>
</div>

<div class="footer">中证红利质量定投 · ETF 159209 · {d['generated_at']} · Powered by akshare</div>

</div>

<script>
const gc='#1e293b',tc='#64748b';
Chart.defaults.color=tc;Chart.defaults.borderColor=gc;

new Chart(document.getElementById('chCsi'),{{
    type:'line',data:{{labels:{json.dumps(d['ts_180'])},datasets:[
        {{label:'931468',data:{json.dumps(d['vals_180'])},borderColor:'#f59e0b',backgroundColor:'rgba(245,158,11,0.05)',borderWidth:2,pointRadius:0,fill:true,tension:0.3}},
        {{label:'MA200',data:{json.dumps(d['ma_180'])},borderColor:'#60a5fa',borderWidth:1.5,borderDash:[6,3],pointRadius:0,fill:false,tension:0.3}}
    ]}},
    options:{{responsive:true,maintainAspectRatio:false,plugins:{{legend:{{labels:{{usePointStyle:true,boxWidth:8}}}}}},scales:{{x:{{ticks:{{maxTicksLimit:8}}}},y:{{ticks:{{callback:v=>v.toLocaleString()}}}}}}}}
}});

new Chart(document.getElementById('chRatio'),{{
    type:'line',data:{{labels:{json.dumps(d['ratio_ts'])},datasets:[{{label:'MA200 Ratio',data:{json.dumps(d['ratio_vals'])},borderColor:'#a78bfa',borderWidth:2,pointRadius:0,fill:true,tension:0.3}}]}},
    options:{{responsive:true,maintainAspectRatio:false,plugins:{{legend:{{display:false}}}},scales:{{x:{{ticks:{{maxTicksLimit:8}}}},y:{{ticks:{{callback:v=>v.toFixed(2)}}}}}}}}
}});

const hts={json.dumps(d['hist_ts'])},hvs={json.dumps(d['hist_vals'])},his={json.dumps(d['hist_invested'])};
if(hts.length>0){{
    new Chart(document.getElementById('chPerf'),{{
        type:'line',data:{{labels:hts,datasets:[
            {{label:'累计投入',data:his,borderColor:'#60a5fa',borderWidth:2,pointRadius:0,fill:true,tension:0.3}},
            {{label:'当前市值',data:hvs,borderColor:'#a78bfa',borderWidth:2,pointRadius:0,fill:true,tension:0.3}}
        ]}},
        options:{{responsive:true,maintainAspectRatio:false,plugins:{{legend:{{labels:{{usePointStyle:true,boxWidth:8}}}}}},scales:{{x:{{ticks:{{maxTicksLimit:10}}}},y:{{ticks:{{callback:v=>(v/10000).toFixed(0)+'万'}}}}}}}}
    }});
}}else{{
    document.querySelector('.chart-card.full').innerHTML='<h3>💰 定投绩效</h3><div style="text-align:center;padding:60px;color:#64748b;">定投将开始于 {d["start_date"]}，届时展示绩效</div>';
}}
</script>
</body>
</html>'''

out_html = os.path.join(BASE, 'csi_dashboard.html')
with open(out_html, 'w', encoding='utf-8') as f:
    f.write(html)
# Also index.html
with open(os.path.join(BASE, 'index.html'), 'w', encoding='utf-8') as f:
    f.write(html)
print(f"HTML: {out_html} ({len(html):,} bytes)")
