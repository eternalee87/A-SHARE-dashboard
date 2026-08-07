# -*- coding: utf-8 -*-
"""分析 NDX 在连续上涨一周后的短期动量效应"""
import pandas as pd
import numpy as np

# 读取 NDX 数据
df = pd.read_csv(r'ndx_dca\data\ndx_data.csv', parse_dates=['date'])
df = df.set_index('date').sort_index()
df['ret'] = df['close'].pct_change()

print(f"数据范围: {df.index[0].strftime('%Y-%m-%d')} ~ {df.index[-1].strftime('%Y-%m-%d')}")
print(f"总交易日: {len(df)}")

# ===== 定义条件 =====
# "连续上涨一周" = 过去5个交易日每天都上涨（严格定义）
df['up_day'] = (df['ret'] > 0).astype(int)
df['up_streak'] = 0
streak = 0
for i in range(len(df)):
    if df['up_day'].iloc[i] == 1:
        streak += 1
    else:
        streak = 0
    df.iloc[i, df.columns.get_loc('up_streak')] = streak

# 标记：过去5天全部上涨（连续5阳）
df['signal_strict'] = (df['up_streak'] >= 5).astype(int)

# 宽松定义：过去5天累计收益 > 0
df['ret_5d'] = df['close'].pct_change(5)
df['signal_loose'] = (df['ret_5d'] > 0).astype(int)

# ===== 计算前向收益 =====
for horizon, days in [('1w', 5), ('2w', 10), ('1m', 21)]:
    df[f'fwd_{horizon}'] = df['close'].shift(-days) / df['close'] - 1

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
        
        win_mask = fwd_rets > 0
        loss_mask = fwd_rets < 0
        
        n_win = win_mask.sum()
        n_loss = loss_mask.sum()
        win_rate = n_win / n * 100 if n > 0 else 0
        
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
        
        # 分布
        pctiles = [10, 25, 50, 75, 90]
        pct_vals = np.percentile(fwd_rets.dropna() * 100, pctiles)
        print(f"     分位数: " + " | ".join([f"P{p}={v:+.2f}%" for p, v in zip(pctiles, pct_vals)]))

# ===== 运行分析 =====
analyze('signal_strict', '连续5个交易日全部上涨（严格定义）')
analyze('signal_loose', '过去5个交易日累计收益 > 0（宽松定义）')

# ===== 额外：不同上涨强度下的表现 =====
print(f"\n{'='*60}")
print(f"📊 按过去一周涨幅分组分析")
print(f"{'='*60}")

bins = [(-0.10, -0.02, '大跌(>-2%)'), (-0.02, 0, '小跌(-2%~0)'), 
        (0, 0.02, '小涨(0~2%)'), (0.02, 0.05, '中涨(2~5%)'), 
        (0.05, 0.10, '大涨(5~10%)'), (0.10, 1.0, '暴涨(>10%)')]

for low, high, label in bins:
    mask = (df['ret_5d'] > low) & (df['ret_5d'] <= high)
    n = mask.sum()
    if n < 10:
        continue
    
    fwd_1m = df.loc[mask, 'fwd_1m'].dropna() * 100
    win_rate = (fwd_1m > 0).sum() / len(fwd_1m) * 100
    avg_ret = fwd_1m.mean()
    
    print(f"\n  过去一周{label}: n={n}")
    print(f"    未来1个月: 平均 {avg_ret:+.2f}%, 胜率 {win_rate:.1f}%")

print("\n✅ 分析完成")
