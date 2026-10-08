"""Teknik göstergeler.

Bütün fonksiyonlar nedenseldir: t barındaki değer yalnızca t ve önceki
barlardan hesaplanır. Pandas serileri alır, aynı indeksle seri döndürür.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def sma(series: pd.Series, period: int) -> pd.Series:
    return series.rolling(period, min_periods=period).mean()


def ema(series: pd.Series, period: int) -> pd.Series:
    return series.ewm(span=period, adjust=False, min_periods=period).mean()


def rma(series: pd.Series, period: int) -> pd.Series:
    """Wilder ortalaması (RSI, ATR ve ADX'te kullanılan)."""
    return series.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean()


def true_range(df: pd.DataFrame) -> pd.Series:
    prev_close = df["close"].shift(1)
    ranges = pd.concat(
        [df["high"] - df["low"], (df["high"] - prev_close).abs(), (df["low"] - prev_close).abs()],
        axis=1,
    )
    return ranges.max(axis=1)


def atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    return rma(true_range(df), period)


def rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gain = rma(delta.clip(lower=0.0), period)
    loss = rma((-delta).clip(lower=0.0), period)
    rs = gain / loss.replace(0.0, np.nan)
    out = 100.0 - 100.0 / (1.0 + rs)
    # Hiç kayıp yoksa RSI 100'dür.
    return out.where(loss != 0.0, 100.0).where(gain.notna())


def macd(close: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> pd.DataFrame:
    line = ema(close, fast) - ema(close, slow)
    sig = line.ewm(span=signal, adjust=False, min_periods=signal).mean()
    return pd.DataFrame({"macd": line, "macd_signal": sig, "macd_hist": line - sig})


def bollinger(close: pd.Series, period: int = 20, width: float = 2.0) -> pd.DataFrame:
    mid = sma(close, period)
    std = close.rolling(period, min_periods=period).std(ddof=0)
    upper = mid + width * std
    lower = mid - width * std
    return pd.DataFrame(
        {
            "bb_mid": mid,
            "bb_upper": upper,
            "bb_lower": lower,
            "bb_width": (upper - lower) / mid,
            "bb_pos": (close - lower) / (upper - lower).replace(0.0, np.nan),
        }
    )


def stochastic(df: pd.DataFrame, period: int = 14, smooth_k: int = 3, smooth_d: int = 3) -> pd.DataFrame:
    lowest = df["low"].rolling(period, min_periods=period).min()
    highest = df["high"].rolling(period, min_periods=period).max()
    raw = 100.0 * (df["close"] - lowest) / (highest - lowest).replace(0.0, np.nan)
    k = raw.rolling(smooth_k, min_periods=smooth_k).mean()
    d = k.rolling(smooth_d, min_periods=smooth_d).mean()
    return pd.DataFrame({"stoch_k": k, "stoch_d": d})


def adx(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
    up = df["high"].diff()
    down = -df["low"].diff()
    plus_dm = up.where((up > down) & (up > 0), 0.0)
    minus_dm = down.where((down > up) & (down > 0), 0.0)
    tr = rma(true_range(df), period)
    plus_di = 100.0 * rma(plus_dm, period) / tr.replace(0.0, np.nan)
    minus_di = 100.0 * rma(minus_dm, period) / tr.replace(0.0, np.nan)
    dx = 100.0 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0.0, np.nan)
    return pd.DataFrame({"adx": rma(dx, period), "plus_di": plus_di, "minus_di": minus_di})


def obv(df: pd.DataFrame) -> pd.Series:
    direction = np.sign(df["close"].diff()).fillna(0.0)
    return (direction * df["volume"]).cumsum()


def cci(df: pd.DataFrame, period: int = 20) -> pd.Series:
    typical = (df["high"] + df["low"] + df["close"]) / 3.0
    mean = typical.rolling(period, min_periods=period).mean()
    values = typical.to_numpy(dtype=float)
    mad = np.full(len(values), np.nan)
    if len(values) >= period:
        windows = np.lib.stride_tricks.sliding_window_view(values, period)
        mad[period - 1 :] = np.abs(windows - windows.mean(axis=1, keepdims=True)).mean(axis=1)
    mad_series = pd.Series(mad, index=typical.index)
    return (typical - mean) / (0.015 * mad_series.replace(0.0, np.nan))


def mfi(df: pd.DataFrame, period: int = 14) -> pd.Series:
    typical = (df["high"] + df["low"] + df["close"]) / 3.0
    flow = typical * df["volume"]
    change = typical.diff()
    positive = flow.where(change > 0, 0.0).rolling(period, min_periods=period).sum()
    negative = flow.where(change < 0, 0.0).rolling(period, min_periods=period).sum()
    ratio = positive / negative.replace(0.0, np.nan)
    out = 100.0 - 100.0 / (1.0 + ratio)
    return out.where(negative != 0.0, 100.0).where(positive.notna())


def rolling_vwap(df: pd.DataFrame, period: int = 20) -> pd.Series:
    typical = (df["high"] + df["low"] + df["close"]) / 3.0
    pv = (typical * df["volume"]).rolling(period, min_periods=period).sum()
    vol = df["volume"].rolling(period, min_periods=period).sum()
    return pv / vol.replace(0.0, np.nan)


def donchian(df: pd.DataFrame, period: int = 20) -> pd.DataFrame:
    """Donchian kanalı. Mevcut bar hariç tutulur ki kırılma ölçülebilsin."""
    upper = df["high"].shift(1).rolling(period, min_periods=period).max()
    lower = df["low"].shift(1).rolling(period, min_periods=period).min()
    return pd.DataFrame({"dc_upper": upper, "dc_lower": lower})


def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Analizde ve grafikte kullanılan standart gösterge setini ekler."""
    out = df.copy()
    close = out["close"]
    out["atr"] = atr(out, 14)
    out["ema20"] = ema(close, 20)
    out["ema50"] = ema(close, 50)
    out["ema200"] = ema(close, 200)
    out["rsi"] = rsi(close, 14)
    out = out.join(macd(close))
    out = out.join(bollinger(close))
    out = out.join(stochastic(out))
    out = out.join(adx(out))
    out["obv"] = obv(out)
    out["cci"] = cci(out)
    out["mfi"] = mfi(out)
    out["vwap20"] = rolling_vwap(out)
    out = out.join(donchian(out))
    out["volume_ratio"] = out["volume"] / sma(out["volume"], 20)
    return out
