# -*- coding: utf-8 -*-
"""分析 U4_M153 策略在连续上涨一周后的短期表现"""
import pandas as pd
import numpy as np

# 读取策略日收益
df = pd.read_excel(r'strategy_analysis\data\groupby_daily_return.xlsx')
df['date'] = pd.to_datetime(df['str_date'])
df = df.sort_values('date').reset_index(drop=True)
df['ret'] = df['daily_return']

print(f"数据范围: {df['date'].iloc[0].strftime('%Y-%m-%d')} ~ {df['date'].iloc[-1].strftime('%Y-%m-%d')}")
print(f"总交易日: {len(df)}")

# 策略累计净值
df['nav'] = (1 + df['ret']).cumprod()

# ===== 定义信号 =====
# 严格定义：连续5个交易日全部上涨
df['up'] = (df['ret'] > 0).astype(int)
streak = 0
streaks = []
for i, up in enumerate(df['up']):
    streak = streak + 1 if up else 0
    streaks.append(streak)
df['up_streak'] = streaks
df['signal_strict'] = (df['up_streak'] >= 5).astype(int)

# 宽松定义：过去5天累计收益 > 0
df['ret_5d'] = df['nav'] / df['nav'].shift(5) - 1
df['signal_loose'] = (df['ret_5d'] > 0).astype(int)

# ===== 前向收益（从收盘到收盘）=====
for horizon, days in [('1w', 5), ('2w', 10), ('1m', 21)]:
    df[f'fwd_{horizon}'] = df['nav'].shift(-days) / df['nav'] - 1

# 从 df['ret'] 也可以直接做累计：
def fwd_return(i, days):
    """从第i天收盘到第i+days天收盘的累计收益"""
    end = min(i + days, len(df) - 1)
    if end <= i:
        return np.nan
    return df['nav'].iloc[end] / df['nav'].iloc[i] - 1

# ===== 分析函数 =====
def analyze(signal_col, signal_name):
    print(f"\n{'='*60}")
    print(f"📊 条件: {signal_name}")
    print(f"{'='*60}")
    
    mask = df[signal_col] == 1
    n_signals = mask.sum()
    n_total = len(df)
    print(f"信号出现次数: {n_signals} / {n_total} ({n_signals/n_total*100:.1f}%)")
    
    for horizon, days in [('1w', 5), ('2w', 10), ('1m', 21)]:
        fwd_col = f'fwd_{horizon}'
        fwd_rets = df.loc[mask, fwd_col].dropna()
        n = len(fwd_rets)
        
        if n == 0:
            continue
        
        win_mask = fwd_rets > 0
        loss_mask = fwd_rets < 0
        n_win = win_mask.sum()
        n_loss = loss_mask.sum()
        win_rate = n_win / n * 100
        
        avg_win = fwd_rets[win_mask].mean() * 100 if n_win > 0 else 0
        avg_loss = fwd_rets[loss_mask].mean() * 100 if n_loss > 0 else 0
        payoff_ratio = abs(avg_win / avg_loss) if avg_loss != 0 else float('inf')
        
        avg_return = fwd_rets.mean() * 100
        median_return = fwd_rets.median() * 100
        
        # 无条件对比
        all_fwd = df[fwd_col].dropna()
        all_avg = all_fwd.mean() * 100
        all_win_rate = (all_fwd > 0).sum() / len(all_fwd) * 100
        
        print(f"\n  📅 未来 {horizon} ({days}个交易日), n={n}")
        print(f"     胜率: {win_rate:.1f}%  (无条件胜率: {all_win_rate:.1f}%)")
        print(f"     平均收益: {avg_return:+.2f}%  (无条件: {all_avg:+.2f}%)")
        print(f"     中位收益: {median_return:+.2f}%")
        print(f"     平均盈利: {avg_win:+.2f}%  |  平均亏损: {avg_loss:+.2f}%")
        print(f"     盈亏比: {payoff_ratio:.2f}")
        
        pctiles = [10, 25, 50, 75, 90]
        pct_vals = np.percentile(fwd_rets.dropna() * 100, pctiles)
        print(f"     分位数: " + " | ".join([f"P{p}={v:+.2f}%" for p, v in zip(pctiles, pct_vals)]))

# ===== 运行 =====
analyze('signal_strict', '策略连续5个交易日全部上涨（严格定义）')
analyze('signal_loose', '策略过去5个交易日累计收益 > 0（宽松定义）')

# ===== 按涨幅分组 =====
print(f"\n{'='*60}")
print(f"📊 按策略过去一周涨幅分组分析")
print(f"{'='*60}")

bins = [(-0.05, -0.02, '大跌(>-2%)'), (-0.02, 0, '小跌(-2%~0)'), 
        (0, 0.005, '微涨(0~0.5%)'), (0.005, 0.01, '小涨(0.5~1%)'),
        (0.01, 0.02, '中涨(1~2%)'), (0.02, 0.03, '大涨(2~3%)'),
        (0.03, 1.0, '暴涨(>3%)')]

for low, high, label in bins:
    mask = (df['ret_5d'] > low) & (df['ret_5d'] <= high)
    n = mask.sum()
    if n < 5:
        continue
    
    fwd_1m = df.loc[mask, 'fwd_1m'].dropna() * 100
    win_rate = (fwd_1m > 0).sum() / len(fwd_1m) * 100
    avg_ret = fwd_1m.mean()
    
    print(f"\n  过去一周{label}: n={n}")
    print(f"    未来1个月: 平均 {avg_ret:+.2f}%, 胜率 {win_rate:.1f}%")

# ===== 关键补充：连续阳线后不同持有期的详细分布 =====
print(f"\n{'='*60}")
print(f"📊 策略自身特性速览")
print(f"{'='*60}")
print(f"日均收益: {df['ret'].mean()*100:+.3f}%")
print(f"日胜率: {(df['ret']>0).sum()/len(df)*100:.1f}%")
print(f"年化波动: {df['ret'].std()*np.sqrt(252)*100:.1f}%")
print(f"最大回撤: {((df['nav']/df['nav'].cummax()-1).min())*100:.2f}%")

# 策略连续上涨的持续性
print(f"\n📊 连阳分布:")
streak_dist = df['up_streak'].value_counts().sort_index()
for k in [1,2,3,4,5,6,7,8]:
    cnt = streak_dist.get(k, 0)
    print(f"  连阳{k}天: {cnt}次")

print("\n✅ 分析完成")
