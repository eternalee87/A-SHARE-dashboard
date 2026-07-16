"""
参数敏感性分析 — 系统性测试不同参数组合对策略表现的影响

测试维度：
1. Delta (1%, 3%, 5%, 10%, 15%, 20%)
2. 虚值程度 Moneyness (70%, 75%, 80%, 85%, 90%, 95%)
3. 期权期限 Tenor (14d, 30d, 60d, 90d)
4. 年化预算 (0.5%, 1%, 2%, 3%, 5%)
5. 波动率窗口 (10d, 20d, 60d, 120d)
"""

import sys, os
sys.path.insert(0, 'lib')
os.environ['MPLCONFIGDIR'] = os.environ.get('TEMP', '.') + '/matplotlib'

import numpy as np
import pandas as pd
from itertools import product
import json
from datetime import datetime

from universa_backtest.strategy import (
    DeepOTMPutStrategy, StrategyParams, StrikeMethod, PositionSizing
)
from universa_backtest.analysis import (
    compute_performance_metrics, compute_trade_analysis
)


def load_data(index_name='沪深300'):
    df = pd.read_csv('data/style_indices_v2.csv', index_col=0, parse_dates=True)
    return df[index_name].dropna()


def run_single_test(price_data, **kwargs):
    """Run a single parameter combination."""
    params = StrategyParams(
        delta=kwargs.get('delta', 0.05),
        moneyness=kwargs.get('moneyness', 0.85),
        strike_method=kwargs.get('strike_method', StrikeMethod.FIXED_DELTA),
        tenor_days=kwargs.get('tenor_days', 30),
        roll_frequency_days=kwargs.get('roll_frequency_days', 21),
        sizing_method=kwargs.get('sizing_method', PositionSizing.FIXED_PREMIUM),
        premium_budget_pct=kwargs.get('premium_budget_pct', 0.01),
        vol_window=kwargs.get('vol_window', 20),
        risk_free_rate=0.03,
    )
    
    strategy = DeepOTMPutStrategy(params)
    try:
        results = strategy.run(price_data)
        trades = strategy.get_trade_log()
        metrics = compute_performance_metrics(results)
        trade_analysis = compute_trade_analysis(trades)
        
        # Extract key metrics
        return {
            **kwargs,
            'spot_cagr': metrics['spot_cagr'],
            'nav_cagr': metrics['nav_cagr'],
            'cagr_diff': metrics['nav_cagr'] - metrics['spot_cagr'],
            'spot_max_dd': metrics['spot_max_drawdown'],
            'nav_max_dd': metrics['nav_max_drawdown'],
            'dd_reduction_pct': metrics['dd_reduction_pct'],
            'total_premium': metrics['total_premium_paid'],
            'total_payoff': metrics['total_payoff'],
            'total_pnl': metrics['total_hedge_pnl'],
            'annualized_premium_pct': metrics['annualized_premium_pct'],
            'annualized_net_cost_pct': metrics['annualized_net_cost_pct'],
            'win_rate': trade_analysis['win_rate'],
            'max_consecutive_losses': trade_analysis['max_consecutive_losses'],
            'payoff_cost_ratio': trade_analysis['payoff_to_cost_ratio'],
            'max_single_payoff': trade_analysis['max_single_payoff'],
            'total_trades': trade_analysis['total_trades'],
            'spot_vol': metrics['spot_volatility'],
            'nav_vol': metrics['nav_volatility'],
            'nav_sharpe': metrics['nav_sharpe'],
            'nav_calmar': metrics['nav_calmar'],
        }
    except Exception as e:
        print(f"  ERROR: {e}")
        return {**kwargs, 'error': str(e)}


def run_delta_sensitivity(price_data):
    """Test different delta values."""
    print("\n" + "=" * 60)
    print("Delta 敏感度分析")
    print("=" * 60)
    
    deltas = [0.01, 0.03, 0.05, 0.10, 0.15, 0.20]
    results = []
    
    for delta in deltas:
        print(f"  Testing delta={delta}...")
        r = run_single_test(price_data, delta=delta, strike_method=StrikeMethod.FIXED_DELTA)
        if 'error' not in r:
            print(f"    CAGR diff: {r['cagr_diff']*100:+.2f}%, DD reduction: {r['dd_reduction_pct']:+.1f}%, "
                  f"Annual cost: {r['annualized_premium_pct']:.2f}%, Win rate: {r['win_rate']*100:.1f}%")
        results.append(r)
    
    return pd.DataFrame(results)


def run_moneyness_sensitivity(price_data):
    """Test different moneyness levels."""
    print("\n" + "=" * 60)
    print("虚值程度 (Moneyness) 敏感度分析")
    print("=" * 60)
    
    moneyness_levels = [0.70, 0.75, 0.80, 0.85, 0.90, 0.95]
    results = []
    
    for m in moneyness_levels:
        print(f"  Testing moneyness={m:.0%}...")
        r = run_single_test(price_data, moneyness=m, strike_method=StrikeMethod.FIXED_MONEYNESS)
        if 'error' not in r:
            print(f"    CAGR diff: {r['cagr_diff']*100:+.2f}%, DD reduction: {r['dd_reduction_pct']:+.1f}%, "
                  f"Annual cost: {r['annualized_premium_pct']:.2f}%, Win rate: {r['win_rate']*100:.1f}%")
        results.append(r)
    
    return pd.DataFrame(results)


def run_tenor_sensitivity(price_data):
    """Test different option tenors."""
    print("\n" + "=" * 60)
    print("期权期限 (Tenor) 敏感度分析")
    print("=" * 60)
    
    tenors = [14, 30, 60, 90]
    results = []
    
    for tenor in tenors:
        # Adjust roll frequency proportional to tenor
        roll_freq = max(5, int(tenor * 21 / 30))
        print(f"  Testing tenor={tenor}d (roll every {roll_freq} trading days)...")
        r = run_single_test(price_data, tenor_days=tenor, roll_frequency_days=roll_freq)
        if 'error' not in r:
            print(f"    CAGR diff: {r['cagr_diff']*100:+.2f}%, DD reduction: {r['dd_reduction_pct']:+.1f}%, "
                  f"Annual cost: {r['annualized_premium_pct']:.2f}%")
        results.append(r)
    
    return pd.DataFrame(results)


def run_budget_sensitivity(price_data):
    """Test different annual premium budgets."""
    print("\n" + "=" * 60)
    print("年化预算 敏感度分析")
    print("=" * 60)
    
    budgets = [0.005, 0.01, 0.02, 0.03, 0.05]
    results = []
    
    for budget in budgets:
        print(f"  Testing budget={budget*100:.1f}%...")
        r = run_single_test(price_data, premium_budget_pct=budget)
        if 'error' not in r:
            print(f"    CAGR diff: {r['cagr_diff']*100:+.2f}%, DD reduction: {r['dd_reduction_pct']:+.1f}%, "
                  f"Annual cost: {r['annualized_premium_pct']:.2f}%")
        results.append(r)
    
    return pd.DataFrame(results)


def run_vol_window_sensitivity(price_data):
    """Test different volatility estimation windows."""
    print("\n" + "=" * 60)
    print("波动率窗口 敏感度分析")
    print("=" * 60)
    
    windows = [10, 20, 60, 120]
    results = []
    
    for w in windows:
        print(f"  Testing vol_window={w}d...")
        r = run_single_test(price_data, vol_window=w)
        if 'error' not in r:
            print(f"    CAGR diff: {r['cagr_diff']*100:+.2f}%, DD reduction: {r['dd_reduction_pct']:+.1f}%")
        results.append(r)
    
    return pd.DataFrame(results)


def run_combined_grid(price_data):
    """Run a grid of delta × budget combinations."""
    print("\n" + "=" * 60)
    print("Delta × Budget 网格分析")
    print("=" * 60)
    
    deltas = [0.03, 0.05, 0.10, 0.15]
    budgets = [0.005, 0.01, 0.02, 0.03]
    results = []
    
    for delta, budget in product(deltas, budgets):
        print(f"  Testing delta={delta}, budget={budget*100:.1f}%...", end=' ')
        r = run_single_test(price_data, delta=delta, premium_budget_pct=budget)
        if 'error' not in r:
            print(f"DD reduction: {r['dd_reduction_pct']:+.1f}%, CAGR diff: {r['cagr_diff']*100:+.2f}%")
        else:
            print(f"ERROR: {r['error']}")
        results.append(r)
    
    return pd.DataFrame(results)


def print_summary_table(df, title, key_cols=None):
    """Print formatted summary table."""
    if key_cols is None:
        key_cols = ['cagr_diff', 'dd_reduction_pct', 'annualized_premium_pct', 
                     'win_rate', 'max_consecutive_losses', 'payoff_cost_ratio']
    
    print(f"\n{'='*80}")
    print(f"  {title}")
    print(f"{'='*80}")
    
    # Format columns
    display = df.copy()
    for col in ['cagr_diff', 'spot_cagr', 'nav_cagr', 'spot_max_dd', 'nav_max_dd',
                'dd_reduction_pct', 'win_rate']:
        if col in display.columns:
            display[col] = display[col].apply(lambda x: f'{x*100:.2f}%' if pd.notna(x) else 'N/A')
    
    for col in ['annualized_premium_pct', 'annualized_net_cost_pct']:
        if col in display.columns:
            display[col] = display[col].apply(lambda x: f'{x:.2f}%' if pd.notna(x) else 'N/A')
    
    for col in ['payoff_cost_ratio', 'total_pnl', 'max_single_payoff']:
        if col in display.columns:
            display[col] = display[col].apply(lambda x: f'{x:.2f}' if pd.notna(x) else 'N/A')
    
    print(display.to_string())


def main():
    print("=" * 60)
    print("Universa 深度虚值看跌期权 — 参数敏感性分析")
    print("=" * 60)
    
    # Load data
    price_data = load_data('沪深300')
    print(f"数据: {len(price_data)} 行, {price_data.index[0].strftime('%Y-%m-%d')} ~ {price_data.index[-1].strftime('%Y-%m-%d')}")
    
    all_results = {}
    
    # 1. Delta sensitivity
    df_delta = run_delta_sensitivity(price_data)
    all_results['delta'] = df_delta
    print_summary_table(df_delta[['delta', 'cagr_diff', 'dd_reduction_pct', 
                                   'annualized_premium_pct', 'win_rate', 
                                   'max_consecutive_losses', 'payoff_cost_ratio']],
                        'Delta 敏感度')
    
    # 2. Moneyness sensitivity
    df_moneyness = run_moneyness_sensitivity(price_data)
    all_results['moneyness'] = df_moneyness
    print_summary_table(df_moneyness[['moneyness', 'cagr_diff', 'dd_reduction_pct',
                                       'annualized_premium_pct', 'win_rate',
                                       'max_consecutive_losses', 'payoff_cost_ratio']],
                        '虚值程度 敏感度')
    
    # 3. Tenor sensitivity
    df_tenor = run_tenor_sensitivity(price_data)
    all_results['tenor'] = df_tenor
    print_summary_table(df_tenor[['tenor_days', 'cagr_diff', 'dd_reduction_pct',
                                   'annualized_premium_pct', 'win_rate',
                                   'total_trades']],
                        '期权期限 敏感度')
    
    # 4. Budget sensitivity
    df_budget = run_budget_sensitivity(price_data)
    all_results['budget'] = df_budget
    print_summary_table(df_budget[['premium_budget_pct', 'cagr_diff', 'dd_reduction_pct',
                                    'annualized_premium_pct', 'win_rate',
                                    'nav_sharpe', 'nav_calmar']],
                        '年化预算 敏感度')
    
    # 5. Combined grid
    df_grid = run_combined_grid(price_data)
    all_results['grid'] = df_grid
    
    # Find best combinations
    if 'error' not in df_grid.columns or df_grid['error'].isna().all():
        valid = df_grid[~df_grid['cagr_diff'].isna()].copy()
        print(f"\n{'='*80}")
        print(f"  最优参数组合推荐")
        print(f"{'='*80}")
        
        # Best by CAGR improvement
        best_cagr = valid.nlargest(5, 'cagr_diff')
        print("\n按 CAGR 提升排序 Top 5:")
        for _, row in best_cagr.iterrows():
            print(f"  delta={row['delta']:.0%}, budget={row['premium_budget_pct']*100:.1f}%: "
                  f"CAGR diff={row['cagr_diff']*100:+.2f}%, DD reduction={row['dd_reduction_pct']:+.1f}%")
        
        # Best by DD reduction
        best_dd = valid.nlargest(5, 'dd_reduction_pct')
        print("\n按回撤降低排序 Top 5:")
        for _, row in best_dd.iterrows():
            print(f"  delta={row['delta']:.0%}, budget={row['premium_budget_pct']*100:.1f}%: "
                  f"CAGR diff={row['cagr_diff']*100:+.2f}%, DD reduction={row['dd_reduction_pct']:+.1f}%")
        
        # Best risk-adjusted (Calmar)
        best_calmar = valid.nlargest(5, 'nav_calmar')
        print("\n按 Calmar Ratio 排序 Top 5:")
        for _, row in best_calmar.iterrows():
            print(f"  delta={row['delta']:.0%}, budget={row['premium_budget_pct']*100:.1f}%: "
                  f"Calmar={row['nav_calmar']:.4f}, DD reduction={row['dd_reduction_pct']:+.1f}%")
    
    # Save results
    os.makedirs('charts_v2', exist_ok=True)
    for name, df in all_results.items():
        df.to_csv(f'charts_v2/sensitivity_{name}.csv', index=False)
    
    # Save summary JSON
    summary = {}
    for name, df in all_results.items():
        if len(df) > 0 and 'error' not in df.columns:
            summary[name] = df.to_dict('records')
    
    with open('charts_v2/sensitivity_summary.json', 'w') as f:
        json.dump(summary, f, indent=2, default=str)
    
    print(f"\n结果已保存到 charts_v2/sensitivity_*.csv 和 charts_v2/sensitivity_summary.json")
    
    return all_results


if __name__ == '__main__':
    main()
