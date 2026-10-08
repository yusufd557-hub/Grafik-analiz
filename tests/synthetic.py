"""Testler için bilinen şekilli sentetik mum serileri."""

from __future__ import annotations

import numpy as np
import pandas as pd


def path_frame(
    anchors: list[tuple[int, float]],
    wick: float = 0.3,
    noise: float = 0.0,
    seed: int = 0,
    freq: str = "1h",
    volume: float = 100.0,
) -> pd.DataFrame:
    """Kapanışları `anchors` noktaları arasında doğrusal giden mum serisi.

    Açılış önceki kapanıştır; fitiller gövdenin `wick` kadar dışına çıkar.
    """
    bars = np.arange(anchors[-1][0] + 1)
    close = np.interp(bars, [a[0] for a in anchors], [a[1] for a in anchors])
    if noise:
        close = close + np.random.default_rng(seed).normal(0, noise, len(close))
    open_ = np.concatenate([[close[0]], close[:-1]])
    high = np.maximum(open_, close) + wick
    low = np.minimum(open_, close) - wick
    index = pd.date_range("2024-01-01", periods=len(bars), freq=freq, tz="UTC")
    return pd.DataFrame(
        {"open": open_, "high": high, "low": low, "close": close, "volume": np.full(len(bars), volume)},
        index=index,
    )


def mirror(anchors: list[tuple[int, float]], around: float = 100.0) -> list[tuple[int, float]]:
    """Fiyatı yatay eksende ters çevirir (tepe formasyonunu dip formasyonuna çevirir)."""
    return [(i, 2 * around - p) for i, p in anchors]


def random_walk(n: int = 3000, seed: int = 7, freq: str = "1h") -> pd.DataFrame:
    """Oynaklığı değişen, gerçekçi görünümlü rastgele yürüyüş."""
    rng = np.random.default_rng(seed)
    vol = 0.01 * np.exp(np.cumsum(rng.normal(0, 0.05, n)).clip(-1.5, 1.5))
    returns = rng.standard_t(4, n) * vol / 2
    close = 100 * np.exp(np.cumsum(returns))
    open_ = np.concatenate([[close[0]], close[:-1]])
    spread = np.abs(rng.normal(0, vol, n)) * close
    high = np.maximum(open_, close) + spread * rng.random(n)
    low = np.minimum(open_, close) - spread * rng.random(n)
    volume = rng.lognormal(5, 0.5, n)
    index = pd.date_range("2023-01-01", periods=n, freq=freq, tz="UTC")
    return pd.DataFrame({"open": open_, "high": high, "low": low, "close": close, "volume": volume}, index=index)


DOUBLE_TOP = [(0, 70), (30, 100), (45, 85), (60, 100), (95, 62)]

HEAD_SHOULDERS = [(0, 70), (25, 95), (35, 85), (50, 105), (65, 85), (75, 95), (115, 55)]

ASCENDING_TRIANGLE = [(0, 70), (20, 100), (30, 85), (40, 100), (50, 90), (60, 100), (64, 95.5), (95, 125)]

BULL_FLAG = [(0, 80), (20, 70), (30, 100), (38, 92), (75, 140)]

CUP_HANDLE = [
    (0, 60), (15, 55), (35, 100), (45, 80), (55, 72), (65, 70), (75, 72), (85, 80), (95, 100),
    (101, 93), (140, 145),
]
