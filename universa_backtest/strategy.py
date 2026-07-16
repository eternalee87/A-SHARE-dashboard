"""
深度虚值看跌期权滚动策略模块

核心策略逻辑：
- 永久持有深度虚值看跌期权（尾部风险敞口）
- 定期滚动（月度/季度），持有至到期
- 无方向择时 —— 不预判大盘涨跌
- 可选降本增效优化：波动率调整仓位、虚值度动态调整

Universa 核心思路：持续小额时间价值损耗换取极端崩盘的非线性收益。
"""

import numpy as np
import pandas as pd
from dataclasses import dataclass, field
from typing import Optional, Dict, List, Tuple
from enum import Enum

from .option_pricing import (
    black_scholes_put, black_scholes_delta,
    strike_from_delta, strike_from_moneyness,
    compute_historical_volatility, compute_ewma_volatility,
    volatility_percentile
)


class PositionSizing(Enum):
    """仓位规模确定方法"""
    FIXED_NOTIONAL = "fixed_notional"       # 固定名义本金（如 100% 组合市值）
    FIXED_PREMIUM = "fixed_premium"          # 固定权利金预算（如 组合市值的 1%）
    VOL_ADJUSTED = "vol_adjusted"            # 波动率调整：低波动时多买
    VOL_PERCENTILE = "vol_percentile"        # 波动率分位数调整
    KELLY = "kelly"                          # Kelly 准则调整


class StrikeMethod(Enum):
    """行权价确定方法"""
    FIXED_DELTA = "fixed_delta"             # 固定 Delta（如 5-delta）
    FIXED_MONEYNESS = "fixed_moneyness"     # 固定虚值程度（如 80% OTM）
    VOL_ADJUSTED_DELTA = "vol_adj_delta"    # 波动率调整 Delta


@dataclass
class StrategyParams:
    """策略参数"""
    # --- 核心参数 ---
    delta: float = 0.05                      # 目标 Delta（默认 5-delta put）
    moneyness: float = 0.85                  # 虚值程度（仅 StrikeMethod.FIXED_MONEYNESS 时使用）
    strike_method: StrikeMethod = StrikeMethod.FIXED_DELTA
    
    # --- 滚动参数 ---
    tenor_days: int = 30                     # 期权期限（日历日），近似 1 个月
    roll_frequency_days: int = 21            # 滚动频率（交易日），每月滚动
    hold_to_expiry: bool = True              # 持有至到期（否则提前滚动）
    
    # --- 仓位参数 ---
    sizing_method: PositionSizing = PositionSizing.FIXED_PREMIUM
    premium_budget_pct: float = 0.01         # 年化权利金预算（组合市值的 %），如 1% = 100bp
    notional_hedge_pct: float = 1.0          # 对冲名义本金比例（100% = 全额对冲）
    
    # --- 波动率估计参数 ---
    vol_window: int = 20                     # 历史波动率估计窗口
    vol_method: str = 'historical'           # 'historical' | 'ewma' | 'garch_proxy'
    vol_min: float = 0.05                    # 波动率下限（防止极端低估）
    vol_max: float = 1.50                    # 波动率上限（防止极端高估）
    
    # --- 降本增效参数 ---
    vol_percentile_threshold: float = 0.25   # 波动率分位数阈值（低于此值降低仓位）
    vol_scale_multiplier: float = 2.0        # 波动率分位数低时的仓位倍率上限
    kelly_fraction: float = 0.25             # Kelly 分数（0.25 = quarter-Kelly）
    
    # --- 其他 ---
    risk_free_rate: float = 0.03             # 无风险利率
    transaction_cost_pct: float = 0.0005     # 交易成本（双向 5bp 估算）
    use_put_spread: bool = False             # 是否使用看跌价差（买入 OTM put + 卖出更虚值 put）
    spread_width_pct: float = 0.10           # 价差宽度（如 10% = 买入 85% put，卖出 75% put）


@dataclass
class OptionPosition:
    """单笔期权头寸"""
    entry_date: pd.Timestamp
    expiry_date: pd.Timestamp
    strike: float
    entry_spot: float
    entry_price: float
    quantity: float                         # 合约数量
    notional_hedged: float                  # 对冲的名义本金
    delta_at_entry: float
    vol_at_entry: float
    
    # 到期结果（到期后回填）
    exit_date: Optional[pd.Timestamp] = None
    exit_price: float = 0.0                 # 到期结算价（内在价值）
    pnl: float = 0.0
    pnl_pct_notional: float = 0.0


@dataclass
class StrategyState:
    """策略运行状态"""
    cash: float = 0.0                       # 累计现金流（负=成本）
    cumulative_premium_paid: float = 0.0    # 累计权利金支出
    cumulative_payoff: float = 0.0          # 累计赔付收入
    positions: List[OptionPosition] = field(default_factory=list)
    active_positions: Dict[int, OptionPosition] = field(default_factory=dict)
    nav_history: List[float] = field(default_factory=list)
    date_history: List[pd.Timestamp] = field(default_factory=list)


class DeepOTMPutStrategy:
    """
    深度虚值看跌期权滚动策略。
    
    每个滚动日：
    1. 结算到期的期权
    2. 根据当前市场条件确定行权价和仓位
    3. 买入新的深度虚值看跌期权
    """
    
    def __init__(self, params: StrategyParams = None):
        self.params = params or StrategyParams()
        self.state = StrategyState()
    
    def _get_volatility(self, returns: pd.Series, date: pd.Timestamp) -> float:
        """获取指定日期的波动率估计"""
        p = self.params
        
        hist_data = returns[:date]
        if len(hist_data) < p.vol_window:
            return np.clip(hist_data.std() * np.sqrt(252), p.vol_min, p.vol_max)
        
        if p.vol_method == 'ewma':
            vol_series = compute_ewma_volatility(returns[:date], span=p.vol_window)
        elif p.vol_method == 'garch_proxy':
            from .option_pricing import compute_garch_volatility_proxy
            vol_series = compute_garch_volatility_proxy(returns[:date], window=p.vol_window)
        else:  # historical
            vol_series = compute_historical_volatility(returns[:date], window=p.vol_window)
        
        vol = vol_series.iloc[-1]
        if pd.isna(vol) or vol <= 0:
            vol = hist_data.std() * np.sqrt(252)
        
        return np.clip(vol, p.vol_min, p.vol_max)
    
    def _determine_strike(self, spot: float, vol: float, date: pd.Timestamp) -> float:
        """确定行权价"""
        p = self.params
        T = p.tenor_days / 365.0
        
        if p.strike_method == StrikeMethod.FIXED_MONEYNESS:
            return strike_from_moneyness(spot, p.moneyness)
        elif p.strike_method == StrikeMethod.VOL_ADJUSTED_DELTA:
            # 高波动时用更虚值的行权价（更便宜），低波动时用稍近的行权价
            vol_percentile_val = 0.5  # 默认中位数
            base_delta = p.delta
            adj_delta = base_delta * (0.5 + vol_percentile_val)  # vol高→delta小→更虚值
            return strike_from_delta(spot, T, p.risk_free_rate, vol, adj_delta)
        else:  # FIXED_DELTA
            return strike_from_delta(spot, T, p.risk_free_rate, vol, p.delta)
    
    def _determine_quantity(self, spot: float, option_price: float, 
                            vol: float, returns: pd.Series, date: pd.Timestamp,
                            portfolio_value: float = 100.0) -> Tuple[float, float]:
        """
        确定合约数量和对冲名义本金。
        
        核心逻辑：
        - 权利金率 = option_price / spot（每单位名义本金的对冲成本）
        - 预算 = portfolio_value * premium_budget_pct
        - 可对冲名义本金 = 预算 / 权利金率
        - 合约数量 = 可对冲名义本金 / spot
        
        Parameters
        ----------
        portfolio_value : float
            当前组合市值（默认 100）
        
        Returns
        -------
        (quantity, notional_hedged)
        """
        p = self.params
        premium_rate = option_price / spot if spot > 0 else 0  # 每元名义本金的权利金成本
        
        if p.sizing_method == PositionSizing.FIXED_NOTIONAL:
            # 全额对冲：对冲名义本金 = 组合市值
            notional_hedged = portfolio_value * p.notional_hedge_pct
            quantity = notional_hedged / spot if spot > 0 else 0
        
        elif p.sizing_method == PositionSizing.FIXED_PREMIUM:
            # 固定权利金预算（年化 → 每期）：预算 = 组合市值 * 年化预算% / 年滚动次数
            periods_per_year = 252 / p.roll_frequency_days
            period_budget_pct = p.premium_budget_pct / periods_per_year
            premium_budget = portfolio_value * period_budget_pct
            # 可对冲名义本金 = 预算 / 单位名义对冲成本
            notional_hedged = premium_budget / premium_rate if premium_rate > 0 else 0
            quantity = notional_hedged / spot if spot > 0 else 0
        
        elif p.sizing_method == PositionSizing.VOL_ADJUSTED:
            # 波动率调整：vol 低时多买
            periods_per_year = 252 / p.roll_frequency_days
            period_budget_pct = p.premium_budget_pct / periods_per_year
            base_budget = portfolio_value * period_budget_pct
            vol_percentile_val = volatility_percentile(vol, returns[:date], p.vol_window)
            if vol_percentile_val < p.vol_percentile_threshold:
                scale = min(p.vol_scale_multiplier, 
                           p.vol_percentile_threshold / max(vol_percentile_val, 0.01))
            else:
                scale = 1.0
            adj_budget = base_budget * scale
            notional_hedged = adj_budget / premium_rate if premium_rate > 0 else 0
            quantity = notional_hedged / spot if spot > 0 else 0
        
        elif p.sizing_method == PositionSizing.VOL_PERCENTILE:
            periods_per_year = 252 / p.roll_frequency_days
            period_budget_pct = p.premium_budget_pct / periods_per_year
            vol_percentile_val = volatility_percentile(vol, returns[:date], p.vol_window)
            base_budget = portfolio_value * period_budget_pct
            scale = 1.0 + (1.0 - vol_percentile_val) * (p.vol_scale_multiplier - 1.0)
            adj_budget = base_budget * scale
            notional_hedged = adj_budget / premium_rate if premium_rate > 0 else 0
            quantity = notional_hedged / spot if spot > 0 else 0
        
        elif p.sizing_method == PositionSizing.KELLY:
            periods_per_year = 252 / p.roll_frequency_days
            period_budget_pct = p.premium_budget_pct / periods_per_year
            base_budget = portfolio_value * period_budget_pct
            notional_hedged = base_budget / premium_rate if premium_rate > 0 else 0
            quantity = notional_hedged / spot if spot > 0 else 0
            quantity *= p.kelly_fraction
            notional_hedged *= p.kelly_fraction
        
        else:
            notional_hedged = 0.0
            quantity = 0.0
        
        return quantity, notional_hedged
    
    def run(self, price_data: pd.Series, start_date: str = None, end_date: str = None,
            progress: bool = False) -> pd.DataFrame:
        """
        运行策略回测。
        
        Parameters
        ----------
        price_data : pd.Series
            标的指数价格序列（index=date, values=price）
        start_date, end_date : str
            回测起止日期
        progress : bool
            是否打印进度
        
        Returns
        -------
        pd.DataFrame
            回测结果（日频）
        """
        p = self.params
        
        # 初始状态
        self.state = StrategyState()
        
        # 计算对数收益率
        log_returns = np.log(price_data / price_data.shift(1))
        
        # 确定回测范围
        if start_date:
            start_dt = pd.Timestamp(start_date)
        else:
            start_dt = price_data.index[p.vol_window + 10]  # 给波动率估计留足数据
        
        if end_date:
            end_dt = pd.Timestamp(end_date)
        else:
            end_dt = price_data.index[-1]
        
        mask = (price_data.index >= start_dt) & (price_data.index <= end_dt)
        backtest_dates = price_data.index[mask]
        
        if len(backtest_dates) == 0:
            raise ValueError(f"回测区间无数据: {start_dt} ~ {end_dt}")
        
        # 模拟 100 元初始本金（归一化）
        initial_nav = 100.0
        current_nav = initial_nav  # 当前组合净值（用于仓位计算）
        
        # 日频记录
        results = []
        next_roll_date = backtest_dates[0]  # 第一个滚动日
        
        # 按月滚动（每 p.roll_frequency_days 个交易日）
        roll_indices = list(range(0, len(backtest_dates), p.roll_frequency_days))
        roll_dates = [backtest_dates[i] for i in roll_indices]
        
        # T+1 到期的模拟：tenor_days 日历日 → 约 tenor_days * 21/30 个交易日
        tenor_trading_days = int(p.tenor_days * 21 / 30)
        
        pos_idx = 0
        for i, date in enumerate(backtest_dates):
            spot = price_data.loc[date]
            
            # --- 到期结算 ---
            # 检查是否有期权今天到期
            to_settle = []
            for pid, pos in list(self.state.active_positions.items()):
                if date >= pos.expiry_date:
                    # 到期结算：payoff = max(strike - spot, 0) * quantity
                    # quantity = notional_hedged / entry_spot, so payoff is in dollar terms
                    intrinsic = max(pos.strike - spot, 0)
                    payoff = intrinsic * pos.quantity
                    pos.exit_date = date
                    pos.exit_price = intrinsic
                    pos.pnl = payoff - pos.entry_price * pos.quantity
                    pos.pnl_pct_notional = pos.pnl / pos.notional_hedged if pos.notional_hedged > 0 else 0
                    
                    self.state.cumulative_payoff += payoff
                    to_settle.append(pid)
                    
                    if progress and intrinsic > 0:
                        print(f"  [{date.strftime('%Y-%m-%d')}] PUT 到期结算: "
                              f"spot={spot:.1f} strike={pos.strike:.1f} "
                              f"payoff={payoff:.4f} pnl={pos.pnl:.4f}")
            
            for pid in to_settle:
                del self.state.active_positions[pid]
            
            # --- 滚动买入 ---
            if date in roll_dates:
                # 获取波动率
                vol = self._get_volatility(log_returns, date)
                
                # 确定行权价
                strike = self._determine_strike(spot, vol, date)
                
                # 定价
                T = p.tenor_days / 365.0
                option_price = black_scholes_put(spot, strike, T, p.risk_free_rate, vol)
                
                # 确定仓位（基于固定初始本金，避免顺周期效应）
                quantity, notional_hedged = self._determine_quantity(
                    spot, option_price, vol, log_returns, date,
                    portfolio_value=initial_nav)  # 固定基准，不在熊市缩减保护
                
                # 交易成本（实际支付的 premium）
                premium_cost = option_price * quantity  # quantity 已经以 spot 为单位归一化
                txn_cost = premium_cost * p.transaction_cost_pct
                total_cost = premium_cost + txn_cost
                
                # 记录头寸
                expiry_date = date + pd.Timedelta(days=p.tenor_days)
                expiry_date_idx = backtest_dates.get_indexer([expiry_date], method='bfill')[0]
                if expiry_date_idx < len(backtest_dates):
                    expiry_date = backtest_dates[expiry_date_idx]
                
                pos = OptionPosition(
                    entry_date=date,
                    expiry_date=expiry_date,
                    strike=strike,
                    entry_spot=spot,
                    entry_price=option_price,
                    quantity=quantity,
                    notional_hedged=notional_hedged,
                    delta_at_entry=black_scholes_delta(spot, strike, T, p.risk_free_rate, vol),
                    vol_at_entry=vol,
                )
                
                self.state.active_positions[pos_idx] = pos
                self.state.positions.append(pos)
                self.state.cumulative_premium_paid += total_cost
                pos_idx += 1
            
            # --- 日终 NAV 计算 ---
            # NAV = 初始本金 + 累计赔付 - 累计权利金支出 + 未实现损益
            # 简化：NAV = 初始 - 累计权利金 + 累计赔付
            # （未实现损益在 deep OTM 情况下通常很小，且我们持有至到期）
            unrealized_pnl = 0.0
            for pid, pos in list(self.state.active_positions.items()):
                T_remaining = max((pos.expiry_date - date).days / 365.0, 1/365.0)
                vol_current = self._get_volatility(log_returns, date)
                mark_price = black_scholes_put(
                    spot, pos.strike, T_remaining, p.risk_free_rate, vol_current)
                unrealized_pnl += (mark_price - pos.entry_price) * pos.quantity
            
            # NAV = 初始本金 + 指数收益 - 累计权利金 + 累计赔付 + 未实现损益
            spot_return_since_start = spot / price_data.loc[backtest_dates[0]] - 1.0
            equity_nav = initial_nav * (1 + spot_return_since_start)
            nav = (equity_nav 
                   - self.state.cumulative_premium_paid 
                   + self.state.cumulative_payoff
                   + unrealized_pnl)
            current_nav = nav
            
            # 裸多头对比
            protected_nav = nav
            
            results.append({
                'date': date,
                'spot': spot,
                'nav': nav,
                'protected_nav': protected_nav,
                'cumulative_premium': self.state.cumulative_premium_paid,
                'cumulative_payoff': self.state.cumulative_payoff,
                'cumulative_pnl': self.state.cumulative_payoff - self.state.cumulative_premium_paid,
                'active_positions': len(self.state.active_positions),
                'unrealized_pnl': unrealized_pnl,
            })
        
        df = pd.DataFrame(results).set_index('date')
        
        # 计算一些衍生指标
        df['spot_return'] = df['spot'] / df['spot'].iloc[0] - 1.0
        df['nav_return'] = df['nav'] / df['nav'].iloc[0] - 1.0
        df['hedge_pnl'] = df['cumulative_pnl']  # 保护组合 P&L
        
        return df
    
    def get_trade_log(self) -> pd.DataFrame:
        """获取交易日志"""
        trades = []
        for pos in self.state.positions:
            trades.append({
                'entry_date': pos.entry_date,
                'expiry_date': pos.expiry_date,
                'exit_date': pos.exit_date,
                'strike': pos.strike,
                'entry_spot': pos.entry_spot,
                'entry_price': pos.entry_price,
                'moneyness': pos.strike / pos.entry_spot,
                'delta': pos.delta_at_entry,
                'vol': pos.vol_at_entry,
                'quantity': pos.quantity,
                'notional_hedged': pos.notional_hedged,
                'premium_paid': pos.entry_price * pos.quantity,
                'payoff': pos.exit_price * pos.quantity,
                'pnl': pos.pnl,
                'pnl_pct': pos.pnl_pct_notional,
            })
        return pd.DataFrame(trades)
