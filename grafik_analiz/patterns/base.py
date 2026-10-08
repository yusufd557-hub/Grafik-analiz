"""Formasyon kaydı ve kırılım/sonuç takibi.

Bir grafik formasyonunun yaşam döngüsü:

1. **oluşuyor** — geometri tamamlandı (son pivot kesinleşti), kırılım bekleniyor.
2. **kırılım** — kapanış sınır çizgisini geçti; hedef ve stop bu barda belirlenir.
3. Sonuç: **hedef** (hedefe stoptan önce ulaşıldı), **stop** (önce stop görüldü)
   veya **süre doldu** (izin verilen sürede ikisi de olmadı).

Kırılım hiç gelmezse **kırılımsız**, beklenen yönün tersine kırılırsa
**geçersiz** olur. Kırılımdan önce aynı pivotları kullanan yeni bir formasyon
tamamlanırsa (ör. ikili tepe üçlü tepeye dönüşürse) eskisi **dönüştü** olur. Her geçiş bir bar indeksine bağlıdır; `status_at(t)` bir
formasyonun t anında bilinen durumunu verir, böylece geçmiş istatistikler
geleceği görmeden hesaplanabilir.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

FORMING = "oluşuyor"
BROKEN = "kırılım"
TARGET = "hedef"
STOPPED = "stop"
TIMEOUT = "süre doldu"
NO_BREAKOUT = "kırılımsız"
INVALID = "geçersiz"
SUPERSEDED = "dönüştü"

RESOLVED = (TARGET, STOPPED, TIMEOUT)


@dataclass(frozen=True)
class Line:
    i1: int
    p1: float
    i2: int
    p2: float

    @property
    def slope(self) -> float:
        return 0.0 if self.i2 == self.i1 else (self.p2 - self.p1) / (self.i2 - self.i1)

    def at(self, index: float | np.ndarray) -> float | np.ndarray:
        return self.p1 + self.slope * (np.asarray(index, dtype=float) - self.i1)

    @classmethod
    def horizontal(cls, i1: int, i2: int, price: float) -> Line:
        return cls(i1, float(price), i2, float(price))


@dataclass
class Formation:
    key: str
    name: str
    bias: int
    """Formasyonun klasik beklenen yönü: +1 yükseliş, -1 düşüş, 0 iki yönlü."""
    scale: float
    """Tespitte kullanılan zigzag eşiği (ATR katı)."""
    start_index: int
    end_index: int
    """Formasyonu tanımlayan son pivotun barı."""
    detected_index: int
    """Formasyonun bilinebildiği bar (son pivotun kesinleştiği bar)."""
    points: list[tuple[int, float]]
    upper: Line | None
    lower: Line | None
    allowed: tuple[int, ...]
    """Geçerli kırılım yönleri. Diğer yöne kapanış formasyonu geçersiz kılar."""
    height: float
    """Ölçülen hareket: kırılım noktasından hedefe uzaklık."""
    expiry_index: int
    """Kırılımın gerçekleşebileceği son bar."""
    stop_levels: dict[int, float] = field(default_factory=dict)
    """Yön → stop (iptal) seviyesi. Yoksa karşı sınır çizgisi kullanılır."""
    abs_targets: dict[int, float] = field(default_factory=dict)
    """Yön → mutlak hedef (ör. kamada formasyon başlangıcı). Yoksa ölçülen hareket."""

    direction: int = 0
    breakout_index: int | None = None
    breakout_price: float | None = None
    target: float | None = None
    stop: float | None = None
    invalid_index: int | None = None
    superseded_index: int | None = None
    outcome: str | None = None
    outcome_index: int | None = None
    outcome_bars: int = 0

    @property
    def width(self) -> int:
        return self.end_index - self.start_index

    def status_at(self, t: int) -> str | None:
        """t barı kapanışında bilinen durum; formasyon henüz bilinmiyorsa None."""
        if t < self.detected_index:
            return None
        if self.breakout_index is None or self.breakout_index > t:
            if self.invalid_index is not None and self.invalid_index <= t:
                return INVALID
            if self.superseded_index is not None and self.superseded_index <= t:
                return SUPERSEDED
            if t >= self.expiry_index:
                return NO_BREAKOUT
            return FORMING
        if self.outcome is not None and self.outcome_index is not None and self.outcome_index <= t:
            return self.outcome
        return BROKEN

    def pending_levels(self, t: int) -> dict[int, dict[str, float]]:
        """Kırılım bekleyen formasyon için t barındaki tetik, hedef ve stop seviyeleri."""
        out: dict[int, dict[str, float]] = {}
        for d in self.allowed:
            trigger = self._boundary(d, t)
            if trigger is None:
                continue
            out[d] = {"trigger": trigger, "target": self._target(d, trigger), "stop": self._stop(d, t)}
        return out

    def _boundary(self, d: int, t: int) -> float | None:
        line = self.upper if d > 0 else self.lower
        return None if line is None else float(line.at(t))

    def _target(self, d: int, boundary: float) -> float:
        absolute = self.abs_targets.get(d)
        if absolute is not None and (absolute - boundary) * d > 0:
            return float(absolute)
        return float(boundary + d * self.height)

    def _stop(self, d: int, t: int) -> float:
        if d in self.stop_levels:
            return float(self.stop_levels[d])
        opposite = self.lower if d > 0 else self.upper
        if opposite is None:
            return float(self._boundary(d, t) - d * self.height)
        return float(opposite.at(t))


def supersede(old: Formation, at: int) -> bool:
    """Kırılmamış eski formasyonu `at` barında yenisine devreder."""
    if old.invalid_index is not None and old.invalid_index <= at:
        return False
    if old.breakout_index is not None and old.breakout_index < at:
        return False
    if old.expiry_index <= at:
        return False
    old.superseded_index = at
    old.invalid_index = None
    old.direction = 0
    old.breakout_index = old.breakout_price = old.target = old.stop = None
    old.outcome = old.outcome_index = None
    return True


def resolve(formation: Formation, close: np.ndarray, high: np.ndarray, low: np.ndarray) -> bool:
    """Kırılımı ve sonucu belirler. Formasyon geç tespit edildiyse False döner.

    Kırılım, `detected_index`'ten itibaren bir kapanışın sınır çizgisini
    geçmesidir; giriş fiyatı o barın kapanışıdır. Sonuç takibi kırılım
    barından **sonraki** bardan başlar. Aynı barda hem hedef hem stop
    görülürse sıra bilinmediği için stop sayılır (ihtiyatlı varsayım).
    """
    n = len(close)
    first = formation.detected_index
    last = min(formation.expiry_index, n - 1)
    if first > last:
        return True
    idx = np.arange(first, last + 1)
    seg = close[first : last + 1]
    up = seg > formation.upper.at(idx) if formation.upper is not None else np.zeros(len(idx), bool)
    dn = seg < formation.lower.at(idx) if formation.lower is not None else np.zeros(len(idx), bool)
    hits = np.flatnonzero(up | dn)
    if len(hits) == 0:
        return True
    j = int(idx[hits[0]])
    d = 1 if up[hits[0]] else -1
    if d not in formation.allowed:
        formation.invalid_index = j
        return True

    boundary = formation._boundary(d, j)
    # Formasyon bilindiğinde fiyat hareketin yarısını çoktan yapmışsa tespit
    # bayattır; bu durumda giriş gerçekçi olmaz.
    if j == first and (close[j] - boundary) * d > 0.5 * formation.height:
        return False

    formation.direction = d
    formation.breakout_index = j
    formation.breakout_price = float(close[j])
    formation.target = formation._target(d, boundary)
    formation.stop = formation._stop(d, j)
    formation.outcome_bars = max(2 * formation.width, 10)
    _track_outcome(formation, high, low)
    return True


def _track_outcome(formation: Formation, high: np.ndarray, low: np.ndarray) -> None:
    n = len(high)
    b = formation.breakout_index
    assert b is not None and formation.target is not None and formation.stop is not None
    end = b + formation.outcome_bars
    seg_end = min(end, n - 1)
    if seg_end <= b:
        return
    hi = high[b + 1 : seg_end + 1]
    lo = low[b + 1 : seg_end + 1]
    if formation.direction > 0:
        hit_target = hi >= formation.target
        hit_stop = lo <= formation.stop
    else:
        hit_target = lo <= formation.target
        hit_stop = hi >= formation.stop
    t_idx = int(np.argmax(hit_target)) if hit_target.any() else None
    s_idx = int(np.argmax(hit_stop)) if hit_stop.any() else None
    if s_idx is not None and (t_idx is None or s_idx <= t_idx):
        formation.outcome, formation.outcome_index = STOPPED, b + 1 + s_idx
    elif t_idx is not None:
        formation.outcome, formation.outcome_index = TARGET, b + 1 + t_idx
    elif end <= n - 1:
        formation.outcome, formation.outcome_index = TIMEOUT, end
