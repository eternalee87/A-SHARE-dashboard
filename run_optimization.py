"""
降本增效优化 + 市场环境稳健性验证

测试：
1. 波动率分位数调整仓位 (低波动时多买)
2. 不同标的指数 (沪深300, 上证50, 中证500, 中证1000)
3. 不同市场环境 (2010-2014熊市, 2014-2015牛市+崩盘, 2016-2018慢牛, 2019-2021牛市, 2022-2026震荡)
"""
import sys, os
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, 'lib')
os.environ['MPLCONFIGDIR'] = os.environ.get('TEMP', '.') + '/matplotlib'

import numpy as np
import pandas as pd
import json
import time

from universa_backtest.strategy import (
    DeepOTMPutStrategy, StrategyParams, StrikeMethod, PositionSizing
)
from universa_backtest.analysis import (
    compute_performance_metrics, compute_trade_analysis
)


def load_data(index_name='沪深300'):
    df = pd.read_csv('data/style_indices_v2.csv', index_col=0, parse_dates=True)
    return df[index_name].dropna()


def quick_test(price_data, **kwargs):
    """Run single test and return key metrics."""
    params = StrategyParams(
        delta=kwargs.get('delta', 0.05),
        moneyness=kwargs.get('moneyness', 0.85),
        strike_method=kwargs.get('strike_method', StrikeMethod.FIXED_DELTA),
        tenor_days=kwargs.get('tenor_days', 30),
        roll_frequency_days=kwargs.get('roll_frequency_days', 21),
        sizing_method=kwargs.get('sizing_method', PositionSizing.FIXED_PREMIUM),
        premium_budget_pct=kwargs.get('premium_budget_pct', 0.01),
        vol_window=kwargs.get('vol_window', 20),
        vol_percentile_threshold=kwargs.get('vol_percentile_threshold', 0.25),
        vol_scale_multiplier=kwargs.get('vol_scale_multiplier', 2.0),
        risk_free_rate=0.03,
    )
    strategy = DeepOTMPutStrategy(params)
    results = strategy.run(price_data)
    trades = strategy.get_trade_log()
    metrics = compute_performance_metrics(results)
    ta = compute_trade_analysis(trades)
    return {
        **kwargs,
        'spot_cagr': metrics['spot_cagr'],
        'nav_cagr': metrics['nav_cagr'],
        'cagr_diff': metrics['nav_cagr'] - metrics['spot_cagr'],
        'dd_reduction_pct': metrics['dd_reduction_pct'],
        'spot_max_dd': metrics['spot_max_drawdown'],
        'nav_max_dd': metrics['nav_max_drawdown'],
        'annualized_premium_pct': metrics['annualized_premium_pct'],
        'annualized_net_cost_pct': metrics['annualized_net_cost_pct'],
        'total_pnl': metrics['total_hedge_pnl'],
        'win_rate': ta['win_rate'],
        'max_consecutive_losses': ta['max_consecutive_losses'],
        'payoff_cost_ratio': ta['payoff_to_cost_ratio'],
        'nav_sharpe': metrics['nav_sharpe'],
        'nav_calmar': metrics['nav_calmar'],
    }


def main():
    t0 = time.time()
    
    # Load all indices
    df = pd.read_csv('data/style_indices_v2.csv', index_col=0, parse_dates=True)
    
    # ====== PART 1: 降本增效优化 ======
    print("=" * 70)
    print("  PART 1: 降本增效优化测试")
    print("=" * 70)
    
    price_data = df['沪深300'].dropna()
    
    opt_results = []
    
    # Baseline (fixed premium, 5-delta)
    print("\n[Baseline] 固定权利金, 5-delta...")
    r = quick_test(price_data, label='Baseline')
    opt_results.append(r)
    print(f"  CAGR diff={r['cagr_diff']*100:+.2f}%, DD red={r['dd_reduction_pct']:+.1f}%, "
          f"cost={r['annualized_premium_pct']:.2f}%")
    
    # Volatility percentile sizing
    print("\n[Optimization 1] 波动率分位数调整仓位...")
    for threshold, multiplier, label in [
        (0.25, 2.0, 'VolPct(0.25,2x)'),
        (0.30, 2.5, 'VolPct(0.30,2.5x)'),
        (0.20, 3.0, 'VolPct(0.20,3x)'),
    ]:
        r = quick_test(price_data, sizing_method=PositionSizing.VOL_PERCENTILE,
                       vol_percentile_threshold=threshold,
                       vol_scale_multiplier=multiplier,
                       label=label)
        opt_results.append(r)
        print(f"  {label}: CAGR diff={r['cagr_diff']*100:+.2f}%, "
              f"DD red={r['dd_reduction_pct']:+.1f}%, cost={r['annualized_premium_pct']:.2f}%")
    
    # Vol-adjusted delta
    print("\n[Optimization 2] 波动率调整Delta...")
    r = quick_test(price_data, strike_method=StrikeMethod.VOL_ADJUSTED_DELTA,
                   label='VolAdjDelta')
    opt_results.append(r)
    print(f"  VolAdjDelta: CAGR diff={r['cagr_diff']*100:+.2f}%, "
          f"DD red={r['dd_reduction_pct']:+.1f}%, cost={r['annualized_premium_pct']:.2f}%")
    
    # Best from sensitivity: 3-delta with 2% budget
    print("\n[Optimization 3] 参数优化: 3-delta + 2%预算...")
    r = quick_test(price_data, delta=0.03, premium_budget_pct=0.02,
                   label='BestParams(d3/b2)')
    opt_results.append(r)
    print(f"  BestParams: CAGR diff={r['cagr_diff']*100:+.2f}%, "
          f"DD red={r['dd_reduction_pct']:+.1f}%, cost={r['annualized_premium_pct']:.2f}%")
    
    # Combined: 3-delta + vol percentile
    print("\n[Optimization 4] 综合优化: 3-delta + 波动率分位数调整 + 2%预算...")
    r = quick_test(price_data, delta=0.03, premium_budget_pct=0.02,
                   sizing_method=PositionSizing.VOL_PERCENTILE,
                   vol_percentile_threshold=0.25, vol_scale_multiplier=2.0,
                   label='Combined(d3/b2/vol)')
    opt_results.append(r)
    print(f"  Combined: CAGR diff={r['cagr_diff']*100:+.2f}%, "
          f"DD red={r['dd_reduction_pct']:+.1f}%, cost={r['annualized_premium_pct']:.2f}%")
    
    # ====== PART 2: 不同市场环境稳健性 ======
    print("\n" + "=" * 70)
    print("  PART 2: 不同市场环境稳健性验证")
    print("=" * 70)
    
    # 2a: Different indices
    print("\n--- 不同标的指数 (5-delta, 1%预算) ---")
    index_results = []
    for idx_name in ['沪深300', '上证50', '中证500', '中证1000']:
        if idx_name in df.columns:
            idx_data = df[idx_name].dropna()
            r = quick_test(idx_data, label=f'Index:{idx_name}')
            index_results.append(r)
            print(f"  {idx_name}: spot CAGR={r['spot_cagr']*100:.2f}%, "
                  f"DD red={r['dd_reduction_pct']:+.1f}%, "
                  f"CAGR diff={r['cagr_diff']*100:+.2f}%, "
                  f"cost={r['annualized_premium_pct']:.2f}%")
    
    # 2b: Different time periods
    print("\n--- 不同市场周期 (5-delta, 1%预算) ---")
    period_results = []
    
    periods = [
        ('2010-2014 (震荡熊)', '2010-01-01', '2014-06-30'),
        ('2014-2016 (牛市+崩盘)', '2014-07-01', '2016-06-30'),
        ('2016-2018 (慢牛)', '2016-07-01', '2018-12-31'),
        ('2019-2021 (牛市)', '2019-01-01', '2021-12-31'),
        ('2022-2026 (震荡)', '2022-01-01', '2026-07-15'),
    ]
    
    for pname, start, end in periods:
        mask = (price_data.index >= start) & (price_data.index <= end)
        period_data = price_data[mask]
        if len(period_data) > 60:
            r = quick_test(period_data, label=f'Period:{pname}')
            period_results.append(r)
            print(f"  {pname}: spot CAGR={r['spot_cagr']*100:.2f}%, "
                  f"DD red={r['dd_reduction_pct']:+.1f}%, "
                  f"CAGR diff={r['cagr_diff']*100:+.2f}%, "
                  f"win rate={r['win_rate']*100:.1f}%")
    
    # ====== SUMMARY ======
    print(f"\n{'='*70}")
    print(f"  综合结果汇总 (总耗时 {time.time()-t0:.0f}s)")
    print(f"{'='*70}")
    
    print(f"\n>> 降本增效优化效果:")
    print(f"  {'策略':<25s} {'CAGR差':>8s} {'回撤降低':>8s} {'年成本':>8s} {'胜率':>6s}")
    print(f"  {'-'*55}")
    for r in opt_results:
        label = r.get('label', 'N/A')
        print(f"  {label:<25s} {r['cagr_diff']*100:>+7.2f}% {r['dd_reduction_pct']:>+7.1f}% "
              f"{r['annualized_premium_pct']:>7.2f}% {r['win_rate']*100:>5.1f}%")
    
    best_opt = max(opt_results, key=lambda x: x['dd_reduction_pct'])
    print(f"\n  ==> 最佳降本方案: {best_opt['label']} "
          f"(回撤降低 {best_opt['dd_reduction_pct']:+.1f}%)")
    
    print(f"\n>> 不同标的指数稳健性:")
    print(f"  {'指数':<12s} {'标的CAGR':>8s} {'CAGR差':>8s} {'回撤降低':>8s} {'年成本':>8s}")
    print(f"  {'-'*48}")
    for r in index_results:
        label = r.get('label', 'N/A').replace('Index:', '')
        print(f"  {label:<12s} {r['spot_cagr']*100:>+7.2f}% {r['cagr_diff']*100:>+7.2f}% "
              f"{r['dd_reduction_pct']:>+7.1f}% {r['annualized_premium_pct']:>7.2f}%")
    
    print(f"\n>> 不同市场周期稳健性:")
    print(f"  {'周期':<25s} {'标的CAGR':>8s} {'CAGR差':>8s} {'回撤降低':>8s} {'胜率':>6s}")
    print(f"  {'-'*58}")
    for r in period_results:
        label = r.get('label', 'N/A').replace('Period:', '')
        print(f"  {label:<25s} {r['spot_cagr']*100:>+7.2f}% {r['cagr_diff']*100:>+7.2f}% "
              f"{r['dd_reduction_pct']:>+7.1f}% {r['win_rate']*100:>5.1f}%")
    
    # Save
    os.makedirs('charts_v2', exist_ok=True)
    all_results = {
        'optimization': opt_results,
        'indices': index_results,
        'periods': period_results,
    }
    
    # Convert to serializable dicts
    serializable = {}
    for key, items in all_results.items():
        serializable[key] = [{k: (float(v) if isinstance(v, (np.floating, np.integer)) else 
                                   str(v) if isinstance(v, pd.Timestamp) else v)
                              for k, v in item.items()}
                             for item in items]
    
    with open('charts_v2/optimization_robustness.json', 'w') as f:
        json.dump(serializable, f, indent=2, default=str)
    
    print(f"\n结果已保存: charts_v2/optimization_robustness.json")
    
    return all_results


if __name__ == '__main__':
    main()
