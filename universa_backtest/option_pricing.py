"""
期权定价模块 — Black-Scholes 欧式期权定价 + 隐含波动率估算

Universa 深度虚值看跌期权回测框架的核心定价引擎。
由于 A 股指数期权历史数据不可得，本模块使用 Black-Scholes 模型合成期权价格。
"""

import numpy as np
from scipy.stats import norm
from scipy.optimize import brentq
import pandas as pd


def black_scholes_put(S, K, T, r, sigma, q=0.0):
    """
    Black-Scholes 欧式看跌期权定价公式。
    
    Parameters
    ----------
    S : float or np.array
        标的现价
    K : float or np.array  
        行权价
    T : float or np.array
        到期时间（年化）
    r : float or np.array
        无风险利率（年化）
    sigma : float or np.array
        波动率（年化）
    q : float or np.array
        股息率（年化），A 股指数期权通常设为 0
    
    Returns
    -------
    price : float or np.array
        期权理论价格
    """
    if T <= 0:
        return np.maximum(K - S, 0)
    
    d1 = (np.log(S / K) + (r - q + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
    d2 = d1 - sigma * np.sqrt(T)
    
    put_price = K * np.exp(-r * T) * norm.cdf(-d2) - S * np.exp(-q * T) * norm.cdf(-d1)
    return np.maximum(put_price, K * np.exp(-r * T) - S)  # 不低于内在价值


def black_scholes_delta(S, K, T, r, sigma, q=0.0, option_type='put'):
    """
    Black-Scholes Delta。
    """
    if T <= 0:
        return -1.0 if option_type == 'put' else 1.0
    
    d1 = (np.log(S / K) + (r - q + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
    
    if option_type == 'put':
        return -np.exp(-q * T) * norm.cdf(-d1)
    else:
        return np.exp(-q * T) * norm.cdf(d1)


def strike_from_delta(S, T, r, sigma, target_delta, q=0.0, option_type='put'):
    """
    给定目标 Delta，反推行权价。
    
    对于看跌期权，target_delta 应为负值（如 -0.05 表示 5-delta put），
    但我们接受正数输入并自动转为负值。
    
    Parameters
    ----------
    target_delta : float
        目标 Delta 绝对值（如 0.05 表示 5-delta put）
    
    Returns
    -------
    K : float
        对应行权价
    """
    if target_delta > 0:
        target_delta = -target_delta  # 看跌期权 delta 为负
    
    # 使用 Newton-Raphson 方法求解
    # 初值：基于 delta ≈ -N(-d1) ≈ -N(-ln(S/K)/(sigma*sqrt(T)))
    # 近似：K ≈ S * exp(sigma * sqrt(T) * norm.ppf(|delta|))
    K_guess = S * np.exp(-sigma * np.sqrt(T) * norm.ppf(abs(target_delta)))
    
    # 边界：极端情况
    K_low = S * 0.01   # 几乎归零
    K_high = S * 2.0   # 深度实值（不会用到）
    
    def f(K):
        d = black_scholes_delta(S, K, T, r, sigma, q, option_type)
        return d - target_delta
    
    try:
        # 如果初值函数值符号相同，调整边界
        f_low = f(K_low)
        f_guess = f(K_guess)
        
        if f_low * f_guess > 0:
            # 扩大搜索范围
            K_low = S * 0.001
            f_low = f(K_low)
        
        f_high = f(K_high)
        if f_low * f_high > 0:
            # 二分法搜索
            K = brentq(f, K_low, K_high, xtol=1e-8)
        else:
            K = brentq(f, K_low, K_high if f_low * f_high < 0 else K_guess * 3, xtol=1e-8)
    except (ValueError, RuntimeError):
        # Fallback: 使用近似公式
        K = K_guess
    
    return K


def strike_from_moneyness(S, moneyness):
    """
    给定虚值程度，计算行权价。
    
    Parameters
    ----------
    moneyness : float
        行权价 / 现价比率，如 0.80 表示 80% OTM put
    """
    return S * moneyness


def compute_historical_volatility(returns, window=20, trading_days=252):
    """
    计算滚动历史波动率。
    
    Parameters
    ----------
    returns : pd.Series
        日对数收益率
    window : int
        滚动窗口（交易日）
    trading_days : int
        年化交易日数
    
    Returns
    -------
    pd.Series of annualized volatility
    """
    vol = returns.rolling(window=window).std() * np.sqrt(trading_days)
    return vol


def compute_ewma_volatility(returns, span=30, trading_days=252):
    """
    计算 EWMA 波动率（对近期赋予更高权重）。
    """
    vol = returns.ewm(span=span).std() * np.sqrt(trading_days)
    return vol


def compute_realized_volatility(returns, window=20, trading_days=252):
    """
    计算已实现波动率（使用 Parkinson 估计或简单标准差）。
    这里使用标准差作为代理。
    """
    return compute_historical_volatility(returns, window, trading_days)


def compute_garch_volatility_proxy(returns, window=20, trading_days=252):
    """
    GARCH(1,1) 波动率简易代理。
    在没有完整 GARCH 拟合的情况下，使用 EWMA 作为近似。
    
    lambda_param 对应 GARCH 的 persistence。
    """
    # GARCH(1,1) 长期方差 → EWMA 近似 (lambda ≈ alpha+beta)
    lambda_param = 0.94  # RiskMetrics 标准值
    vol_sq = returns.ewm(alpha=1 - lambda_param).var() * trading_days
    return np.sqrt(vol_sq)


# ==================== 波动率锥 (Volatility Cone) ====================

def compute_volatility_cone(returns, windows=[5, 10, 20, 60, 120, 252], 
                             trading_days=252, percentiles=[10, 25, 50, 75, 90]):
    """
    计算波动率锥：不同时间窗口下的波动率分位数分布。
    用于判断当前波动率在历史中的相对位置（便宜/昂贵）。
    
    Returns
    -------
    pd.DataFrame
        行=窗口，列=分位数
    """
    results = {}
    for w in windows:
        vol = compute_historical_volatility(returns, window=w, trading_days=trading_days)
        results[w] = {f'p{p}': np.nanpercentile(vol.dropna(), p) for p in percentiles}
    return pd.DataFrame(results).T


def volatility_percentile(current_vol, returns, window=20, trading_days=252):
    """
    计算当前波动率在历史波动率分布中的分位数。
    
    Returns
    -------
    float: 0-1 之间的分位数值
    """
    hist_vol = compute_historical_volatility(returns, window=window, trading_days=trading_days)
    hist_vol_clean = hist_vol.dropna()
    if len(hist_vol_clean) == 0:
        return 0.5
    percentile = (hist_vol_clean < current_vol).mean()
    return percentile
