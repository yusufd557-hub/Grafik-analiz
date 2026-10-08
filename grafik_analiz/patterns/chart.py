"""Klasik grafik formasyonları.

Formasyonlar zigzag pivotlarının dizilişinden tanınır. Her yeni pivot
kesinleştiğinde (yalnızca o ana kadar bilinen pivotlarla) son pivotlarda bir
formasyon aranır; bir pivotta en fazla bir formasyon kaydedilir ve öncelik
sırası `DETECTORS` listesindedir. Toleranslar ATR ve formasyon yüksekliğine
göre ölçeklenir, böylece aynı kurallar her coin ve zaman diliminde çalışır.

Hedefler klasik ölçülen hareket kuralıyla hesaplanır (Bulkowski,
*Encyclopedia of Chart Patterns*): kırılım noktasından formasyon yüksekliği
kadar. Kamalarda hedef kamanın başladığı seviyedir.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

import numpy as np

from ..pivots import HIGH, LOW, Pivot, ZigZag
from .base import FORMING, Formation, Line, resolve, supersede

NAMES: dict[str, str] = {
    "double_top": "İkili tepe",
    "double_bottom": "İkili dip",
    "triple_top": "Üçlü tepe",
    "triple_bottom": "Üçlü dip",
    "head_shoulders": "Omuz-baş-omuz",
    "inverse_head_shoulders": "Ters omuz-baş-omuz",
    "ascending_triangle": "Yükselen üçgen",
    "descending_triangle": "Alçalan üçgen",
    "symmetric_triangle": "Simetrik üçgen",
    "rising_wedge": "Yükselen kama",
    "falling_wedge": "Alçalan kama",
    "rectangle": "Dikdörtgen",
    "bull_flag": "Boğa bayrağı",
    "bear_flag": "Ayı bayrağı",
    "cup_handle": "Fincan-kulp",
    "inverse_cup_handle": "Ters fincan-kulp",
}


@dataclass(frozen=True)
class Context:
    close: np.ndarray
    high: np.ndarray
    low: np.ndarray
    atr: float
    t: int
    scale: float


def _kinds(pivots: list[Pivot]) -> tuple[int, ...]:
    return tuple(p.kind for p in pivots)


def _make(key: str, bias: int, ctx: Context, pts: list[Pivot], **kw) -> Formation:
    return Formation(
        key=key,
        name=NAMES[key],
        bias=bias,
        scale=ctx.scale,
        start_index=pts[0].index,
        end_index=pts[-1].index,
        detected_index=ctx.t,
        points=[(p.index, p.price) for p in pts],
        **kw,
    )


def _closes_inside(ctx: Context, upper: Line, lower: Line, start: int, end: int, tol: float, max_out: float = 0.1) -> bool:
    if end <= start:
        return True
    idx = np.arange(start, end + 1)
    seg = ctx.close[start : end + 1]
    outside = (seg > upper.at(idx) + tol) | (seg < lower.at(idx) - tol)
    return outside.mean() <= max_out


def _not_broken_before_detection(ctx: Context, upper: Line | None, lower: Line | None, end_index: int) -> bool:
    """Son pivot ile tespit anı arasında sınır kapanışla aşılmamış olmalı."""
    if ctx.t - 1 <= end_index:
        return True
    idx = np.arange(end_index + 1, ctx.t)
    seg = ctx.close[end_index + 1 : ctx.t]
    if upper is not None and np.any(seg > upper.at(idx)):
        return False
    if lower is not None and np.any(seg < lower.at(idx)):
        return False
    return True


# ---------------------------------------------------------------- ikili / üçlü


def double(piv: list[Pivot], ctx: Context) -> Formation | None:
    if len(piv) < 4:
        return None
    prior, a, mid, b = piv[-4:]
    top = a.kind == HIGH
    sign = 1 if top else -1
    extreme_avg = (a.price + b.price) / 2
    height = (extreme_avg - mid.price) * sign
    if height <= 0 or b.index - a.index < 4:
        return None
    if abs(a.price - b.price) > max(0.5 * ctx.atr, 0.15 * height):
        return None
    # Önceki hareket formasyona doğru gelmiş olmalı (tepede yükseliş, dipte düşüş).
    if (prior.price - mid.price) * sign >= 0:
        return None
    worst = max(a.price, b.price) if top else min(a.price, b.price)
    upper = Line.horizontal(a.index, b.index, worst if top else mid.price)
    lower = Line.horizontal(a.index, b.index, mid.price if top else worst)
    d = -sign
    if not _not_broken_before_detection(ctx, upper, lower, b.index):
        return None
    return _make(
        "double_top" if top else "double_bottom",
        d,
        ctx,
        [a, mid, b],
        upper=upper,
        lower=lower,
        allowed=(d,),
        height=height,
        expiry_index=b.index + max(int(1.5 * (b.index - a.index)), 5),
        stop_levels={d: worst},
    )


def triple(piv: list[Pivot], ctx: Context) -> Formation | None:
    if len(piv) < 6:
        return None
    prior, a, m1, b, m2, c = piv[-6:]
    top = a.kind == HIGH
    sign = 1 if top else -1
    extremes = np.array([a.price, b.price, c.price])
    mids = np.array([m1.price, m2.price])
    neck = mids.min() if top else mids.max()
    height = (extremes.mean() - neck) * sign
    if height <= 0:
        return None
    tol = max(0.5 * ctx.atr, 0.15 * height)
    if np.abs(extremes - extremes.mean()).max() > tol:
        return None
    if abs(m1.price - m2.price) <= tol:
        return None  # dipler de eşitse dikdörtgendir
    if (prior.price - neck) * sign >= 0:
        return None
    worst = extremes.max() if top else extremes.min()
    upper = Line.horizontal(a.index, c.index, worst if top else neck)
    lower = Line.horizontal(a.index, c.index, neck if top else worst)
    d = -sign
    if not _not_broken_before_detection(ctx, upper, lower, c.index):
        return None
    return _make(
        "triple_top" if top else "triple_bottom",
        d,
        ctx,
        [a, m1, b, m2, c],
        upper=upper,
        lower=lower,
        allowed=(d,),
        height=height,
        expiry_index=c.index + max(int(0.75 * (c.index - a.index)), 5),
        stop_levels={d: float(worst)},
    )


# ---------------------------------------------------------------- omuz-baş-omuz


def head_shoulders(piv: list[Pivot], ctx: Context) -> Formation | None:
    if len(piv) < 6:
        return None
    prior, ls, n1, head, n2, rs = piv[-6:]
    top = head.kind == HIGH
    sign = 1 if top else -1
    neckline = Line(n1.index, n1.price, n2.index, n2.price)
    height = (head.price - float(neckline.at(head.index))) * sign
    if height <= 0:
        return None
    # Baş iki omuzdan belirgin biçimde uç olmalı.
    shoulder_extreme = max(ls.price, rs.price) if top else min(ls.price, rs.price)
    if (head.price - shoulder_extreme) * sign < max(0.5 * ctx.atr, 0.1 * height):
        return None
    # Omuzlar boyun çizgisinin anlamlı ölçüde üstünde/altında ve birbirine yakın.
    for s in (ls, rs):
        if (s.price - float(neckline.at(s.index))) * sign < 0.3 * height:
            return None
    if abs(ls.price - rs.price) > max(ctx.atr, 0.35 * height):
        return None
    d1, d2 = head.index - ls.index, rs.index - head.index
    if d1 <= 0 or d2 <= 0 or not (1 / 3 <= d1 / d2 <= 3):
        return None
    if abs(n1.price - n2.price) > 0.5 * height:
        return None
    if (prior.price - min(n1.price, n2.price) if top else prior.price - max(n1.price, n2.price)) * sign >= 0:
        return None
    d = -sign
    guard = Line.horizontal(ls.index, rs.index, head.price)
    upper, lower = (guard, neckline) if top else (neckline, guard)
    if not _not_broken_before_detection(ctx, upper, lower, rs.index):
        return None
    return _make(
        "head_shoulders" if top else "inverse_head_shoulders",
        d,
        ctx,
        [ls, n1, head, n2, rs],
        upper=upper,
        lower=lower,
        allowed=(d,),
        height=height,
        expiry_index=rs.index + max(rs.index - ls.index, 5),
        stop_levels={d: rs.price},
    )


# ---------------------------------------------------------------- üçgen / kama / dikdörtgen


def _fit(points: list[Pivot]) -> tuple[Line, float]:
    x = np.array([p.index for p in points], dtype=float)
    y = np.array([p.price for p in points], dtype=float)
    slope, intercept = np.polyfit(x, y, 1)
    resid = float(np.abs(y - (slope * x + intercept)).max())
    i1, i2 = int(x[0]), int(x[-1])
    return Line(i1, float(slope * i1 + intercept), i2, float(slope * i2 + intercept)), resid


def consolidation(piv: list[Pivot], ctx: Context) -> Formation | None:
    if len(piv) < 5:
        return None
    pts = piv[-5:]
    highs = [p for p in pts if p.kind == HIGH]
    lows = [p for p in pts if p.kind == LOW]
    x0, x1 = pts[0].index, pts[-1].index
    width = x1 - x0
    if width < 8:
        return None
    upper, ru = _fit(highs)
    lower, rl = _fit(lows)
    h0 = float(upper.at(x0) - lower.at(x0))
    h1 = float(upper.at(x1) - lower.at(x1))
    if h0 <= 0 or h1 <= 0:
        return None
    fit_tol = max(0.5 * ctx.atr, 0.1 * h0)
    if ru > fit_tol or rl > fit_tol:
        return None

    flat_tol = max(0.5 * ctx.atr, 0.15 * h0)
    cu, cl = upper.slope * width, lower.slope * width

    def trend(change: float) -> int:
        return 0 if abs(change) <= flat_tol else (1 if change > 0 else -1)

    tu, tl = trend(cu), trend(cl)
    converging = h1 <= 0.8 * h0
    key: str | None = None
    abs_targets: dict[int, float] = {}
    if tu == 0 and tl == 0 and abs(h1 / h0 - 1) <= 0.3:
        key, bias = "rectangle", 0
    elif tu == 0 and tl == 1 and converging:
        key, bias = "ascending_triangle", 1
    elif tu == -1 and tl == 0 and converging:
        key, bias = "descending_triangle", -1
    elif tu == -1 and tl == 1 and converging:
        key, bias = "symmetric_triangle", 0
    elif tu == 1 and tl == 1 and converging:
        key, bias = "rising_wedge", -1
        abs_targets = {-1: float(lower.at(x0))}
    elif tu == -1 and tl == -1 and converging:
        key, bias = "falling_wedge", 1
        abs_targets = {1: float(upper.at(x0))}
    if key is None:
        return None

    if not _closes_inside(ctx, upper, lower, x0, x1, fit_tol):
        return None
    if not _not_broken_before_detection(ctx, upper, lower, x1):
        return None

    expiry = x1 + width
    if upper.slope != lower.slope:
        apex = x0 + h0 / (lower.slope - upper.slope)
        if apex > x1:
            expiry = min(expiry, int(apex))
    return _make(
        key,
        bias,
        ctx,
        pts,
        upper=upper,
        lower=lower,
        allowed=(1, -1),
        height=h0,
        expiry_index=max(expiry, x1 + 3),
        abs_targets=abs_targets,
    )


# ---------------------------------------------------------------- bayrak


def flag(piv: list[Pivot], ctx: Context) -> Formation | None:
    for size in (5, 3):
        found = _flag(piv, ctx, size)
        if found is not None:
            return found
    return None


def _flag(piv: list[Pivot], ctx: Context, size: int) -> Formation | None:
    if len(piv) < size:
        return None
    pts = piv[-size:]
    base, top = pts[0], pts[1]
    bull = top.kind == HIGH
    sign = 1 if bull else -1
    pole = (top.price - base.price) * sign
    pole_bars = top.index - base.index
    if pole <= 0 or pole_bars <= 0:
        return None
    if pole < 4 * ctx.atr or pole / pole_bars < 0.4 * ctx.atr:
        return None
    flag_pts = pts[1:]
    counter = [p for p in flag_pts if p.kind != top.kind]
    same = [p for p in flag_pts if p.kind == top.kind]
    deepest = min(p.price for p in counter) if bull else max(p.price for p in counter)
    if (top.price - deepest) * sign > 0.5 * pole:
        return None
    # Bayrak sırasında direğin ucu aşılmamalı.
    if any((p.price - top.price) * sign > 0.3 * ctx.atr for p in same[1:]):
        return None
    flag_bars = pts[-1].index - top.index
    if flag_bars < 2 or flag_bars > max(3 * pole_bars, 15):
        return None

    if len(same) >= 2:
        trigger = Line(same[0].index, same[0].price, same[-1].index, same[-1].price)
    else:
        trigger = Line.horizontal(top.index, pts[-1].index, top.price)
    guard = Line.horizontal(top.index, pts[-1].index, deepest)
    upper, lower = (trigger, guard) if bull else (guard, trigger)
    if not _not_broken_before_detection(ctx, upper, lower, pts[-1].index):
        return None
    return _make(
        "bull_flag" if bull else "bear_flag",
        sign,
        ctx,
        pts,
        upper=upper,
        lower=lower,
        allowed=(sign,),
        height=pole,
        expiry_index=pts[-1].index + max(flag_bars, 5),
        stop_levels={sign: deepest},
    )


# ---------------------------------------------------------------- fincan-kulp


def cup_handle(piv: list[Pivot], ctx: Context) -> Formation | None:
    if len(piv) < 5:
        return None
    prior, left, bottom, right, handle = piv[-5:]
    cup = left.kind == HIGH
    sign = 1 if cup else -1
    rim = (left.price + right.price) / 2
    depth = (rim - bottom.price) * sign
    if depth <= 0 or depth < 3 * ctx.atr:
        return None
    if abs(left.price - right.price) > max(0.5 * ctx.atr, 0.15 * depth):
        return None
    if (prior.price - bottom.price) * sign >= 0:
        return None
    retrace = (right.price - handle.price) * sign
    if retrace <= 0 or retrace > 0.5 * depth:
        return None
    handle_bars = handle.index - right.index
    cup_bars = right.index - left.index
    if handle_bars < 1 or cup_bars < 10 or cup_bars < 3 * handle_bars:
        return None
    # "U" şekli: kapanışların en az %40'ı fincanın dip üçte birlik bölgesinde.
    # Düz bir "V"de bu oran üçte birdir; yuvarlak dip daha uzun süre dipte kalır.
    seg = ctx.close[left.index : right.index + 1]
    near_bottom = ((seg - bottom.price) * sign <= depth / 3).mean()
    if near_bottom < 0.4:
        return None
    trigger = Line.horizontal(right.index, handle.index, right.price)
    guard = Line.horizontal(right.index, handle.index, handle.price)
    upper, lower = (trigger, guard) if cup else (guard, trigger)
    if not _not_broken_before_detection(ctx, upper, lower, handle.index):
        return None
    return _make(
        "cup_handle" if cup else "inverse_cup_handle",
        sign,
        ctx,
        [left, bottom, right, handle],
        upper=upper,
        lower=lower,
        allowed=(sign,),
        height=depth,
        expiry_index=handle.index + max(cup_bars // 2, 10),
        stop_levels={sign: handle.price},
    )


Detector = Callable[[list[Pivot], Context], Formation | None]

DETECTORS: tuple[Detector, ...] = (head_shoulders, triple, cup_handle, consolidation, flag, double)


def detect_chart_patterns(
    close: np.ndarray,
    high: np.ndarray,
    low: np.ndarray,
    atr: np.ndarray,
    zz: ZigZag,
) -> list[Formation]:
    """Bir zigzag ölçeğindeki bütün formasyonları bulur, kırılım ve sonuçlarını işler."""
    close = np.asarray(close, dtype=float)
    high = np.asarray(high, dtype=float)
    low = np.asarray(low, dtype=float)
    atr = np.asarray(atr, dtype=float)
    found: list[Formation] = []
    pivots = zz.pivots
    for k in range(len(pivots)):
        t = pivots[k].confirmed
        a = atr[t]
        if not np.isfinite(a) or a <= 0:
            continue
        window = pivots[max(0, k - 5) : k + 1]
        ctx = Context(close, high, low, float(a), t, zz.threshold)
        for detector in DETECTORS:
            formation = detector(window, ctx)
            if formation is None:
                continue
            if _already_tracked(found, formation):
                break
            if resolve(formation, close, high, low):
                _supersede_previous(found, formation)
                found.append(formation)
            break
    return found


def _already_tracked(found: list[Formation], new: Formation, lookback: int = 6) -> bool:
    """Aynı yapı kırılım beklerken kayan pivot penceresi onu yeniden bulursa tekrar sayılmaz."""
    return any(
        old.key == new.key
        and old.status_at(new.detected_index) == FORMING
        and _shared_points(old, new) >= 0.6
        for old in found[-lookback:]
    )


def _supersede_previous(found: list[Formation], new: Formation, lookback: int = 6) -> None:
    """Eski formasyonu kapsayan yeni bir formasyon gelince kırılmamış eskiyi kapatır.

    Örnek: ikili tepe üçüncü tepeyle üçlü tepeye dönüşür. Yeni formasyon
    eskisinin başlangıcını içermeli ve eskinin son pivotu yeninin noktaları
    arasında olmalıdır; büyük bir formasyonun içindeki küçük parça eskisini
    kapatmaz.
    """
    pivot_bars = {i for i, _ in new.points}
    for old in found[-lookback:]:
        if old.end_index in pivot_bars and old.end_index != new.end_index and new.start_index <= old.start_index:
            supersede(old, new.detected_index)


def _shared_points(a: Formation, b: Formation, tolerance: int = 2) -> float:
    """Küçük formasyonun noktalarından kaçının diğerinin bir noktasıyla çakıştığı (oran)."""
    small, large = (a, b) if len(a.points) <= len(b.points) else (b, a)
    bars = [i for i, _ in large.points]
    shared = sum(1 for i, _ in small.points if any(abs(i - j) <= tolerance for j in bars))
    return shared / len(small.points)


def merge_scales(groups: list[list[Formation]], min_shared: float = 0.6) -> list[Formation]:
    """Farklı ölçeklerde aynı yapının tekrarını eler.

    Aynı tipte iki formasyon aynı pivotta bitiyor ve noktalarının en az
    `min_shared` oranı aynı barlara denk geliyorsa aynı yapı sayılır ve **önce tespit edilen** tutulur
    (eşitlikte büyük ölçek). Seçim böylece nedensel kalır: bir formasyon,
    kendisinden sonra tespit edilecek bir başkası yüzünden geçmişte elenmez.
    """
    ordered = sorted((f for g in groups for f in g), key=lambda f: (f.detected_index, -f.scale, f.start_index))
    kept: list[Formation] = []
    for f in ordered:
        if not any(
            g.key == f.key
            and g.scale != f.scale
            and abs(g.end_index - f.end_index) <= 2
            and _shared_points(f, g) >= min_shared
            for g in kept
        ):
            kept.append(f)
    return kept
