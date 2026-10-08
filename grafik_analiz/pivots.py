"""Salınım tepe ve dipleri (pivotlar): ATR tabanlı zigzag.

Fiyat son uç noktadan `eşik × ATR` kadar ters yöne gittiğinde o uç nokta
pivot olarak kesinleşir. Her pivot iki zaman taşır:

- `index`: tepenin/dibin oluştuğu bar,
- `confirmed`: pivotun **bilinebildiği** bar (ters hareketin eşiği geçtiği bar).

Formasyon tespiti yalnızca `confirmed <= t` olan pivotlarla yapılır; böylece
t anında bilinmeyen bir tepe/dip hiçbir zaman kullanılmaz. Tepe ve dipler
sırayla gelir (tepe, dip, tepe, ...).
"""

from __future__ import annotations

import bisect
from dataclasses import dataclass

import numpy as np

HIGH = 1
LOW = -1


@dataclass(frozen=True)
class Pivot:
    index: int
    price: float
    kind: int
    """+1 tepe, -1 dip."""
    confirmed: int
    """Pivotun kesinleştiği bar; henüz kesinleşmemiş uç noktada -1."""

    @property
    def is_high(self) -> bool:
        return self.kind == HIGH


@dataclass
class ZigZag:
    pivots: list[Pivot]
    provisional: Pivot | None
    """Son ayağın henüz kesinleşmemiş uç noktası (yalnızca çizim için)."""
    threshold: float

    def __post_init__(self) -> None:
        self._confirmed = [p.confirmed for p in self.pivots]

    def known_at(self, bar: int) -> list[Pivot]:
        """`bar` kapanışında bilinen pivotlar."""
        return self.pivots[: bisect.bisect_right(self._confirmed, bar)]

    def count_known_at(self, bar: int) -> int:
        return bisect.bisect_right(self._confirmed, bar)


def zigzag(high: np.ndarray, low: np.ndarray, atr: np.ndarray, threshold: float = 2.0) -> ZigZag:
    """ATR eşikli zigzag. Tamamen nedenseldir: t barındaki karar yalnızca ≤ t verisini kullanır."""
    high = np.asarray(high, dtype=float)
    low = np.asarray(low, dtype=float)
    atr = np.asarray(atr, dtype=float)
    n = len(high)
    finite = np.flatnonzero(np.isfinite(atr) & (atr > 0))
    if len(finite) == 0:
        return ZigZag([], None, threshold)

    start = int(finite[0])
    pivots: list[Pivot] = []
    direction = 0
    hi_val, hi_idx = high[start], start
    lo_val, lo_idx = low[start], start
    # Yön belli olduktan sonra: ext = ayağın uç noktası, opp = uçtan sonraki en ters değer.
    ext = opp = 0.0
    ext_idx = opp_idx = start
    last_atr = atr[start]

    for i in range(start + 1, n):
        if np.isfinite(atr[i]) and atr[i] > 0:
            last_atr = atr[i]
        thr = threshold * last_atr
        h, l = high[i], low[i]

        if direction == 0:
            if h > hi_val:
                hi_val, hi_idx = h, i
            if l < lo_val:
                lo_val, lo_idx = l, i
            high_rev = hi_idx < i and hi_val - l >= thr
            low_rev = lo_idx < i and h - lo_val >= thr
            if high_rev and (not low_rev or hi_idx <= lo_idx):
                pivots.append(Pivot(hi_idx, float(hi_val), HIGH, i))
                seg = low[hi_idx + 1 : i + 1]
                k = int(np.argmin(seg))
                direction, ext, ext_idx = LOW, float(seg[k]), hi_idx + 1 + k
                opp, opp_idx = _after(high, ext_idx, i, np.max, -np.inf)
            elif low_rev:
                pivots.append(Pivot(lo_idx, float(lo_val), LOW, i))
                seg = high[lo_idx + 1 : i + 1]
                k = int(np.argmax(seg))
                direction, ext, ext_idx = HIGH, float(seg[k]), lo_idx + 1 + k
                opp, opp_idx = _after(low, ext_idx, i, np.min, np.inf)
            continue

        if direction == HIGH:
            if h >= ext:
                ext, ext_idx = h, i
                opp, opp_idx = np.inf, i  # aynı barın dibi tepeden önce mi sonra mı bilinmez
            elif l < opp:
                opp, opp_idx = l, i
            if opp_idx > ext_idx and ext - opp >= thr:
                pivots.append(Pivot(ext_idx, float(ext), HIGH, i))
                direction, ext, ext_idx = LOW, float(opp), opp_idx
                opp, opp_idx = _after(high, ext_idx, i, np.max, -np.inf)
        else:
            if l <= ext:
                ext, ext_idx = l, i
                opp, opp_idx = -np.inf, i
            elif h > opp:
                opp, opp_idx = h, i
            if opp_idx > ext_idx and opp - ext >= thr:
                pivots.append(Pivot(ext_idx, float(ext), LOW, i))
                direction, ext, ext_idx = HIGH, float(opp), opp_idx
                opp, opp_idx = _after(low, ext_idx, i, np.min, np.inf)

    provisional = Pivot(ext_idx, float(ext), direction, -1) if direction != 0 else None
    return ZigZag(pivots, provisional, threshold)


def _after(values: np.ndarray, ext_idx: int, i: int, reducer, empty: float) -> tuple[float, int]:
    """Uç noktadan sonraki (uç bar hariç) barlarda en ters değer ve konumu."""
    if ext_idx >= i:
        return empty, ext_idx
    seg = values[ext_idx + 1 : i + 1]
    k = int(np.argmax(seg)) if reducer is np.max else int(np.argmin(seg))
    return float(seg[k]), ext_idx + 1 + k
