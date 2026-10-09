"""Konumlanma ailesi, araştırma turu 2 ("t2_konumlanma").

Vadeli piyasanın konumlanma verilerine dayanan, BTC/ETH/SOL sürekli vadeli
sözleşmelerinde uzun/kısa stratejiler:

- açık pozisyon (OI) ve fiyat birlikte (``oi``),
- genel hesapların uzun/kısa oranı, karşıt (``kalabalik``),
- prim endeksi, karşıt (``prim``),
- taker alım payı (``taker``),
- en büyük hesaplarla genel hesapların oran farkı (``fark``),
- bunların birleşimi (``bilesik``).

Nedensellik:

- Konumlanma ölçüleri 5 dakikalıktır. t barında yalnız zaman damgası
  ``bar kapanışı − METRIC_LAG`` anına eşit ya da daha eski olan **son** kayıt
  kullanılır (kayıt ``METRIC_MAX_AGE``'den eskiyse değer yok sayılır). Kayıtlar
  ``signal_fn`` içinde ``scope="dev"`` ile yüklenir ve verilen mumların son
  barının kapanışına kadar açıkça kesilir; böylece ``assert_causal``'ın
  mumları kesmesi bu verileri de keser.
- Prim endeksi: barla aynı açılış zamanlı prim mumu, barla aynı anda kapanır;
  kapanış değeri kullanılır. Yine son barın kapanışına kadar kesilir.
- Taker alım payı vadeli mumun kendi ``taker_buy_base / volume`` alanından.
- Bütün normalizasyonlar geriye dönük kayan pencerelerledir (z-skor =
  (x − kayan ortalama) / kayan std). ``shift(-k)``, ortalanmış pencere ya da
  tam örneklem istatistiği kullanılmaz.

Pozisyon coin başına −1/0/+1; sepette bacak başına 1/3 sermaye (kaldıraç yok).

`specs()` yalnız dondurulup iç doğrulamada (dev_valid) bir kez ölçülen
yapılandırmaları döndürür (bkz. ``arastirma/tur2/t2_konumlanma/RAPOR.md``).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from grafik_analiz.research.evaluate import StrategySpec

FAMILY = "t2_konumlanma"

COINS = ("BTCUSDT", "ETHUSDT", "SOLUSDT")

BARS_PER_DAY = {"1h": 24, "4h": 6}

METRIC_LAG = pd.Timedelta(minutes=10)
"""Bar kapanışından bu kadar önceki (ya da daha eski) ölçüm kullanılır."""

METRIC_MAX_AGE = pd.Timedelta(hours=2)
"""Kullanılan ölçüm bundan eskiyse (veri boşluğu) değer yok sayılır."""

METRIC_COLS = ("oi", "oi_usdt", "top_hesap_oran", "top_pozisyon_oran", "genel_oran")

_CACHE: dict = {}
_CACHE_MAX = 48


# ---------------------------------------------------------------- yardımcılar


def coins_for(universe: str) -> tuple[str, ...]:
    if universe == "SEPET3":
        return COINS
    if universe == "SEPET2":
        return COINS[:2]
    return (universe,)


def legs_for(universe: str) -> tuple:
    return tuple(("futures", c) for c in coins_for(universe))


def _ns(index) -> np.ndarray:
    return pd.DatetimeIndex(index).as_unit("ns").asi8


def _step(frame: pd.DataFrame) -> pd.Timedelta:
    """Bar uzunluğu (kapanış zamanı açılıştan bir ms eksik tutulur)."""
    diff = (pd.to_datetime(frame["close_time"], utc=True) - frame.index).median()
    return pd.Timedelta(diff).ceil("min")


def _cache_get(key, fn):
    if key in _CACHE:
        return _CACHE[key]
    if len(_CACHE) >= _CACHE_MAX:
        _CACHE.clear()
    value = fn()
    _CACHE[key] = value
    return value


def _key(tag: str, symbol: str, index: pd.DatetimeIndex, step: pd.Timedelta) -> tuple:
    return (tag, symbol, len(index), int(_ns(index[:1])[0]), int(_ns(index[-1:])[0]), step.value)


def bar_metrics(symbol: str, index: pd.DatetimeIndex, step: pd.Timedelta, lag: pd.Timedelta = METRIC_LAG) -> pd.DataFrame:
    """Her bar için kapanıştan en az ``lag`` (varsayılan ``METRIC_LAG``) önceki son konumlanma ölçümü."""

    def compute() -> pd.DataFrame:
        from grafik_analiz.research.data import load_metrics

        out = pd.DataFrame(np.nan, index=index, columns=list(METRIC_COLS))
        if len(index) == 0:
            return out
        try:
            raw = load_metrics(symbol, scope="dev")
        except FileNotFoundError:
            return out
        # Açık kesme: verilen mumların son barının kapanışından önceki kayıtlar.
        raw = raw[raw.index < index[-1] + step]
        cutoff = _ns(index + step - lag)
        for col in METRIC_COLS:
            s = raw[col].astype(float)
            if col in ("oi", "oi_usdt"):
                s = s.where(s > 0)
            s = s.dropna()
            if s.empty:
                continue
            times = _ns(s.index)
            pos = np.searchsorted(times, cutoff, side="right") - 1
            ok = pos >= 0
            safe = np.clip(pos, 0, None)
            vals = s.to_numpy()[safe]
            age = cutoff - times[safe]
            ok &= age <= METRIC_MAX_AGE.value
            out[col] = np.where(ok, vals, np.nan)
        return out

    return _cache_get(_key("metrics", symbol, index, step) + (pd.Timedelta(lag).value,), compute)


def bar_premium(symbol: str, index: pd.DatetimeIndex, step: pd.Timedelta) -> pd.Series:
    """Barla aynı açılış zamanlı prim endeksi mumunun kapanışı."""

    def compute() -> pd.Series:
        from grafik_analiz.research.data import load_premium

        if len(index) == 0:
            return pd.Series(np.nan, index=index)
        iv = "1h" if step == pd.Timedelta(hours=1) else "4h"
        try:
            raw = load_premium(symbol, iv, scope="dev")
        except FileNotFoundError:
            return pd.Series(np.nan, index=index)
        # Açık kesme: son barın kapanışından sonra kapanan prim mumu kullanılmaz.
        raw = raw[pd.to_datetime(raw["close_time"], utc=True) < index[-1] + step]
        return raw["close"].astype(float).reindex(index)

    return _cache_get(_key("premium", symbol, index, step), compute)


def _z(x: pd.Series, window: int, center: bool = True) -> pd.Series:
    mp = max(10, window // 2)
    roll = x.rolling(window, min_periods=mp)
    sd = roll.std().replace(0.0, np.nan)
    if center:
        return (x - roll.mean()) / sd
    return x / sd


def _hold(events: np.ndarray, hold: int) -> np.ndarray:
    """Olay (+1/−1) sonrası ``hold`` bar boyunca o yönde kal; yeni olay eskisini ezer."""
    s = pd.Series(np.where(events != 0, events, np.nan), dtype=float)
    if hold > 1:
        s = s.ffill(limit=hold - 1)
    return s.fillna(0.0).to_numpy()


def _band(z: np.ndarray, enter: float, exit_: float) -> np.ndarray:
    """Histerezisli durum: z > enter → +1, z < −enter → −1; +1 iken z < exit_ olunca, −1 iken z > −exit_ olunca 0."""
    out = np.zeros(len(z))
    state = 0
    for i, v in enumerate(z):
        if not np.isfinite(v):
            state = 0
        else:
            if state == 1 and v < exit_:
                state = 0
            elif state == -1 and v > -exit_:
                state = 0
            if state == 0:
                if v > enter:
                    state = 1
                elif v < -enter:
                    state = -1
        out[i] = state
    return out


def _side(pos: np.ndarray, yon: str) -> np.ndarray:
    if yon == "uzun":
        return np.where(pos > 0, pos, 0.0)
    if yon == "kisa":
        return np.where(pos < 0, pos, 0.0)
    return pos


def _trend(pos: np.ndarray, close: pd.Series, days: int, bpd: int, mode: str) -> np.ndarray:
    """``ile``: uzun yalnız kapanış > SMA iken, kısa yalnız altındayken. ``karsi``: tersi."""
    if not days or mode == "yok":
        return pos
    n = int(days * bpd)
    sma = close.rolling(n, min_periods=n).mean().to_numpy()
    c = close.to_numpy()
    valid = np.isfinite(sma)
    up = valid & (c > sma)
    down = valid & (c < sma)
    if mode == "ile":
        keep = ((pos > 0) & up) | ((pos < 0) & down)
    else:
        keep = ((pos > 0) & down) | ((pos < 0) & up)
    return np.where(keep, pos, 0.0)


# ---------------------------------------------------------------- sinyaller


def _signal_oi(frame, met, bpd, k=6, w_gun=30, a=1.0, b=1.5, mod="tasfiye", tut=6, **_):
    w = int(w_gun * bpd)
    lc = np.log(frame["close"].astype(float))
    rk = lc - lc.shift(k)
    zr = _z(rk, w, center=False).to_numpy()
    loi = np.log(met["oi"])
    ok_ = loi - loi.shift(k)
    zo = _z(ok_, w).to_numpy()
    ev = np.zeros(len(frame))
    with np.errstate(invalid="ignore"):
        if mod in ("tasfiye", "ikisi"):
            ev = np.where((zo < -b) & (zr < -a), 1.0, ev)
            ev = np.where((zo < -b) & (zr > a), -1.0, ev)
        if mod in ("birikim", "ikisi"):
            ev = np.where((zo > b) & (zr > a), 1.0, ev)
            ev = np.where((zo > b) & (zr < -a), -1.0, ev)
    return _hold(ev, int(tut))


def _signal_kalabalik(frame, met, bpd, oran="genel", w_gun=30, c=1.5, cx=0.0, isaret=-1, **_):
    col = {"genel": "genel_oran", "top_hesap": "top_hesap_oran", "top_poz": "top_pozisyon_oran"}[oran]
    z = _z(np.log(met[col]), int(w_gun * bpd)).to_numpy()
    return isaret * _band(z, c, cx)


def _signal_prim(frame, prem, bpd, n=8, w_gun=30, c=1.5, cx=0.0, isaret=-1, **_):
    x = prem.rolling(int(n), min_periods=int(n)).mean()
    z = _z(x, int(w_gun * bpd)).to_numpy()
    return isaret * _band(z, c, cx)


def _signal_taker(frame, bpd, k=6, w_gun=30, c=1.5, cx=0.0, isaret=1, **_):
    tb = frame["taker_buy_base"].astype(float).rolling(int(k), min_periods=int(k)).sum()
    vol = frame["volume"].astype(float).rolling(int(k), min_periods=int(k)).sum()
    x = tb / vol.replace(0.0, np.nan)
    z = _z(x, int(w_gun * bpd)).to_numpy()
    return isaret * _band(z, c, cx)


def _signal_fark(frame, met, bpd, w_gun=30, c=1.5, cx=0.0, isaret=1, **_):
    w = int(w_gun * bpd)
    d = _z(np.log(met["top_pozisyon_oran"]), w) - _z(np.log(met["genel_oran"]), w)
    return isaret * _band(d.to_numpy(), c, cx)


def _signal_bilesik(frame, met, bpd, w_gun=7, k=24, w_taker_gun=30, c=1.0, cx=0.0, **_):
    """Kalabalık (genel oran, karşıt) ile taker akışının (izle) z-skorlarının ortalaması."""
    z1 = -_z(np.log(met["genel_oran"]), int(w_gun * bpd))
    tb = frame["taker_buy_base"].astype(float).rolling(int(k), min_periods=int(k)).sum()
    vol = frame["volume"].astype(float).rolling(int(k), min_periods=int(k)).sum()
    z2 = _z(tb / vol.replace(0.0, np.nan), int(w_taker_gun * bpd))
    score = (z1 + z2) / 2.0
    return _band(score.to_numpy(), c, cx)


def _signal_fiyat(frame, bpd, w_gun=7, c=1.0, cx=0.0, isaret=1, **_):
    """Kontrol: yalnız fiyat (log kapanışın kayan z-skoru); konumlanma verisi kullanmaz."""
    z = _z(np.log(frame["close"].astype(float)), int(w_gun * bpd)).to_numpy()
    return isaret * _band(z, c, cx)


def signal_fn(
    data: dict,
    funding: dict,
    kind: str = "oi",
    yon: str = "iki",
    trend_gun: int = 0,
    filtre: str = "yok",
    gecikme_dk: int = 10,
    **params,
) -> dict:
    out = {}
    for leg, frame in data.items():
        market, symbol = leg
        index = frame.index
        if len(index) < 3:
            out[leg] = pd.Series(0.0, index=index)
            continue
        step = _step(frame)
        bpd = int(round(pd.Timedelta(days=1) / step))
        lag = pd.Timedelta(minutes=max(int(gecikme_dk), int(METRIC_LAG / pd.Timedelta(minutes=1))))
        if kind == "oi":
            pos = _signal_oi(frame, bar_metrics(symbol, index, step, lag), bpd, **params)
        elif kind == "kalabalik":
            pos = _signal_kalabalik(frame, bar_metrics(symbol, index, step, lag), bpd, **params)
        elif kind == "prim":
            pos = _signal_prim(frame, bar_premium(symbol, index, step), bpd, **params)
        elif kind == "taker":
            pos = _signal_taker(frame, bpd, **params)
        elif kind == "bilesik":
            pos = _signal_bilesik(frame, bar_metrics(symbol, index, step, lag), bpd, **params)
        elif kind == "fiyat":
            pos = _signal_fiyat(frame, bpd, **params)
        elif kind == "fark":
            pos = _signal_fark(frame, bar_metrics(symbol, index, step, lag), bpd, **params)
        else:
            raise ValueError(f"bilinmeyen tür: {kind}")
        pos = _side(np.asarray(pos, dtype=float), yon)
        pos = _trend(pos, frame["close"].astype(float), int(trend_gun), bpd, filtre)
        out[leg] = pd.Series(pos, index=index, dtype=float)
    return out


# ---------------------------------------------------------------- yapılandırmalar


def make_spec(name: str, universe: str, interval: str, params: dict, description: str = "") -> StrategySpec:
    if not name.startswith(FAMILY + "_"):
        name = f"{FAMILY}_{name}"
    return StrategySpec(
        name=name,
        family=FAMILY,
        interval=interval,
        legs=legs_for(universe),
        signal_fn=signal_fn,
        params=dict(params),
        description=description,
    )


FROZEN: list = []
"""(ad, evren, dilim, parametreler, açıklama) — iç doğrulamadan önce dondurulanlar."""


def specs() -> list[StrategySpec]:
    """Dondurulan ve dev_valid'de bir kez değerlendirilen yapılandırmalar."""
    return [make_spec(name, universe, interval, dict(params), desc) for name, universe, interval, params, desc in FROZEN]
