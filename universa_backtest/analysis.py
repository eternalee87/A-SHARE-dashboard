"""
回测分析与可视化模块

性能指标计算、归因分析、绘图功能。
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional


# ==================== 性能指标 ====================

def compute_performance_metrics(results: pd.DataFrame, 
                                 benchmark_returns: pd.Series = None,
                                 risk_free_rate: float = 0.03,
                                 initial_nav: float = 100.0) -> Dict[str, Any]:
    """
    计算核心绩效指标。
    
    Parameters
    ----------
    results : pd.DataFrame
        策略回测结果（从 strategy.run() 返回）
    benchmark_returns : pd.Series, optional
        基准日收益率
    risk_free_rate : float
        无风险利率
    
    Returns
    -------
    dict of metrics
    """
    metrics = {}
    
    # 基础统计
    n_days = len(results)
    n_years = n_days / 252
    
    spot = results['spot']
    nav = results['nav']
    
    # 日收益率
    spot_returns = spot.pct_change().dropna()
    nav_returns = nav.pct_change().dropna()
    
    # --- 收益指标 ---
    metrics['total_spot_return'] = spot.iloc[-1] / spot.iloc[0] - 1.0
    metrics['total_nav_return'] = nav.iloc[-1] / nav.iloc[0] - 1.0
    
    # CAGR
    metrics['spot_cagr'] = (spot.iloc[-1] / spot.iloc[0]) ** (1 / n_years) - 1 if n_years > 0 else 0
    metrics['nav_cagr'] = (nav.iloc[-1] / nav.iloc[0]) ** (1 / n_years) - 1 if n_years > 0 else 0
    
    # 年化波动率
    metrics['spot_volatility'] = spot_returns.std() * np.sqrt(252)
    metrics['nav_volatility'] = nav_returns.std() * np.sqrt(252)
    
    # Sharpe Ratio
    excess_nav = nav_returns - risk_free_rate / 252
    metrics['nav_sharpe'] = excess_nav.mean() / nav_returns.std() * np.sqrt(252) if nav_returns.std() > 0 else 0
    
    # --- 风险指标 ---
    # 最大回撤
    spot_peak = spot.expanding().max()
    spot_dd = (spot - spot_peak) / spot_peak
    metrics['spot_max_drawdown'] = spot_dd.min()
    
    nav_peak = nav.expanding().max()
    nav_dd = (nav - nav_peak) / nav_peak
    metrics['nav_max_drawdown'] = nav_dd.min()
    
    # 最大回撤降低幅度
    metrics['dd_reduction_pct'] = (abs(metrics['spot_max_drawdown']) - abs(metrics['nav_max_drawdown'])) / abs(metrics['spot_max_drawdown']) * 100
    
    # Calmar Ratio (CAGR / |MaxDD|)
    metrics['spot_calmar'] = metrics['spot_cagr'] / abs(metrics['spot_max_drawdown']) if abs(metrics['spot_max_drawdown']) > 0 else 0
    metrics['nav_calmar'] = metrics['nav_cagr'] / abs(metrics['nav_max_drawdown']) if abs(metrics['nav_max_drawdown']) > 0 else 0
    
    # --- 尾部风险指标 ---
    # 5% VaR（历史模拟法）
    metrics['spot_var_95'] = spot_returns.quantile(0.05)
    metrics['nav_var_95'] = nav_returns.quantile(0.05)
    
    # CVaR (Expected Shortfall)
    metrics['spot_cvar_95'] = spot_returns[spot_returns <= metrics['spot_var_95']].mean()
    metrics['nav_cvar_95'] = nav_returns[nav_returns <= metrics['nav_var_95']].mean()
    
    # 偏度和峰度
    metrics['spot_skewness'] = spot_returns.skew()
    metrics['nav_skewness'] = nav_returns.skew()
    metrics['spot_kurtosis'] = spot_returns.kurtosis()
    metrics['nav_kurtosis'] = nav_returns.kurtosis()
    
    # --- 对冲成本 ---
    metrics['total_premium_paid'] = results['cumulative_premium'].iloc[-1]
    metrics['total_payoff'] = results['cumulative_payoff'].iloc[-1]
    metrics['total_hedge_pnl'] = results['cumulative_pnl'].iloc[-1]
    # 年化对冲净成本（% of 初始本金）
    metrics['annualized_net_cost_pct'] = (results['cumulative_premium'].iloc[-1] - results['cumulative_payoff'].iloc[-1]) / n_years / initial_nav * 100
    
    # 年化权利金支出率（% of 初始本金）
    metrics['annualized_premium_pct'] = (results['cumulative_premium'].iloc[-1] / n_years) / initial_nav * 100
    
    # 年化赔付率（% of 初始本金）
    metrics['annualized_payoff_pct'] = (results['cumulative_payoff'].iloc[-1] / n_years) / initial_nav * 100
    
    # --- 崩盘爆发力 ---
    # 最大单笔赔付 / 平均单笔成本
    # (需要从 trade log 计算)
    
    # 负收益月的对冲效果
    monthly_spot = spot.resample('ME').last().pct_change()
    monthly_nav = nav.resample('ME').last().pct_change()
    
    down_months = monthly_spot[monthly_spot < 0]
    if len(down_months) > 0:
        spot_down_avg = down_months.mean()
        nav_down_avg = monthly_nav.loc[down_months.index].mean()
        metrics['avg_down_month_spot'] = spot_down_avg
        metrics['avg_down_month_nav'] = nav_down_avg
        metrics['down_month_protection'] = nav_down_avg - spot_down_avg  # 正值表示保护
    else:
        metrics['avg_down_month_spot'] = 0
        metrics['avg_down_month_nav'] = 0
        metrics['down_month_protection'] = 0
    
    return metrics


def compute_trade_analysis(trades: pd.DataFrame) -> Dict[str, Any]:
    """
    交易层面分析。
    """
    if len(trades) == 0:
        return {}
    
    analysis = {}
    
    # 胜率（有正收益的 trade 占比）
    analysis['total_trades'] = len(trades)
    analysis['winning_trades'] = (trades['pnl'] > 0).sum()
    analysis['win_rate'] = analysis['winning_trades'] / analysis['total_trades']
    
    # 赔付比
    analysis['avg_premium'] = trades['premium_paid'].mean()
    analysis['avg_payoff_when_positive'] = trades[trades['payoff'] > 0]['payoff'].mean() if (trades['payoff'] > 0).sum() > 0 else 0
    analysis['avg_payoff'] = trades['payoff'].mean()
    
    # 最大崩盘收益
    analysis['max_single_payoff'] = trades['payoff'].max()
    analysis['max_single_pnl'] = trades['pnl'].max()
    analysis['max_single_cost'] = trades['premium_paid'].max()
    
    # 盈亏比
    if analysis['avg_premium'] > 0:
        analysis['payoff_to_cost_ratio'] = analysis['avg_payoff_when_positive'] / analysis['avg_premium']
    else:
        analysis['payoff_to_cost_ratio'] = 0
    
    # 连续亏损
    pnl_series = trades['pnl'].values
    loss_streaks = []
    current_streak = 0
    for p in pnl_series:
        if p <= 0:
            current_streak += 1
        else:
            if current_streak > 0:
                loss_streaks.append(current_streak)
            current_streak = 0
    if current_streak > 0:
        loss_streaks.append(current_streak)
    
    analysis['max_consecutive_losses'] = max(loss_streaks) if loss_streaks else 0
    analysis['avg_consecutive_losses'] = np.mean(loss_streaks) if loss_streaks else 0
    
    # 盈亏分位数
    for q in [0.1, 0.25, 0.5, 0.75, 0.9, 0.95, 0.99]:
        analysis[f'pnl_q{int(q*100)}'] = trades['pnl'].quantile(q)
    
    return analysis


def compute_rolling_metrics(results: pd.DataFrame, window: int = 252) -> pd.DataFrame:
    """
    计算滚动绩效指标。
    """
    df = pd.DataFrame(index=results.index)
    
    spot = results['spot']
    nav = results['nav']
    
    # 滚动收益率
    df['rolling_spot_return'] = spot.pct_change(window).dropna()
    df['rolling_nav_return'] = nav.pct_change(window).dropna()
    
    # 滚动波动率
    df['rolling_spot_vol'] = spot.pct_change().rolling(window).std() * np.sqrt(252)
    df['rolling_nav_vol'] = nav.pct_change().rolling(window).std() * np.sqrt(252)
    
    # 滚动最大回撤
    df['rolling_spot_dd'] = spot.rolling(window).apply(
        lambda x: (x[-1] / x.max() - 1) if x.max() > 0 else 0)
    df['rolling_nav_dd'] = nav.rolling(window).apply(
        lambda x: (x[-1] / x.max() - 1) if x.max() > 0 else 0)
    
    # 滚动对冲成本
    df['rolling_premium'] = results['cumulative_premium'].diff(window)
    df['rolling_payoff'] = results['cumulative_payoff'].diff(window)
    df['rolling_hedge_pnl'] = df['rolling_payoff'] - df['rolling_premium']
    
    return df


# ==================== 可视化 ====================

def plot_baseline_results(results: pd.DataFrame, metrics: Dict, 
                          trades: pd.DataFrame = None,
                          save_path: str = None):
    """
    绘制 Baseline 回测结果图。
    """
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    
    plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans']
    plt.rcParams['axes.unicode_minus'] = False
    
    fig, axes = plt.subplots(3, 2, figsize=(16, 14))
    
    # ---- (1) 净值曲线 ----
    ax = axes[0, 0]
    ax.plot(results.index, results['nav'] / results['nav'].iloc[0], 
            label='对冲组合 NAV', color='blue', linewidth=1.5)
    ax.plot(results.index, results['spot'] / results['spot'].iloc[0], 
            label='标的指数 (裸多头)', color='gray', linewidth=1, alpha=0.7)
    ax.set_title('净值曲线对比')
    ax.set_ylabel('累计净值')
    ax.legend(loc='upper left')
    ax.grid(True, alpha=0.3)
    
    # ---- (2) 累计对冲 P&L ----
    ax = axes[0, 1]
    ax.fill_between(results.index, 0, results['cumulative_pnl'] / results['spot'].iloc[0] * 100,
                    where=results['cumulative_pnl'] >= 0, color='green', alpha=0.3, label='正收益')
    ax.fill_between(results.index, 0, results['cumulative_pnl'] / results['spot'].iloc[0] * 100,
                    where=results['cumulative_pnl'] < 0, color='red', alpha=0.3, label='净成本')
    ax.plot(results.index, results['cumulative_pnl'] / results['spot'].iloc[0] * 100, 
            color='black', linewidth=1)
    ax.set_title('累计对冲损益 (% 初始本金)')
    ax.set_ylabel('累计损益 (%)')
    ax.legend(loc='upper left')
    ax.grid(True, alpha=0.3)
    ax.axhline(y=0, color='black', linewidth=0.5)
    
    # ---- (3) 回撤对比 ----
    ax = axes[1, 0]
    spot_peak = results['spot'].expanding().max()
    nav_peak = results['nav'].expanding().max()
    spot_dd = (results['spot'] - spot_peak) / spot_peak * 100
    nav_dd = (results['nav'] - nav_peak) / nav_peak * 100
    ax.fill_between(results.index, 0, spot_dd, color='red', alpha=0.15, label='标的指数回撤')
    ax.fill_between(results.index, 0, nav_dd, color='blue', alpha=0.15, label='对冲组合回撤')
    ax.set_title('回撤对比')
    ax.set_ylabel('回撤 (%)')
    ax.legend(loc='lower left')
    ax.grid(True, alpha=0.3)
    
    # ---- (4) 权利金支出 vs 赔付 ----
    ax = axes[1, 1]
    if trades is not None and len(trades) > 0:
        monthly_premium = trades.set_index('entry_date')['premium_paid'].resample('M').sum()
        monthly_payoff = trades.set_index('exit_date')['payoff'].resample('M').sum()
        all_months = pd.date_range(monthly_premium.index.min(), monthly_premium.index.max(), freq='M')
        monthly_premium = monthly_premium.reindex(all_months, fill_value=0)
        monthly_payoff = monthly_payoff.reindex(all_months, fill_value=0)
        
        width = 0.35
        x = np.arange(min(len(monthly_premium), 120))  # 最多显示 120 个月
        ax.bar(x, monthly_premium.values[:len(x)], width, label='月度权利金支出', color='red', alpha=0.6)
        ax.bar(x + width, monthly_payoff.values[:len(x)], width, label='月度赔付收入', color='green', alpha=0.6)
        ax.set_title('月度权利金 vs 赔付')
        ax.set_xlabel('月份序号')
        ax.set_ylabel('金额')
        ax.legend()
        ax.grid(True, alpha=0.3, axis='y')
    
    # ---- (5) 滚动 1 年对冲效果 ----
    ax = axes[2, 0]
    window = 252
    rolling_spot_ret = results['spot'].pct_change(window).dropna()
    rolling_nav_ret = results['nav'].pct_change(window).dropna()
    ax.plot(rolling_spot_ret.index, rolling_spot_ret * 100, label='标的 1年收益', color='gray', linewidth=1)
    ax.plot(rolling_nav_ret.index, rolling_nav_ret * 100, label='对冲组合 1年收益', color='blue', linewidth=1)
    ax.set_title('滚动 1 年收益率')
    ax.set_ylabel('收益率 (%)')
    ax.legend()
    ax.grid(True, alpha=0.3)
    ax.axhline(y=0, color='black', linewidth=0.5)
    
    # ---- (6) 绩效摘要 ----
    ax = axes[2, 1]
    ax.axis('off')
    summary_text = f"""
    ═══════════════════════════════
            策略绩效摘要
    ═══════════════════════════════
    标的 CAGR:           {metrics.get('spot_cagr', 0)*100:6.2f}%
    对冲组合 CAGR:       {metrics.get('nav_cagr', 0)*100:6.2f}%
    
    标的波动率:          {metrics.get('spot_volatility', 0)*100:6.2f}%
    对冲组合波动率:      {metrics.get('nav_volatility', 0)*100:6.2f}%
    
    标的最大回撤:        {metrics.get('spot_max_drawdown', 0)*100:6.2f}%
    对冲组合最大回撤:    {metrics.get('nav_max_drawdown', 0)*100:6.2f}%
    回撤降低幅度:        {metrics.get('dd_reduction_pct', 0):6.1f}%
    
    年化权利金成本:      {metrics.get('annualized_premium_pct', 0):6.2f}% / 年
    年化净对冲成本:      {metrics.get('annualized_net_cost_pct', 0):6.2f}% / 年
    总对冲损益:          {metrics.get('total_hedge_pnl', 0):6.2f}
    
    Sharpe Ratio:        {metrics.get('nav_sharpe', 0):6.3f}
    Calmar Ratio:        {metrics.get('nav_calmar', 0):6.3f}
    
    95% VaR:             {metrics.get('nav_var_95', 0)*100:6.2f}%
    95% CVaR:            {metrics.get('nav_cvar_95', 0)*100:6.2f}%
    
    偏度:                {metrics.get('nav_skewness', 0):6.3f}
    峰度:                {metrics.get('nav_kurtosis', 0):6.3f}
    
    下跌月平均保护:      {metrics.get('down_month_protection', 0)*100:6.2f}%
    ═══════════════════════════════
    """
    ax.text(0.1, 0.9, summary_text, transform=ax.transAxes,
            fontsize=9, fontfamily='monospace', verticalalignment='top',
            bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
    
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        print(f"图表已保存: {save_path}")
    
    plt.show()
    return fig


def plot_sensitivity_heatmap(results_df: pd.DataFrame, x_param: str, y_param: str, 
                              metric: str, title: str = None, save_path: str = None):
    """
    绘制参数敏感度热力图。
    """
    import matplotlib.pyplot as plt
    
    plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans']
    plt.rcParams['axes.unicode_minus'] = False
    
    pivot = results_df.pivot_table(values=metric, index=y_param, columns=x_param, aggfunc='mean')
    
    fig, ax = plt.subplots(figsize=(10, 8))
    im = ax.imshow(pivot.values, aspect='auto', cmap='RdYlGn')
    
    ax.set_xticks(range(len(pivot.columns)))
    ax.set_xticklabels([f'{x:.3f}' for x in pivot.columns], rotation=45)
    ax.set_yticks(range(len(pivot.index)))
    ax.set_yticklabels([f'{y:.3f}' for y in pivot.index])
    
    ax.set_xlabel(x_param)
    ax.set_ylabel(y_param)
    ax.set_title(title or f'{metric} 敏感度热力图')
    
    plt.colorbar(im, ax=ax)
    
    # 标注数值
    for i in range(len(pivot.index)):
        for j in range(len(pivot.columns)):
            ax.text(j, i, f'{pivot.values[i, j]:.3f}', ha='center', va='center', fontsize=8)
    
    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
    
    plt.show()
    return fig


def plot_regime_analysis(regime_results: Dict[str, pd.DataFrame], 
                          metrics_list: List[str] = None,
                          save_path: str = None):
    """
    不同市场环境下的策略表现对比。
    """
    import matplotlib.pyplot as plt
    
    plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans']
    plt.rcParams['axes.unicode_minus'] = False
    
    if metrics_list is None:
        metrics_list = ['nav_cagr', 'spot_max_drawdown', 'nav_max_drawdown', 
                       'dd_reduction_pct', 'annualized_premium_pct']
    
    n_regimes = len(regime_results)
    n_metrics = len(metrics_list)
    
    fig, axes = plt.subplots(1, n_metrics, figsize=(4 * n_metrics, 5))
    if n_metrics == 1:
        axes = [axes]
    
    regime_names = list(regime_results.keys())
    colors = plt.cm.Set2(np.linspace(0, 1, n_regimes))
    
    for i, metric_name in enumerate(metrics_list):
        ax = axes[i]
        values = [regime_results[r].get(metric_name, 0) for r in regime_names]
        
        # 格式化显示
        if metric_name in ['annualized_premium_pct']:
            display_values = values
            fmt = '{:.0f}'
        else:
            display_values = [v * 100 for v in values]
            fmt = '{:.1f}%'
        
        bars = ax.bar(range(n_regimes), display_values, color=colors)
        ax.set_xticks(range(n_regimes))
        ax.set_xticklabels(regime_names, rotation=30, ha='right')
        ax.set_title(metric_name)
        ax.grid(True, alpha=0.3, axis='y')
        
        for bar, val in zip(bars, display_values):
            ax.text(bar.get_x() + bar.get_width()/2, bar.get_height(),
                    fmt.format(val), ha='center', va='bottom', fontsize=8)
    
    plt.suptitle('不同市场环境下的策略表现', fontsize=14)
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
    
    plt.show()
    return fig
