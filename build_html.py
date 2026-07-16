import json, os

BASE = os.path.dirname(os.path.abspath(__file__))

# Load data
with open(os.path.join(BASE, 'dashboard_data.json'), 'r', encoding='utf-8') as f:
    data = json.load(f)

# Write JS data file (clean UTF-8, no f-string)
data_json = json.dumps(data, ensure_ascii=False)
with open(os.path.join(BASE, 'dashboard_data.js'), 'w', encoding='utf-8') as f:
    f.write('const DATA = ' + data_json + ';\n')
print("JS data written: dashboard_data.js")

# Write HTML (no f-string at all — pure template with a single placeholder)
html_template = r'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate">
<meta http-equiv="Pragma" content="no-cache">
<meta http-equiv="Expires" content="0">
<title>A股风格轮动盯盘仪表盘</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.7/dist/chart.umd.min.js"></script>
<script src="dashboard_data.js"></script>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: -apple-system, 'Microsoft YaHei', sans-serif; background: #0d1117; color: #c9d1d9; padding: 16px; }
.header { display: flex; align-items: center; justify-content: space-between; padding: 16px 24px; border-radius: 10px; margin-bottom: 16px; }
.header.GREEN { background: linear-gradient(135deg, #0d3320, #1a4a2e); border: 1px solid #2ecc71; }
.header.YELLOW { background: linear-gradient(135deg, #3d2e0f, #5a4518); border: 1px solid #f39c12; }
.header.ORANGE { background: linear-gradient(135deg, #3d1f0f, #5a2e18); border: 1px solid #e67e22; }
.header.RED { background: linear-gradient(135deg, #330d0d, #4a1e1e); border: 1px solid #e74c3c; }
.header h1 { font-size: 22px; }
.status-badge { font-size: 28px; font-weight: bold; padding: 8px 20px; border-radius: 8px; }
.status-badge.GREEN { color: #2ecc71; background: rgba(46,204,113,0.15); }
.status-badge.YELLOW { color: #f39c12; background: rgba(243,156,18,0.15); }
.status-badge.ORANGE { color: #e67e22; background: rgba(230,126,34,0.15); }
.status-badge.RED { color: #e74c3c; background: rgba(231,76,60,0.15); }
.grid { display: grid; gap: 16px; }
.grid-3 { grid-template-columns: repeat(3, 1fr); }
.grid-2 { grid-template-columns: repeat(2, 1fr); }
.grid-4 { grid-template-columns: repeat(4, 1fr); }
.card { background: #161b22; border: 1px solid #30363d; border-radius: 10px; padding: 16px; }
.card h3 { font-size: 14px; color: #8b949e; margin-bottom: 12px; text-transform: uppercase; letter-spacing: 1px; }
.kpi { text-align: center; }
.kpi .value { font-size: 28px; font-weight: bold; margin: 4px 0; }
.kpi .label { font-size: 11px; color: #8b949e; }
.kpi .sub { font-size: 12px; color: #8b949e; margin-top: 2px; }
.green { color: #2ecc71; } .red { color: #e74c3c; } .orange { color: #e67e22; } .yellow { color: #f39c12; }
.signal-row { display: flex; align-items: center; justify-content: space-between; padding: 8px 12px; border-bottom: 1px solid #21262d; }
.signal-row:last-child { border-bottom: none; }
.signal-dot { width: 12px; height: 12px; border-radius: 50%; display: inline-block; margin-right: 8px; }
.signal-dot.g { background: #2ecc71; box-shadow: 0 0 6px #2ecc71; }
.signal-dot.r { background: #e74c3c; box-shadow: 0 0 6px #e74c3c; }
.risk-tag { display: inline-block; padding: 4px 10px; margin: 4px; border-radius: 4px; font-size: 12px; background: rgba(231,76,60,0.15); color: #e74c3c; border: 1px solid rgba(231,76,60,0.3); }
.advice-box { padding: 12px 16px; border-radius: 8px; font-size: 14px; line-height: 1.6; }
.advice-box.GREEN { background: rgba(46,204,113,0.1); border-left: 3px solid #2ecc71; }
.advice-box.YELLOW { background: rgba(243,156,18,0.1); border-left: 3px solid #f39c12; }
.advice-box.ORANGE { background: rgba(230,126,34,0.1); border-left: 3px solid #e67e22; }
.advice-box.RED { background: rgba(231,76,60,0.1); border-left: 3px solid #e74c3c; }
.bar-row { display: flex; align-items: center; padding: 4px 0; font-size: 12px; }
.bar-row .name { width: 70px; text-align: right; margin-right: 10px; flex-shrink: 0; }
.bar-row .bar-wrap { flex: 1; height: 16px; background: #21262d; border-radius: 3px; position: relative; overflow: hidden; }
.bar-row .bar-fill { height: 100%; border-radius: 3px; position: absolute; }
.bar-row .bar-val { width: 55px; margin-left: 8px; text-align: right; flex-shrink: 0; }
canvas { max-height: 280px; }
.chart-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
@media (max-width: 900px) { .grid-3, .grid-4, .chart-grid { grid-template-columns: 1fr; } }
.stage-chain { font-size: 12px; }
.stage-row { display: flex; align-items: flex-start; padding: 5px 0; border-left: 2px solid #30363d; margin-left: 8px; padding-left: 12px; }
.stage-row.active { border-left-color: #e67e22; background: rgba(230,126,34,0.06); }
.stage-row.passed { border-left-color: #e74c3c; }
.stage-row .stage-num { width: 24px; font-weight: bold; flex-shrink: 0; }
.freshness { font-size: 11px; color: #8b949e; margin-top: 2px; }
.freshness.stale { color: #e67e22; }
.freshness.fresh { color: #2ecc71; }
.toast { position: fixed; top: 20px; right: 20px; padding: 12px 20px; border-radius: 8px; color: #fff; font-size: 14px; z-index: 9999; opacity: 0; transform: translateY(-20px); transition: all 0.3s; pointer-events: none; }
.toast.show { opacity: 1; transform: translateY(0); }
.toast.success { background: #2ecc71; }
.toast.error { background: #e74c3c; }
.toast.info { background: #3498db; }
</style>
</head>
<body>

<div class="header __OVERALL__" id="header">
  <div>
    <h1>📊 A股风格轮动盯盘仪表盘</h1>
    <div style="font-size:11px;color:#8b949e;margin-top:2px;">交易日收盘后更新 · 下次更新: 16:00</div>
    <div style="font-size:13px;color:#8b949e;margin-top:4px;" id="headerDate"></div>
  </div>
  <div>
    <div class="status-badge __OVERALL__" id="statusBadge">__STATUS__</div>
    <div style="text-align:right;font-size:12px;color:#8b949e;margin-top:4px;" id="headerCounts"></div>
  </div>
</div>

<!-- ROW 1: KPIs -->
<div class="grid grid-4" style="margin-bottom:16px;">
  <div class="card kpi">
    <div class="label">上证指数</div>
    <div class="value" id="kpiSH"></div>
    <div class="sub" id="kpiMA250"></div>
  </div>
  <div class="card kpi">
    <div class="label">当前回撤</div>
    <div class="value red" id="kpiDD"></div>
    <div class="sub">历史最大回撤 -52.3%</div>
  </div>
  <div class="card kpi">
    <div class="label">最强风格(60日)</div>
    <div class="value green" id="kpiBest"></div>
    <div class="sub" id="kpiBestV"></div>
  </div>
  <div class="card kpi">
    <div class="label">最弱风格(60日)</div>
    <div class="value red" id="kpiWorst"></div>
    <div class="sub" id="kpiWorstV"></div>
  </div>
</div>

<!-- ROW 2: Charts + Signals -->
<div class="grid grid-3" style="margin-bottom:16px;">
  <div class="card" style="grid-column:span 2;">
    <h3>上证指数 180日 + 均线系统</h3>
    <canvas id="chartSH"></canvas>
  </div>
  <div class="card">
    <h3>🎯 信号面板</h3>
    <div id="signalPanel"></div>
  </div>
</div>

<!-- ROW 3: YTD + Risk + Stage Chain -->
<div class="grid grid-3" style="margin-bottom:16px;">
  <div class="card">
    <h3>2026 YTD 收益率</h3>
    <div id="ytdBars"></div>
  </div>
  <div class="card">
    <h3>🔴 风险信号</h3>
    <div id="riskFlags"></div>
    <div style="margin-top:12px;">
      <h3>💡 操作建议</h3>
      <div class="advice-box __OVERALL__" id="adviceBox">__ADVICE__</div>
    </div>
  </div>
  <div class="card">
    <h3>📋 牛转熊七步信号链</h3>
    <div class="stage-chain" id="stageChain"></div>
  </div>
</div>

<!-- ROW 3.5: ETF 国家队 -->
<div class="grid grid-1" style="margin-bottom:16px;" id="etfSection">
  <div class="card">
    <h3>🏛️ 国家队ETF行动跟踪</h3>
    <div id="etfTable"></div>
  </div>
</div>

<!-- ROW 4: Charts -->
<div class="chart-grid" style="margin-bottom:16px;">
  <div class="card">
    <h3>价值/成长比率 (360日, 1=起点)</h3>
    <canvas id="chartVG"></canvas>
  </div>
  <div class="card">
    <h3>大小盘轮动 (2年, 沪深300/中证1000)</h3>
    <canvas id="chartLS"></canvas>
  </div>
</div>

<!-- ROW 5: Benchmark Table + Rolling Returns -->
<div class="grid grid-2" style="margin-bottom:16px;">
  <div class="card">
    <h3>核心指数一览</h3>
    <div id="benchTable"></div>
  </div>
  <div class="card">
    <h3>风格近60日滚动20日收益 (%)</h3>
    <canvas id="chartRoll"></canvas>
  </div>
</div>

<script>
// ===== POPULATE HEADER =====
document.getElementById('headerDate').textContent = '数据日期: ' + DATA.date + ' | 上证指数: ' + DATA.sh_index.toFixed(0);
document.getElementById('statusBadge').textContent = DATA.overall_label;
document.getElementById('headerCounts').textContent = '破位计数: ' + DATA.bdd_count + ' | 风险信号: ' + DATA.rf_count;

// ===== KPIs =====
document.getElementById('kpiSH').textContent = DATA.sh_index.toFixed(0);
document.getElementById('kpiMA250').textContent = '距年线 ' + ((DATA.sh_index/DATA.ma250-1)*100).toFixed(1) + '%';
document.getElementById('kpiDD').textContent = (DATA.drawdown*100).toFixed(1) + '%';
document.getElementById('kpiBest').textContent = DATA.best_60;
document.getElementById('kpiBestV').textContent = (DATA.best_60_val*100).toFixed(1) + '%';
document.getElementById('kpiWorst').textContent = DATA.worst_60;
document.getElementById('kpiWorstV').textContent = (DATA.worst_60_val*100).toFixed(1) + '%';
document.getElementById('adviceBox').textContent = DATA.overall_desc;

// ===== SIGNAL PANEL =====
(function() {
  var signals = [
    ['上证>MA250(年线)', DATA.above_ma250, DATA.sh_index.toFixed(0)+' vs '+DATA.ma250.toFixed(0)],
    ['上证>MA120(半年线)', DATA.above_ma120, DATA.sh_index.toFixed(0)+' vs '+DATA.ma120.toFixed(0)],
    ['上证>MA60(季线)', DATA.above_ma60, DATA.sh_index.toFixed(0)+' vs '+DATA.ma60.toFixed(0)],
    ['上证>MA20(月线)', DATA.above_ma20, DATA.sh_index.toFixed(0)+' vs '+DATA.ma20.toFixed(0)],
    ['MA60>MA120>MA250', DATA.ma_bull, '未形成死叉' + (DATA.ma_bull?' ✓':' ✗')],
    ['回撤<15%', Math.abs(DATA.drawdown)<0.15, '当前'+(DATA.drawdown*100).toFixed(1)+'%'],
  ];
  var html = '';
  for (var i = 0; i < signals.length; i++) {
    var s = signals[i], name = s[0], ok = s[1], detail = s[2];
    html += '<div class="signal-row">' +
      '<span><span class="signal-dot '+(ok?'g':'r')+'"></span>'+name+'</span>' +
      '<span style="font-size:11px;color:'+(ok?'#2ecc71':'#e74c3c')+'">'+detail+'</span>' +
    '</div>';
  }
  document.getElementById('signalPanel').innerHTML = html;
})();

// ===== YTD BARS =====
(function() {
  var ytd = DATA.ytd;
  var order = ['大盘价值','大盘成长','中盘价值','中盘成长','小盘价值','小盘成长',
                '上证50','沪深300','中证500','中证1000','创业板指','中证红利'];
  var html = '';
  for (var i = 0; i < order.length; i++) {
    var name = order[i], v = ytd[name]*100, w = Math.min(Math.abs(v)*3, 100);
    html += '<div class="bar-row">' +
      '<span class="name">'+name+'</span>' +
      '<span class="bar-wrap"><span class="bar-fill" style="width:'+w+'%;background:'+(v>=0?'#2ecc71':'#e74c3c')+'"></span></span>' +
      '<span class="bar-val" style="color:'+(v>=0?'#2ecc71':'#e74c3c')+'">'+(v>=0?'+':'')+v.toFixed(1)+'%</span>' +
    '</div>';
  }
  document.getElementById('ytdBars').innerHTML = html;
})();

// ===== RISK FLAGS =====
(function() {
  var html = '';
  if (DATA.risk_flags.length === 0) {
    html = '<div style="color:#2ecc71;padding:8px;">✅ 无显著风险信号</div>';
  } else {
    for (var i = 0; i < DATA.risk_flags.length; i++) {
      html += '<span class="risk-tag">'+DATA.risk_flags[i]+'</span>';
    }
  }
  document.getElementById('riskFlags').innerHTML = html;
})();

// ===== STAGE CHAIN =====
(function() {
  var stages = [
    [0, '牛市健康', '未死叉,成长主导', DATA.ma_bull],
    [1, '⚠️ 过热', '距MA250>25%', Math.abs(DATA.sh_index/DATA.ma250-1)>0.25],
    [2, '🔶 拐头', '跌破MA20', !DATA.above_ma20],
    [3, '🔴 中期转弱', '跌破MA60', !DATA.above_ma60],
    [4, '⬛ 确认熊市', '跌破MA120', !DATA.above_ma120],
    [5, '💀 加速', '跌破MA250', !DATA.above_ma250],
    [6, '💎 底部区域', '距MA250<-15%', DATA.sh_index/DATA.ma250-1 < -0.15],
  ];
  var highestTriggered = -1;
  for (var i = stages.length - 1; i >= 0; i--) {
    if (stages[i][3]) { highestTriggered = i; break; }
  }
  var html = '';
  for (var i = 0; i < stages.length; i++) {
    var num = stages[i][0], title = stages[i][1], desc = stages[i][2], triggered = stages[i][3];
    var cls = '', note = '—';
    if (triggered) { cls = 'passed'; note = '✅ 已触发'; }
    else if (num === highestTriggered + 1) { cls = 'active'; note = '⚠️ 当前关注'; }
    html += '<div class="stage-row '+cls+'">' +
      '<span class="stage-num" style="color:'+(triggered?'#e74c3c':(cls==='active'?'#e67e22':'#8b949e'))+'">'+num+'</span>' +
      '<span style="flex:1"><b>'+title+'</b><br><span style="color:#8b949e;font-size:10px;">'+desc+' '+note+'</span></span>' +
    '</div>';
  }
  document.getElementById('stageChain').innerHTML = html;
})();

// ===== BENCH TABLE =====
(function() {
  var bm = DATA.benchmarks, ytd = DATA.ytd;
  var html = '<table style="width:100%;font-size:12px;border-collapse:collapse;">';
  html += '<tr style="color:#8b949e;"><th style="text-align:left;padding:4px;">指数</th><th style="text-align:right;padding:4px;">点位</th><th style="text-align:right;padding:4px;">YTD</th></tr>';
  var keys = Object.keys(bm);
  for (var i = 0; i < keys.length; i++) {
    var name = keys[i], val = bm[name], y = (ytd[name]||0)*100;
    html += '<tr style="border-top:1px solid #21262d;">' +
      '<td style="padding:4px;">'+name+'</td>' +
      '<td style="text-align:right;padding:4px;">'+val+'</td>' +
      '<td style="text-align:right;padding:4px;color:'+(y>=0?'#2ecc71':'#e74c3c')+'">'+(y>=0?'+':'')+y.toFixed(1)+'%</td>' +
    '</tr>';
  }
  html += '</table>';
  document.getElementById('benchTable').innerHTML = html;
})();

// ===== ETF 国家队行动跟踪 =====
(function() {
  var ef = DATA.etf_flow;
  if (!ef || !ef.daily || ef.daily.length === 0) {
    document.getElementById('etfSection').style.display = 'none';
    return;
  }
  var dates = ef.dates || [];
  var daily = ef.daily;
  var summary = ef.summary || {};
  
  // Build table header
  var html = '<div style="margin-bottom:2px;font-size:12px;color:#8b949e;">🏛️ 国家队ETF份额变化 (亿份)</div>';
  html += '<table style="width:100%;font-size:11px;border-collapse:collapse;">';
  html += '<tr style="color:#8b949e;font-size:10px;">';
  html += '<th style="text-align:left;padding:2px 4px;">ETF</th>';
  for (var di = 0; di < dates.length; di++) {
    var ds = dates[di]; var label = ds.slice(5); // MM-DD
    html += '<th style="text-align:right;padding:2px 3px;">'+label+'</th>';
  }
  html += '<th style="text-align:right;padding:2px 3px;color:#58a6ff;">3日</th>';
  html += '<th style="text-align:right;padding:2px 3px;color:#58a6ff;">5日</th>';
  html += '<th style="text-align:right;padding:2px 3px;color:#58a6ff;">10日</th>';
  html += '</tr>';
  
  // ETF rows
  for (var i = 0; i < daily.length; i++) {
    var r = daily[i];
    html += '<tr style="border-top:1px solid #21262d;">';
    html += '<td style="padding:2px 4px;">'+r.name+'</td>';
    for (var di = 0; di < dates.length; di++) {
      var ds = dates[di]; var v = r[ds] || 0;
      var color = v > 2 ? '#2ecc71' : (v < -2 ? '#e74c3c' : '#c9d1d9');
      html += '<td style="text-align:right;padding:2px 3px;color:'+color+'">'+(v>=0?'+':'')+v.toFixed(1)+'</td>';
    }
    html += '<td style="text-align:right;padding:2px 3px;color:'+(r.d3>=0?'#2ecc71':'#e74c3c')+'">'+(r.d3>=0?'+':'')+r.d3.toFixed(1)+'</td>';
    html += '<td style="text-align:right;padding:2px 3px;color:'+(r.d5>=0?'#2ecc71':'#e74c3c')+'">'+(r.d5>=0?'+':'')+r.d5.toFixed(1)+'</td>';
    html += '<td style="text-align:right;padding:2px 3px;color:'+(r.d10>=0?'#2ecc71':'#e74c3c')+'">'+(r.d10>=0?'+':'')+r.d10.toFixed(1)+'</td>';
    html += '</tr>';
  }
  
  // Summary row
  html += '<tr style="border-top:2px solid #30363d;font-weight:bold;">';
  html += '<td style="padding:2px 4px;">合计</td>';
  for (var di = 0; di < dates.length; di++) {
    var ds = dates[di]; var sv = summary[ds] || 0;
    var color = sv > 10 ? '#2ecc71' : (sv < -10 ? '#e74c3c' : '#c9d1d9');
    html += '<td style="text-align:right;padding:2px 3px;color:'+color+'">'+(sv>=0?'+':'')+sv.toFixed(1)+'</td>';
  }
  html += '<td style="text-align:right;padding:2px 3px;color:'+(summary.d3>=0?'#2ecc71':'#e74c3c')+'">'+(summary.d3>=0?'+':'')+(summary.d3||0).toFixed(1)+'</td>';
  html += '<td style="text-align:right;padding:2px 3px;color:'+(summary.d5>=0?'#2ecc71':'#e74c3c')+'">'+(summary.d5>=0?'+':'')+(summary.d5||0).toFixed(1)+'</td>';
  html += '<td style="text-align:right;padding:2px 3px;color:'+(summary.d10>=0?'#2ecc71':'#e74c3c')+'">'+(summary.d10>=0?'+':'')+(summary.d10||0).toFixed(1)+'</td>';
  html += '</tr>';
  html += '</table>';
  
  // Alert banner
  if (ef.alert) {
    html += '<div style="margin-top:6px;padding:4px 8px;background:#442222;border-left:3px solid #e74c3c;font-size:11px;color:#e74c3c;">⚠ '+ef.alert_msg+'</div>';
  }
  
  document.getElementById('etfTable').innerHTML = html;
})();

// ===== CHARTS =====
// ===== AUTO-REFRESH & FRESHNESS CHECK =====
var API_BASE = (window.location.port === '8765') ? '' : '';
var IS_LOCAL_SERVER = (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1');

// Show data freshness
(function() {
  var el = document.createElement('div');
  el.className = 'freshness';
  el.id = 'freshness';
  el.textContent = '📅 数据日期: ' + DATA.date + ' | 刷新时间: ' + new Date().toLocaleString('zh-CN');
  document.getElementById('headerDate').parentNode.appendChild(el);
})();

// Toast notification system
function showToast(msg, type) {
  type = type || 'info';
  var t = document.getElementById('toast');
  if (!t) {
    t = document.createElement('div');
    t.id = 'toast';
    t.className = 'toast';
    document.body.appendChild(t);
  }
  t.textContent = msg;
  t.className = 'toast ' + type + ' show';
  setTimeout(function() { t.className = 'toast'; }, 3000);
}

// Auto-check freshness on load (only on local server)
if (IS_LOCAL_SERVER) {
  fetch(API_BASE + '/api/status')
    .then(function(r) { return r.json(); })
    .then(function(s) {
      if (s.is_stale && s.data_exists) {
        var el = document.getElementById('freshness');
        el.className = 'freshness stale';
        el.textContent += ' ⚠️ 数据已过期 (' + s.hours_since_update + '小时前)';
        showToast('⚠️ 数据已超过24小时未更新，建议点击刷新按钮', 'info');
      }
    })
    .catch(function() { /* not on local server, ignore */ });
}

// Keyboard shortcut: Ctrl+R or F5 will also trigger data refresh if on local server
if (IS_LOCAL_SERVER) {
  document.addEventListener('keydown', function(e) {
    if ((e.ctrlKey && e.key === 'r') || e.key === 'F5') {
      // Let browser handle normal reload - it will load fresh files from server
    }
  });
}

// ===== VERSION POLLING (auto-detect new deployments) =====
var BUILD_TIME = '__BUILD_TIME__';
(function() {
  var freshnessEl = document.getElementById('freshness');
  if (freshnessEl && BUILD_TIME && BUILD_TIME !== '__BUILD_TIME__') {
    freshnessEl.textContent = freshnessEl.textContent + ' | 构建: ' + BUILD_TIME;
  }

  var initialVersion = localStorage.getItem('last_version');

  function checkVersion() {
    fetch('version.json?t=' + Date.now(), { cache: 'no-store' })
      .then(function(r) { return r.json(); })
      .then(function(v) {
        // First visit: just store version, don't reload
        if (!initialVersion) {
          initialVersion = v.version;
          localStorage.setItem('last_version', v.version);
          return;
        }
        // Version changed → new deployment → reload
        if (v.version !== localStorage.getItem('last_version')) {
          localStorage.setItem('last_version', v.version);
          showToast('🆕 数据已更新，刷新中...', 'success');
          setTimeout(function() { location.reload(true); }, 1000);
        }
      })
      .catch(function() {});
  }

  checkVersion();
  setInterval(checkVersion, 5 * 60 * 1000);
})();

Chart.defaults.color = '#8b949e';
Chart.defaults.borderColor = '#30363d';

// SH Index
new Chart(document.getElementById('chartSH'), {
  type: 'line',
  data: {
    labels: DATA.ts_180,
    datasets: [
      { label: '上证指数', data: DATA.sz_180, borderColor: '#58a6ff', borderWidth: 1.5, pointRadius: 0, tension: 0.1 },
      { label: 'MA250='+DATA.ma250.toFixed(0), data: Array(180).fill(DATA.ma250), borderColor: '#2ecc71', borderWidth: 1, borderDash: [6,3], pointRadius: 0 },
      { label: 'MA120='+DATA.ma120.toFixed(0), data: Array(180).fill(DATA.ma120), borderColor: '#3498db', borderWidth: 1, borderDash: [6,3], pointRadius: 0 },
      { label: 'MA60='+DATA.ma60.toFixed(0), data: Array(180).fill(DATA.ma60), borderColor: '#e74c3c', borderWidth: 1, borderDash: [6,3], pointRadius: 0 },
    ]
  },
  options: { responsive: true, plugins: { legend: { labels: { boxWidth: 12, font: { size: 10 } } } } }
});

// VG Ratio
var vgColors = { '大盘': '#e74c3c', '中盘': '#3498db', '小盘': '#2ecc71' };
var vgKeys = Object.keys(DATA.vg_data);
var vgDatasets = [];
for (var i = 0; i < vgKeys.length; i++) {
  var k = vgKeys[i];
  vgDatasets.push({ label: k, data: DATA.vg_data[k].vals, borderColor: vgColors[k], borderWidth: 1.2, pointRadius: 0, tension: 0.1 });
}
new Chart(document.getElementById('chartVG'), {
  type: 'line', data: { labels: DATA.vg_data['大盘'].ts, datasets: vgDatasets },
  options: { responsive: true, plugins: { legend: { labels: { boxWidth: 12, font: { size: 10 } } } } }
});

// Size Rotation
new Chart(document.getElementById('chartLS'), {
  type: 'line',
  data: { labels: DATA.ls_data.ts, datasets: [{ label: '沪深300/中证1000', data: DATA.ls_data.vals, borderColor: '#8e44ad', borderWidth: 1.2, pointRadius: 0 }] },
  options: { responsive: true, plugins: { legend: { display: false } } }
});

// Rolling Returns
var rollColors = { '大盘价值': '#c0392b', '大盘成长': '#e74c3c', '中盘价值': '#2471a3', '中盘成长': '#3498db', '小盘价值': '#1e8449', '小盘成长': '#2ecc71' };
var rollKeys = Object.keys(DATA.roll_data);
var rollDatasets = [];
for (var i = 0; i < rollKeys.length; i++) {
  var k = rollKeys[i];
  rollDatasets.push({ label: k, data: DATA.roll_data[k].vals, borderColor: rollColors[k], borderWidth: 1, pointRadius: 0, tension: 0.1 });
}
new Chart(document.getElementById('chartRoll'), {
  type: 'line', data: { labels: DATA.roll_data[rollKeys[0]].ts, datasets: rollDatasets },
  options: { responsive: true, plugins: { legend: { labels: { boxWidth: 10, font: { size: 9 } } } } }
});
</script>

</body>
</html>'''

# Replace placeholders
from datetime import datetime
overall = data['overall']
build_time = datetime.now().strftime('%m-%d %H:%M')
html = html_template.replace('__OVERALL__', overall)
html = html.replace('__STATUS__', data['overall_label'])
html = html.replace('__ADVICE__', data['overall_desc'])
html = html.replace('__BUILD_TIME__', build_time)

with open(os.path.join(BASE, 'dashboard.html'), 'w', encoding='utf-8') as f:
    f.write(html)

print(f"HTML written: dashboard.html ({len(html)} chars)")
