"""Destek/direnç seviyeleri, trend çizgileri ve Fibonacci düzeltmeleri.

Hepsi belirli bir bar (`as_of`) kapanışında bilinen pivotlardan hesaplanır.
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations

import numpy as np

from .pivots import HIGH, LOW, Pivot

FIB_RATIOS = (0.0, 0.236, 0.382, 0.5, 0.618, 0.786, 1.0)


@dataclass(frozen=True)
class Level:
    price: float
    kind: str
    """"destek" (fiyatın altında) veya "direnç" (fiyatın üstünde)."""
    touches: int
    first_index: int
    last_index: int


@dataclass(frozen=True)
class Trendline:
    kind: str
    """"destek" (yükselen dipler) veya "direnç" (alçalan tepeler)."""
    i1: int
    p1: float
    i2: int
    p2: float
    touches: int

    @property
    def slope(self) -> float:
        return (self.p2 - self.p1) / (self.i2 - self.i1)

    def value_at(self, index: float) -> float:
        return self.p1 + self.slope * (index - self.i1)


@dataclass(frozen=True)
class FibRetracement:
    start_index: int
    start_price: float
    end_index: int
    end_price: float
    levels: dict[float, float]
    """Oran → fiyat. 0 = son uç nokta, 1 = salınımın başlangıcı."""


def support_resistance(
    pivots: list[Pivot],
    close: float,
    atr: float,
    as_of: int,
    lookback: int = 500,
    tolerance: float = 0.6,
    min_touches: int = 2,
    per_side: int = 4,
) -> list[Level]:
    """Yakın fiyatlarda kümelenen pivotlardan yatay seviyeler üretir.

    İki pivot `tolerance × ATR` mesafesindeyse aynı seviyeye dokunmuş sayılır.
    Fiyatın altındaki en yakın `per_side` destek ve üstündeki en yakın
    `per_side` direnç döner.
    """
    recent = [p for p in pivots if p.confirmed <= as_of and p.index >= as_of - lookback]
    if not recent or not np.isfinite(atr) or atr <= 0:
        return []
    ordered = sorted(recent, key=lambda p: p.price)
    clusters: list[list[Pivot]] = [[ordered[0]]]
    for pivot in ordered[1:]:
        cluster = clusters[-1]
        center = float(np.mean([p.price for p in cluster]))
        if pivot.price - center <= tolerance * atr:
            cluster.append(pivot)
        else:
            clusters.append([pivot])

    levels = []
    for cluster in clusters:
        if len(cluster) < min_touches:
            continue
        price = float(np.mean([p.price for p in cluster]))
        levels.append(
            Level(
                price=price,
                kind="destek" if price < close else "direnç",
                touches=len(cluster),
                first_index=min(p.index for p in cluster),
                last_index=max(p.index for p in cluster),
            )
        )
    below = sorted([lv for lv in levels if lv.price < close], key=lambda lv: close - lv.price)[:per_side]
    above = sorted([lv for lv in levels if lv.price >= close], key=lambda lv: lv.price - close)[:per_side]
    return below + above


def trendlines(
    pivots: list[Pivot],
    close: np.ndarray,
    atr: float,
    as_of: int,
    candidates: int = 8,
    tolerance: float = 0.3,
) -> list[Trendline]:
    """Kırılmamış en güçlü yükselen destek ve alçalan direnç çizgisi.

    Çizgi iki pivottan geçer. Geçerli sayılması için ikinci pivottan `as_of`a
    kadar hiçbir kapanışın çizginin `tolerance × ATR` ötesine geçmemesi
    gerekir. Birden fazla aday varsa en çok pivota değen, sonra en yeni olan
    seçilir.
    """
    known = [p for p in pivots if p.confirmed <= as_of]
    if not np.isfinite(atr) or atr <= 0:
        return []
    out: list[Trendline] = []
    for kind, label, rising in ((LOW, "destek", True), (HIGH, "direnç", False)):
        points = [p for p in known if p.kind == kind][-candidates:]
        best: tuple | None = None
        for a, b in combinations(points, 2):
            if (b.price > a.price) != rising or b.index == a.index:
                continue
            slope = (b.price - a.price) / (b.index - a.index)
            span = np.arange(b.index, as_of + 1)
            line = a.price + slope * (span - a.index)
            seg = close[b.index : as_of + 1]
            broken = np.any(seg < line - tolerance * atr) if rising else np.any(seg > line + tolerance * atr)
            if broken:
                continue
            touches = sum(
                1 for p in points if p.index >= a.index and abs(p.price - (a.price + slope * (p.index - a.index))) <= tolerance * atr
            )
            score = (touches, b.index)
            if best is None or score > best[0]:
                best = (score, Trendline(label, a.index, a.price, b.index, b.price, touches))
        if best is not None:
            out.append(best[1])
    return out


def fibonacci(pivots: list[Pivot], as_of: int) -> FibRetracement | None:
    """Son tamamlanmış salınımın Fibonacci düzeltme seviyeleri."""
    known = [p for p in pivots if p.confirmed <= as_of]
    if len(known) < 2:
        return None
    start, end = known[-2], known[-1]
    move = end.price - start.price
    levels = {ratio: end.price - ratio * move for ratio in FIB_RATIOS}
    return FibRetracement(start.index, start.price, end.index, end.price, levels)
