import sys,io,os,json
sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding='utf-8')

import pandas as pd,numpy as np

def to_py(v):
    if isinstance(v,(np.integer,)): return int(v)
    if isinstance(v,(np.floating,np.float64)): return float(v)
    if isinstance(v,(np.bool_,)): return bool(v)
    return v

BASE=os.path.dirname(os.path.abspath(__file__))
df=pd.read_csv(os.path.join(BASE,'data','style_indices_v2.csv'),index_col=0,parse_dates=True)
STYLES=['大盘价值','大盘成长','中盘价值','中盘成长','小盘价值','小盘成长']
BENCHMARKS=['上证指数','沪深300','上证50','中证500','中证1000','创业板指','中证红利']

sz=df['上证指数']; sz_cur=sz.iloc[-1]
sz_ma20=sz.iloc[-20:].mean(); sz_ma60=sz.iloc[-60:].mean()
sz_ma120=sz.iloc[-120:].mean(); sz_ma250=sz.iloc[-250:].mean()
sz_dd=(sz/sz.expanding().max()-1).iloc[-1]

# 180d for chart
r180=df.iloc[-180:]
ts_180=[str(d)[:10] for d in r180.index]
sz_180=r180['上证指数'].tolist()

# YTD
ytd={}
for col in STYLES+['上证50','沪深300','中证500','中证1000','创业板指','中证红利']:
    s=df[col];m=s.index>='2026-01-01';ytd[col]=round(s[m].iloc[-1]/s[m].iloc[0]-1,4)

# Value/Growth ratios (360d)
vg_data={}
for prefix in ['大盘','中盘','小盘']:
    r=df[f'{prefix}价值']/df[f'{prefix}成长']
    r=r.iloc[-360:]
    base=r.iloc[0]
    vg_data[prefix]={
        'ts':[str(d)[:10] for d in r.index],
        'vals':[round(v/base,4) for v in r.values]
    }

# Size rotation (720d)
ls_ratio=df['沪深300']/df['中证1000']
ls=ls_ratio.iloc[-720:]
ls_base=ls.iloc[0]
ls_data={'ts':[str(d)[:10] for d in ls.index],'vals':[round(v/ls_base,4) for v in ls.values]}

# Rolling 20d (60d)
r60=df.iloc[-60:]
roll_data={}
for st in STYLES:
    rr=r60[st].pct_change(20)*100
    valid=rr.dropna()
    roll_data[st]={'ts':[str(d)[:10] for d in valid.index],'vals':[round(v,2) for v in valid.values]}

# Signals
lv_vs_lg=round(r180['大盘价值'].iloc[-1]/r180['大盘价值'].iloc[-60]-1-(r180['大盘成长'].iloc[-1]/r180['大盘成长'].iloc[-60]-1),4)
rets_60={st:round(r180[st].iloc[-1]/r180[st].iloc[-60]-1,4) for st in STYLES}
rets_20={st:round(r180[st].iloc[-1]/r180[st].iloc[-20]-1,4) for st in STYLES}
best_60=max(rets_60,key=rets_60.get); worst_60=min(rets_60,key=rets_60.get)

# Risk flags
risk_flags=[]
if abs(sz_dd)>0.15: risk_flags.append(f"回撤{abs(sz_dd):.0%}超过15%阈值")
if sz_cur<sz_ma60: risk_flags.append("上证跌破MA60(季线)")
if sz_cur<sz_ma120: risk_flags.append("上证跌破MA120(半年线)")
if sz_cur<sz_ma250: risk_flags.append("上证跌破MA250(年线)")
if lv_vs_lg>0.05: risk_flags.append(f"大盘价值持续跑赢成长({lv_vs_lg:+.1%})→防御模式")

# Breakdown count
bd=0
if sz_cur<sz_ma60: bd+=1
if sz_cur<sz_ma120: bd+=2
if sz_cur<sz_ma250: bd+=3
if not (sz_ma60>sz_ma120>sz_ma250): bd+=1
if abs(sz_dd)>0.15: bd+=2
if abs(sz_dd)>0.25: bd+=2
if lv_vs_lg>0.05: bd+=1
rf_count=len(risk_flags)

if bd<=1 and rf_count<=1: overall='GREEN'
elif bd<=3 and rf_count<=2: overall='YELLOW'
elif bd<=5 or sz_cur>=sz_ma250: overall='ORANGE'
else: overall='RED'

status_labels={'GREEN':'牛市健康','YELLOW':'牛市调整','ORANGE':'中期走弱','RED':'熊市特征'}
status_desc={
    'GREEN':'维持牛市思维,持有强势风格,可适度追涨',
    'YELLOW':'牛市调整中,控制仓位60-80%,关注MA120支撑,减仓弱风格',
    'ORANGE':'仓位降至30-50%,转防御(大盘价值),密切关注年线得失',
    'RED':'仓位<30%或空仓,仅保留防御底仓,等待底部信号'
}

# Latest values
last=df.iloc[-1]

data={
    'date':str(df.index[-1])[:10],
    'sh_index':round(sz_cur,0),
    'ma20':round(sz_ma20,0),'ma60':round(sz_ma60,0),'ma120':round(sz_ma120,0),'ma250':round(sz_ma250,0),
    'drawdown':round(sz_dd,4),
    'above_ma250':to_py(sz_cur>sz_ma250),'above_ma120':to_py(sz_cur>sz_ma120),'above_ma60':to_py(sz_cur>sz_ma60),
    'above_ma20':to_py(sz_cur>sz_ma20),'ma_bull':to_py(sz_ma60>sz_ma120>sz_ma250),
    'bdd_count':bd,'risk_flags':risk_flags,'rf_count':rf_count,
    'overall':overall,'overall_label':status_labels[overall],'overall_desc':status_desc[overall],
    'best_60':best_60,'worst_60':worst_60,'best_60_val':rets_60[best_60],'worst_60_val':rets_60[worst_60],
    'lv_vs_lg':lv_vs_lg,
    'benchmarks':{k:round(last[k],0) for k in BENCHMARKS},
    'ytd':ytd,'vg_data':vg_data,'ls_data':ls_data,'roll_data':roll_data,
    'ts_180':ts_180,'sz_180':sz_180,'rets_20':rets_20,'rets_60':rets_60
}

with open(os.path.join(BASE,'dashboard_data.json'),'w',encoding='utf-8') as f:
    json.dump(data,f,ensure_ascii=False,indent=1)
print("JSON data generated: dashboard_data.json")
