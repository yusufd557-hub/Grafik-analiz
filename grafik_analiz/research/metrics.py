"""Performans ölçüleri, blok bootstrap ve çoklu deneme düzeltmesi (Deflated Sharpe)."""

from __future__ import annotations

import math

import numpy as np
import pandas as pd
from scipy import stats

from .protocol import BOOTSTRAP_BLOCK_DAYS, BOOTSTRAP_SAMPLES


def window(series: pd.Series, start: pd.Timestamp | None, end: pd.Timestamp | None) -> pd.Series:
    out = series
    if start is not None:
        out = out[out.index >= start]
    if end is not None:
        out = out[out.index < end]
    return out


def daily_returns(returns: pd.Series) -> pd.Series:
    """Bar getirilerini UTC günlerine bileşik olarak toplar."""
    if returns.empty:
        return returns
    return (1.0 + returns).groupby(returns.index.floor("1D")).prod() - 1.0


def block_bootstrap_means(daily: np.ndarray, block: int = BOOTSTRAP_BLOCK_DAYS, samples: int = BOOTSTRAP_SAMPLES, seed: int = 12345) -> np.ndarray:
    """Dairesel blok bootstrap ile günlük ortalama dağılımı (otokorelasyonu korur)."""
    n = len(daily)
    if n == 0:
        return np.array([])
    block = max(1, min(block, n))
    rng = np.random.default_rng(seed)
    blocks = int(math.ceil(n / block))
    starts = rng.integers(0, n, size=(samples, blocks))
    offsets = np.arange(block)
    idx = (starts[:, :, None] + offsets[None, None, :]) % n
    idx = idx.reshape(samples, -1)[:, :n]
    return daily[idx].mean(axis=1)


def sharpe(daily: pd.Series | np.ndarray) -> float:
    d = np.asarray(daily, dtype=float)
    if len(d) < 2 or np.std(d, ddof=1) == 0:
        return float("nan")
    return float(np.mean(d) / np.std(d, ddof=1) * math.sqrt(365))


def deflated_sharpe(sr_annual: float, n_days: int, n_trials: int, sr_trials_var_annual: float, skew: float, kurt: float) -> float:
    """Bailey & López de Prado (2014) Deflated Sharpe oranı: olasılık (0–1).

    Denenen strateji sayısı arttıkça en iyi sonucun şansla bulunma ihtimali
    artar; DSR, gözlenen Sharpe'ın bu beklenen en büyük değerin üstünde olma
    olasılığıdır. Sharpe değerleri yıllık verilir, günlüğe çevrilerek kullanılır.
    """
    if n_days < 3 or not np.isfinite(sr_annual):
        return float("nan")
    sr = sr_annual / math.sqrt(365)
    var = max(sr_trials_var_annual, 0.0) / 365
    gamma = 0.5772156649
    if n_trials > 1 and var > 0:
        sr0 = math.sqrt(var) * ((1 - gamma) * stats.norm.ppf(1 - 1 / n_trials) + gamma * stats.norm.ppf(1 - 1 / (n_trials * math.e)))
    else:
        sr0 = 0.0
    denom = math.sqrt(max(1e-12, 1 - skew * sr + (kurt - 1) / 4 * sr * sr))
    return float(stats.norm.cdf((sr - sr0) * math.sqrt(n_days - 1) / denom))


def alpha_beta(daily: pd.Series, benchmark: pd.Series) -> dict:
    """Günlük getirilerin piyasa kıyasına göre OLS alfası (yıllık), betası ve alfa t değeri."""
    joined = pd.concat([daily.rename("s"), benchmark.rename("m")], axis=1).dropna()
    if len(joined) < 30 or joined["m"].std() == 0:
        return {"alfa": float("nan"), "beta": float("nan"), "alfa_t": float("nan")}
    x = joined["m"].to_numpy()
    y = joined["s"].to_numpy()
    X = np.column_stack([np.ones_like(x), x])
    coef, *_ = np.linalg.lstsq(X, y, rcond=None)
    resid = y - X @ coef
    dof = max(1, len(y) - 2)
    sigma2 = float(resid @ resid) / dof
    cov = sigma2 * np.linalg.inv(X.T @ X)
    t = coef[0] / np.sqrt(cov[0, 0]) if cov[0, 0] > 0 else float("nan")
    return {"alfa": float(coef[0] * 365), "beta": float(coef[1]), "alfa_t": float(t)}


def summarize(
    returns: pd.Series,
    trades: pd.DataFrame | None = None,
    exposure: pd.Series | None = None,
    costs: pd.Series | None = None,
    funding: pd.Series | None = None,
    start: pd.Timestamp | None = None,
    end: pd.Timestamp | None = None,
    confidence: float = 0.95,
) -> dict:
    """Bir dönem için net getiri ölçüleri."""
    r = window(returns, start, end)
    out: dict = {"start": None, "end": None, "days": 0}
    if r.empty:
        return out
    equity = (1.0 + r).cumprod()
    total = float(equity.iloc[-1] - 1.0)
    days = max(1.0, (r.index[-1] - r.index[0]).total_seconds() / 86400.0)
    years = days / 365.25
    daily = daily_returns(r)
    d = daily.to_numpy(dtype=float)
    boot = block_bootstrap_means(d)
    alpha = 1.0 - confidence
    downside = d[d < 0]
    out.update(
        {
            "start": str(r.index[0]),
            "end": str(r.index[-1]),
            "days": int(round(days)),
            "total_return": total,
            "cagr": float((1.0 + total) ** (1.0 / years) - 1.0) if total > -1 and years > 0 else float("nan"),
            "sharpe": sharpe(d),
            "sortino": float(np.mean(d) / np.sqrt(np.mean(downside**2)) * math.sqrt(365)) if len(downside) else float("nan"),
            "volatility": float(np.std(d, ddof=1) * math.sqrt(365)) if len(d) > 1 else float("nan"),
            "max_drawdown": float((equity / equity.cummax() - 1.0).min()),
            "mean_daily": float(np.mean(d)),
            "daily_lower": float(np.quantile(boot, alpha)) if len(boot) else float("nan"),
            "p_value": float(np.mean(boot <= 0)) if len(boot) else float("nan"),
            "skew": float(stats.skew(d)) if len(d) > 2 else float("nan"),
            "kurtosis": float(stats.kurtosis(d, fisher=False)) if len(d) > 3 else float("nan"),
        }
    )
    if exposure is not None:
        out["exposure"] = float((window(exposure, start, end).abs() > 0).mean())
    if costs is not None:
        out["total_costs"] = float(window(costs, start, end).sum())
    if funding is not None:
        out["total_funding"] = float(window(funding, start, end).sum())
    if trades is not None:
        t = trades
        if start is not None:
            t = t[t["entry_time"] >= start]
        if end is not None:
            t = t[t["entry_time"] < end]
        n = len(t)
        out["trades"] = int(n)
        if n:
            wins = t["net_return"] > 0
            gains = t.loc[wins, "net_return"].sum()
            losses = -t.loc[~wins, "net_return"].sum()
            best = float(t["net_return"].max())
            out.update(
                {
                    "win_rate": float(wins.mean()),
                    "avg_trade": float(t["net_return"].mean()),
                    "best_trade": best,
                    "profit_factor": float(gains / losses) if losses > 0 else float("inf"),
                    # En iyi tek işlem çıkarılırsa kalan bileşik getiri (yaklaşık).
                    "total_without_best": float((1.0 + total) / (1.0 + best) - 1.0) if best > -1 else float("nan"),
                    "avg_bars": float(t["bars"].mean()),
                }
            )
    return out
