"""Formasyonların geçmiş sonuç istatistikleri.

Bir formasyonun "hedefe ulaşma oranı" internette sıkça abartılı verilir;
burada aynı coin ve zaman diliminin kendi geçmişinden ölçülür. Hesap
nedenseldir: `as_of` barında yalnızca sonucu o ana kadar belli olmuş
formasyonlar sayılır.
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd

from .patterns.base import RESOLVED, STOPPED, TARGET, Formation
from .patterns.candles import SPECS


def wilson_interval(successes: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """İkiterimli oran için Wilson %95 güven aralığı."""
    if n == 0:
        return float("nan"), float("nan")
    p = successes / n
    denom = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return max(0.0, center - half), min(1.0, center + half)


def random_walk_baseline(f: Formation) -> float:
    """Yönsüz bir fiyat için hedefin stoptan önce görülme olasılığı: S / (H + S).

    H girişten hedefe, S girişten stopa uzaklıktır. Bu oran, fiyat hedef ya da
    stoptan birine **ulaştığında** geçerlidir; bu yüzden süresi dolan
    kırılımlar karşılaştırmanın dışında tutulur (`formation_stats`).
    """
    if f.breakout_price is None or f.target is None or f.stop is None:
        return float("nan")
    reward = (f.target - f.breakout_price) * f.direction
    risk = (f.breakout_price - f.stop) * f.direction
    if reward <= 0 or risk <= 0:
        return float("nan")
    return risk / (reward + risk)


def formation_stats(formations: list[Formation], as_of: int) -> pd.DataFrame:
    """Formasyon tipi ve kırılım yönü başına sonuç tablosu.

    `hit_rate` = hedef / (hedef + stop): hedef ya da stoptan birine ulaşan
    kırılımlar içinde hedefin payı. `baseline` aynı kırılımlar için rastgele
    hareket kıyasıdır (S/(H+S) ortalaması). Süresi dolanlar `timeout`
    sütununda ayrıca sayılır.
    """
    rows = []
    groups: dict[tuple[str, int], list[Formation]] = {}
    detected: dict[str, int] = {}
    for f in formations:
        if f.detected_index > as_of:
            continue
        detected[f.key] = detected.get(f.key, 0) + 1
        if f.breakout_index is not None and f.breakout_index <= as_of:
            groups.setdefault((f.key, f.direction), []).append(f)

    for (key, direction), items in sorted(groups.items()):
        resolved = [f for f in items if f.status_at(as_of) in RESOLVED]
        decided = [f for f in resolved if f.outcome in (TARGET, STOPPED)]
        hits = sum(1 for f in decided if f.outcome == TARGET)
        stops = len(decided) - hits
        timeouts = len(resolved) - len(decided)
        n = len(decided)
        lo, hi = wilson_interval(hits, n)
        baselines = [random_walk_baseline(f) for f in decided]
        baselines = [b for b in baselines if np.isfinite(b)]
        rows.append(
            {
                "key": key,
                "name": items[0].name,
                "direction": direction,
                "detected": detected.get(key, 0),
                "breakouts": len(items),
                "resolved": len(resolved),
                "decided": n,
                "target": hits,
                "stop": stops,
                "timeout": timeouts,
                "hit_rate": hits / n if n else float("nan"),
                "ci_low": lo,
                "ci_high": hi,
                "baseline": float(np.mean(baselines)) if baselines else float("nan"),
            }
        )
    columns = [
        "key", "name", "direction", "detected", "breakouts", "resolved", "decided",
        "target", "stop", "timeout", "hit_rate", "ci_low", "ci_high", "baseline",
    ]
    return pd.DataFrame(rows, columns=columns)


def lookup(stats: pd.DataFrame, key: str, direction: int) -> pd.Series | None:
    if stats.empty:
        return None
    match = stats[(stats["key"] == key) & (stats["direction"] == direction)]
    return None if match.empty else match.iloc[0]


def candle_stats(candles: pd.DataFrame, close: pd.Series, horizon: int, as_of: int) -> pd.DataFrame:
    """Mum formasyonundan `horizon` bar sonra fiyatın beklenen yönde olma oranı.

    Kıyas, aynı dönemdeki koşulsuz orandır: piyasa çoğunlukla yükseldiyse
    "yükseliş" formasyonlarının isabeti de yüksek görünür; anlamlı olan fark,
    formasyonun bu taban oranın üzerine ne kattığıdır.
    """
    values = close.to_numpy(dtype=float)
    n = len(values)
    fwd = np.full(n, np.nan)
    if n > horizon:
        fwd[:-horizon] = values[horizon:] / values[:-horizon] - 1.0
    usable = np.zeros(n, dtype=bool)
    usable[: max(0, as_of - horizon + 1)] = True
    usable &= np.isfinite(fwd)
    base_up = float(np.mean(fwd[usable] > 0)) if usable.any() else float("nan")
    base_down = float(np.mean(fwd[usable] < 0)) if usable.any() else float("nan")
    base_abs = float(np.mean(np.abs(fwd[usable]))) if usable.any() else float("nan")

    rows = []
    for spec in SPECS:
        mask = candles[spec.key].to_numpy(dtype=bool) & usable
        count = int(mask.sum())
        moves = fwd[mask]
        if spec.bias != 0 and count:
            success = float(np.mean(np.sign(moves) == spec.bias))
            base = base_up if spec.bias > 0 else base_down
            lo, hi = wilson_interval(int(round(success * count)), count)
            avg = float(np.mean(moves * spec.bias))
        else:
            success = base = lo = hi = float("nan")
            avg = float(np.mean(np.abs(moves))) if count else float("nan")
        rows.append(
            {
                "key": spec.key,
                "name": spec.name,
                "bias": spec.bias,
                "count": count,
                "success": success,
                "base": base,
                "edge": success - base if spec.bias != 0 else float("nan"),
                "ci_low": lo,
                "ci_high": hi,
                "avg_move": avg,
                "base_abs_move": base_abs,
            }
        )
    return pd.DataFrame(rows)
