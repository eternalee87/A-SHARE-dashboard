"""
Baseline 回测 — 纯买入深度虚值看跌期权策略

目标：
1. 复现 "永久持有尾部风险敞口" 的基准收益/成本特征
2. 建立无择时策略的 Baseline
3. 验证 Black-Scholes 合成的期权定价是否合理

用法：
    python run_baseline.py
    python run_baseline.py --index 沪深300 --delta 0.05 --tenor 30 --budget 1.0
"""

import sys
import os
import argparse
import numpy as np
import pandas as pd
from datetime import datetime

# 添加项目根目录到 path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from universa_backtest.strategy import (
    DeepOTMPutStrategy, StrategyParams, StrikeMethod, PositionSizing
)
from universa_backtest.analysis import (
    compute_performance_metrics, compute_trade_analysis,
    compute_rolling_metrics, plot_baseline_results
)


def load_data(csv_path='data/style_indices_v2.csv', index_name='沪深300'):
    """加载指数数据"""
    df = pd.read_csv(csv_path, index_col=0, parse_dates=True)
    if index_name not in df.columns:
        available = [c for c in df.columns if not c.startswith('Unnamed')]
        raise ValueError(f"指数 '{index_name}' 不存在。可用: {available}")
    
    price_data = df[index_name].dropna()
    print(f"加载 {index_name}: {len(price_data)} 行, "
          f"{price_data.index[0].strftime('%Y-%m-%d')} ~ {price_data.index[-1].strftime('%Y-%m-%d')}")
    return price_data


def run_baseline(price_data: pd.Series, delta: float = 0.05, 
                 tenor_days: int = 30, premium_budget_pct: float = 0.01,
                 vol_window: int = 20, moneyness: float = None,
                 strike_method: str = 'delta') -> dict:
    """
    运行 Baseline 回测。
    
    Parameters
    ----------
    price_data : pd.Series
        指数价格序列
    delta : float
        目标 Delta（仅 strike_method='delta' 时）
    tenor_days : int
        期权期限（日历日）
    premium_budget_pct : float
        年化权利金预算比例
    vol_window : int
        波动率估计窗口（交易日）
    moneyness : float
        虚值程度（仅 strike_method='moneyness' 时）
    strike_method : str
        'delta' 或 'moneyness'
    """
    # 配置策略参数
    if strike_method == 'moneyness' and moneyness is not None:
        sm = StrikeMethod.FIXED_MONEYNESS
        m = moneyness
        d = 0.05  # 不使用
    else:
        sm = StrikeMethod.FIXED_DELTA
        d = delta
        m = 0.85
    
    params = StrategyParams(
        delta=d,
        moneyness=m,
        strike_method=sm,
        tenor_days=tenor_days,
        roll_frequency_days=21,
        hold_to_expiry=True,
        sizing_method=PositionSizing.FIXED_PREMIUM,
        premium_budget_pct=premium_budget_pct,
        notional_hedge_pct=1.0,
        vol_window=vol_window,
        vol_method='historical',
        vol_min=0.05,
        vol_max=1.50,
        risk_free_rate=0.03,
        transaction_cost_pct=0.0005,
    )
    
    print(f"\n{'='*60}")
    print(f"策略参数:")
    print(f"  行权方式: {params.strike_method.value}")
    if params.strike_method == StrikeMethod.FIXED_DELTA:
        print(f"  目标 Delta: {params.delta:.0%}")
    else:
        print(f"  虚值程度: {params.moneyness:.0%}")
    print(f"  期权期限: {params.tenor_days} 天")
    print(f"  权利金预算: {params.premium_budget_pct*100:.1f}% / 期")
    print(f"  波动率窗口: {params.vol_window} 天")
    print(f"  无风险利率: {params.risk_free_rate:.1%}")
    print(f"{'='*60}")
    
    # 创建策略并运行
    strategy = DeepOTMPutStrategy(params)
    
    print("\n运行回测...")
    results = strategy.run(price_data, progress=True)
    
    # 获取交易日志
    trades = strategy.get_trade_log()
    
    # 计算绩效指标
    metrics = compute_performance_metrics(results)
    
    # 交易分析
    trade_analysis = compute_trade_analysis(trades)
    
    # 打印结果
    print(f"\n{'='*60}")
    print(f"回测完成: {results.index[0].strftime('%Y-%m-%d')} ~ {results.index[-1].strftime('%Y-%m-%d')}")
    print(f"交易日数: {len(results)}")
    print(f"{'='*60}")
    
    print(f"\n--- 收益指标 ---")
    print(f"标的 CAGR:           {metrics['spot_cagr']*100:8.2f}%")
    print(f"对冲组合 CAGR:       {metrics['nav_cagr']*100:8.2f}%")
    print(f"对冲成本 (CAGR差):   {(metrics['spot_cagr']-metrics['nav_cagr'])*100:8.2f}%")
    
    print(f"\n--- 风险指标 ---")
    print(f"标的波动率:          {metrics['spot_volatility']*100:8.2f}%")
    print(f"对冲组合波动率:      {metrics['nav_volatility']*100:8.2f}%")
    print(f"标的最大回撤:        {metrics['spot_max_drawdown']*100:8.2f}%")
    print(f"对冲组合最大回撤:    {metrics['nav_max_drawdown']*100:8.2f}%")
    print(f"回撤降低:            {metrics['dd_reduction_pct']:8.1f}%")
    
    print(f"\n--- 对冲成本 ---")
    print(f"累计权利金支出:      {metrics['total_premium_paid']:8.2f}")
    print(f"累计赔付收入:        {metrics['total_payoff']:8.2f}")
    print(f"累计对冲损益:        {metrics['total_hedge_pnl']:8.2f}")
    print(f"年化权利金成本:      {metrics['annualized_premium_pct']:8.2f}% / 年")
    print(f"年化赔付收入:        {metrics['annualized_payoff_pct']:8.2f}% / 年")
    print(f"年化净成本:          {metrics['annualized_net_cost_pct']:8.2f}% / 年")
    
    print(f"\n--- 尾部风险 ---")
    print(f"95% VaR:             {metrics['spot_var_95']*100:8.2f}% → {metrics['nav_var_95']*100:8.2f}%")
    print(f"95% CVaR:            {metrics['spot_cvar_95']*100:8.2f}% → {metrics['nav_cvar_95']*100:8.2f}%")
    print(f"偏度:                {metrics['spot_skewness']:8.3f} → {metrics['nav_skewness']:8.3f}")
    print(f"下跌月平均保护:      {metrics['down_month_protection']*100:8.2f}%")
    
    print(f"\n--- 交易统计 ---")
    print(f"总交易笔数:          {trade_analysis.get('total_trades', 0)}")
    print(f"胜率:                {trade_analysis.get('win_rate', 0)*100:8.1f}%")
    print(f"最大单笔赔付:        {trade_analysis.get('max_single_payoff', 0):8.2f}")
    print(f"最大连续亏损笔数:    {trade_analysis.get('max_consecutive_losses', 0)}")
    print(f"盈亏比 (正收益均值/成本均值): {trade_analysis.get('payoff_to_cost_ratio', 0):8.2f}")
    
    return {
        'results': results,
        'trades': trades,
        'metrics': metrics,
        'trade_analysis': trade_analysis,
        'params': params,
    }


def main():
    parser = argparse.ArgumentParser(description='Universa 深度虚值看跌期权 Baseline 回测')
    parser.add_argument('--index', default='沪深300', help='标的指数 (默认: 沪深300)')
    parser.add_argument('--delta', type=float, default=0.05, help='目标 Delta (默认: 0.05)')
    parser.add_argument('--tenor', type=int, default=30, help='期权期限天数 (默认: 30)')
    parser.add_argument('--budget', type=float, default=1.0, help='权利金预算 %% (默认: 1.0)')
    parser.add_argument('--moneyness', type=float, default=None, help='虚值程度 (如 0.85=85%% OTM)')
    parser.add_argument('--method', default='delta', choices=['delta', 'moneyness'],
                       help='行权价确定方式')
    parser.add_argument('--vol-window', type=int, default=20, help='波动率窗口')
    parser.add_argument('--save-plot', default=None, help='图表保存路径')
    parser.add_argument('--save-results', default=None, help='结果 CSV 保存路径')
    args = parser.parse_args()
    
    # 加载数据
    print("=" * 60)
    print("Universa 深度虚值看跌期权 — Baseline 回测")
    print("=" * 60)
    
    price_data = load_data(index_name=args.index)
    
    # 运行回测
    output = run_baseline(
        price_data,
        delta=args.delta,
        tenor_days=args.tenor,
        premium_budget_pct=args.budget / 100.0,
        vol_window=args.vol_window,
        moneyness=args.moneyness,
        strike_method=args.method,
    )
    
    # 保存结果
    if args.save_results:
        output['results'].to_csv(args.save_results)
        print(f"\n结果已保存: {args.save_results}")
        output['trades'].to_csv(args.save_results.replace('.csv', '_trades.csv'))
    
    # 绘图
    plot_dir = args.save_plot or f"charts_v2/baseline_{args.index}_{args.method}_{args.delta}.png"
    os.makedirs(os.path.dirname(plot_dir) if os.path.dirname(plot_dir) else '.', exist_ok=True)
    plot_baseline_results(
        output['results'], output['metrics'], output['trades'],
        save_path=plot_dir
    )
    
    return output


if __name__ == '__main__':
    main()
