"""Fonlama ve carry ailesi ("fonlama_carry").

Vadeli (USDⓈ-M sürekli) fonlama oranlarına dayanan stratejiler.

Nedensellik: fonlama kaydı yalnızca zaman damgası barın **açılış** zamanına eşit
ya da ondan önceyse kullanılır (kapanış şartından daha sıkı; BTC/ETH kayıtları
00/08/16 UTC'de olduğundan 1s ve 4s barlarda ikisi aynıdır). Fonlama
özellikleri kayıt serisi üzerinde geriye dönük zaman pencereleriyle hesaplanır
ve bar zamanına "en son bilinen değer" olarak taşınır. Fiyat özellikleri
geriye dönük pencerelerle hesaplanır. `shift(-k)`, ortalanmış pencere, tam
örneklem istatistiği kullanılmaz. Coinin ilk fonlama kaydından önce hiçbir
bacakta pozisyon açılmaz (vadeli 1d verisi fonlamadan önce başlar).

Türler (``kind``):

- ``carry``: nakit-carry (cash-and-carry). Aynı coinde spot uzun + sürekli
  vadeli kısa; bacak ağırlıkları 0,5/0,5 (sepette her bacak 1/6), fiyat
  riski yaklaşık nötrdür, getiri fonlamadan gelir. ``n`` gün geriye bakan
  ortalama fonlama (8 saatlik eşdeğer oran) ``giris`` eşiğinin üstüne çıkınca
  girilir; ``cikis`` eşiğinin altına inince (``son_neg`` açıksa son yayımlanan
  kayıt negatif olunca da) çıkılır. ``n=0`` her zaman pozisyonda (taban
  çizgisi).
- ``yonlu``: fonlama uçlarından yönlü sinyal (yalnız vadeli bacak). Ortalama
  fonlama (mutlak eşik ya da geriye dönük ``W`` günlük yüzdelik sıra) çok
  yüksekse kalabalık uzun → kısa; çok düşük/negatifse kalabalık kısa → uzun
  (karşıt yön). İsteğe bağlı fiyat trendi filtresi (``filtre="ile"``: uzun
  yalnız kapanış > ``m`` günlük SMA iken, kısa yalnız altındayken). Sinyal
  ``tut`` gün boyunca geçerli kalır.
- ``kaplama``: spot uzun + vadeli bacakla dinamik koruma. Fonlama yüksekken
  (kalabalık) vadeli kısa açılır ve pozisyon nötr carry'ye döner; fonlama
  düşükken vadeli bacak ``uzun_poz`` (0 ya da 1) olur.

`specs()` yalnızca dondurulup dev_valid'de bir kez değerlendirilen
yapılandırmaları döndürür (bkz. `arastirma/fonlama_carry/RAPOR.md`).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from grafik_analiz.research.evaluate import StrategySpec

FAMILY = "fonlama_carry"

COINS = ("BTCUSDT", "ETHUSDT", "SOLUSDT")

BARS_PER_DAY = {"1h": 24, "4h": 6, "1d": 1}


# ---------------------------------------------------------------- yardımcılar


def coins_for(universe: str) -> tuple[str, ...]:
    if universe == "SEPET3":
        return COINS
    if universe == "SEPET2":
        return COINS[:2]
    return (universe,)


def legs_for(kind: str, universe: str) -> tuple:
    coins = coins_for(universe)
    if kind in ("carry", "kaplama"):
        return tuple(leg for c in coins for leg in (("spot", c), ("futures", c)))
    return tuple(("futures", c) for c in coins)


def _ns(index: pd.DatetimeIndex) -> np.ndarray:
    return index.as_unit("ns").asi8


def _asof(series: pd.Series, index: pd.DatetimeIndex) -> pd.Series:
    """Her bar zamanında (açılış), zaman damgası <= bar zamanı olan en son kayıt değeri."""
    if series.empty:
        return pd.Series(np.nan, index=index)
    pos = np.searchsorted(_ns(series.index), _ns(index), side="right") - 1
    vals = series.to_numpy(dtype=float)
    out = np.where(pos >= 0, vals[np.clip(pos, 0, None)], np.nan)
    return pd.Series(out, index=index)


def _fund_avg(f: pd.DataFrame, n_days: float) -> pd.Series:
    """Kayıt serisinde, geriye dönük `n_days` günlük fonlama toplamının 8 saatlik eşdeğer ortalaması.

    Pencere (t − n gün, t] aralığındaki kayıtları toplar; ilk n gün NaN'dır.
    Fonlama aralığı kısaldığında (ör. SOL 2022-11) toplam doğru zaman ağırlığını korur.
    """
    r = f["funding_rate"].astype(float)
    s = r.rolling(pd.Timedelta(days=n_days)).sum() / (3.0 * n_days)
    first = r.index.min()
    return s.where(r.index >= first + pd.Timedelta(days=n_days))


def _hysteresis(enter: np.ndarray, exit_: np.ndarray) -> np.ndarray:
    """Giriş şartında 1, çıkış şartında 0 (çıkış öncelikli), arada önceki durum."""
    s = pd.Series(np.where(exit_, 0.0, np.where(enter, 1.0, np.nan)))
    return s.ffill().fillna(0.0).to_numpy()


def _union_index(frames: list[pd.DataFrame]) -> pd.DatetimeIndex:
    idx = frames[0].index
    for fr in frames[1:]:
        idx = idx.union(fr.index)
    return idx


def _close_on(frame: pd.DataFrame, index: pd.DatetimeIndex) -> pd.Series:
    """Kapanış fiyatı, eksik barlarda en son bilinen kapanış (yalnız geçmiş)."""
    return frame["close"].reindex(index).ffill()


# ---------------------------------------------------------------- 1) carry


def _carry_state(index: pd.DatetimeIndex, f: pd.DataFrame, n: float, giris: float, cikis: float, son_neg: bool) -> np.ndarray:
    first = f.index.min() if not f.empty else None
    if first is None:
        return np.zeros(len(index))
    allowed = np.asarray(index >= first)
    if n == 0:
        return allowed.astype(float)
    F = _asof(_fund_avg(f, n), index).to_numpy()
    last = _asof(f["funding_rate"], index).to_numpy()
    with np.errstate(invalid="ignore"):
        enter = F > giris
        exit_ = (F < cikis) | np.isnan(F)
        if son_neg:
            exit_ = exit_ | (last < 0)
    state = _hysteresis(enter, exit_)
    return np.where(allowed, state, 0.0)


def carry_signal(data: dict, funding: dict, universe: str = "BTCUSDT", n: float = 3, giris: float = 0.0001,
                 cikis: float = 0.0, son_neg: bool = False, **_) -> dict:
    out = {}
    for c in coins_for(universe):
        spot = data[("spot", c)]
        fut = data[("futures", c)]
        idx = _union_index([spot, fut])
        state = pd.Series(_carry_state(idx, funding.get(c, pd.DataFrame()), n, giris, cikis, son_neg), index=idx)
        out[("spot", c)] = state.reindex(spot.index).astype(float)
        out[("futures", c)] = (-state).reindex(fut.index).astype(float)
    return out


# ---------------------------------------------------------------- 2) yönlü


def _rank_feature(f: pd.DataFrame, n: float, W: int) -> pd.Series:
    """`n` günlük ortalama fonlamanın son `W` günlük kayıtlar içindeki yüzdelik sırası (kayıt serisinde)."""
    F = _fund_avg(f, n)
    win = int(W * 3)
    return F.rolling(win, min_periods=win).rank(pct=True)


def yonlu_signal(data: dict, funding: dict, universe: str = "BTCUSDT", n: float = 3, olcek: str = "mutlak",
                 W: int = 180, alt: float = 0.0, ust: float = 0.0005, yon: str = "iki", filtre: str = "yok",
                 m: int = 100, tut: float = 3, **_) -> dict:
    out = {}
    for c in coins_for(universe):
        fut = data[("futures", c)]
        idx = fut.index
        f = funding.get(c, pd.DataFrame())
        if f.empty:
            out[("futures", c)] = pd.Series(0.0, index=idx)
            continue
        bpd = _bars_per_day(idx)
        X = _asof(_rank_feature(f, n, W) if olcek == "yuzdelik" else _fund_avg(f, n), idx).to_numpy()
        with np.errstate(invalid="ignore"):
            L = X < alt
            S = X > ust
        if filtre != "yok":
            close = fut["close"]
            sma = close.rolling(int(m * bpd), min_periods=int(m * bpd)).mean()
            up = (close > sma).to_numpy()
            dn = (close < sma).to_numpy()
            if filtre == "ile":
                L = L & up
                S = S & dn
            elif filtre == "karsi":
                L = L & dn
                S = S & up
        if yon == "uzun":
            S = np.zeros_like(S)
        elif yon == "kisa":
            L = np.zeros_like(L)
        d = pd.Series(np.where(L, 1.0, np.where(S, -1.0, np.nan)), index=idx)
        lim = int(round(tut * bpd))
        d = d.ffill(limit=lim) if lim > 0 else d
        d = d.fillna(0.0)
        d[idx < f.index.min()] = 0.0
        out[("futures", c)] = d.astype(float)
    return out


def _bars_per_day(index: pd.DatetimeIndex) -> float:
    if len(index) < 2:
        return 1.0
    step = pd.Series(index[1:] - index[:-1]).median()
    return pd.Timedelta(days=1) / step


# ---------------------------------------------------------------- 3) kaplama


def kaplama_signal(data: dict, funding: dict, universe: str = "BTCUSDT", n: float = 3, ust: float = 0.0003,
                   ust_cikis: float = 0.0001, uzun_poz: float = 0.0, filtre: str = "yok", m: int = 100, **_) -> dict:
    """Spot hep uzun; vadeli bacak fonlama yüksekken −1 (nötr carry), değilken `uzun_poz`.

    `filtre="trend"`: kapanış `m` günlük SMA'nın altındaysa da vadeli −1 (nötr), yani
    düşüş trendinde nakit yerine carry tutulur.
    """
    out = {}
    for c in coins_for(universe):
        spot = data[("spot", c)]
        fut = data[("futures", c)]
        f = funding.get(c, pd.DataFrame())
        idx = _union_index([spot, fut])
        if f.empty:
            out[("spot", c)] = pd.Series(0.0, index=spot.index)
            out[("futures", c)] = pd.Series(0.0, index=fut.index)
            continue
        allowed = np.asarray(idx >= f.index.min())
        F = _asof(_fund_avg(f, n), idx).to_numpy()
        with np.errstate(invalid="ignore"):
            hedge = _hysteresis(F > ust, (F < ust_cikis) | np.isnan(F)) > 0
        if filtre == "trend":
            close = _close_on(spot, idx)
            bpd = _bars_per_day(spot.index)
            sma = close.rolling(int(m * bpd), min_periods=int(m * bpd)).mean()
            hedge = hedge | ~(close > sma).to_numpy()
        fpos = np.where(hedge, -1.0, uzun_poz)
        spos = np.ones(len(idx))
        spos = np.where(allowed, spos, 0.0)
        fpos = np.where(allowed, fpos, 0.0)
        out[("spot", c)] = pd.Series(spos, index=idx).reindex(spot.index).astype(float)
        out[("futures", c)] = pd.Series(fpos, index=idx).reindex(fut.index).astype(float)
    return out


# ---------------------------------------------------------------- spec üretimi


SIGNALS = {"carry": carry_signal, "yonlu": yonlu_signal, "kaplama": kaplama_signal}


def _signal(data: dict, funding: dict, kind: str = "carry", **params) -> dict:
    return SIGNALS[kind](data, funding, **params)


def make_spec(name: str, kind: str, universe: str, interval: str, params: dict, description: str = "") -> StrategySpec:
    legs = legs_for(kind, universe)
    p = {"kind": kind, "universe": universe, **params}
    return StrategySpec(name, FAMILY, interval, legs, _signal, p, None, description)


# ---------------------------------------------------------------- dondurulmuş yapılandırmalar


FROZEN = (
    (
        "fonlama_carry_sepet3_hizli",
        "carry",
        "SEPET3",
        "4h",
        {"n": 1, "giris": 1.5e-4, "cikis": 0.5e-4, "son_neg": False},
        "Üç coinlik nakit-carry sepeti (her coinde spot uzun + vadeli kısa, her bacak 1/6). "
        "Son 1 günün ortalama fonlaması 8 saatte %0,015'i geçince girilir, %0,005'in altına inince çıkılır.",
    ),
    (
        "fonlama_carry_sepet3_yavas_dusuk",
        "carry",
        "SEPET3",
        "4h",
        {"n": 7, "giris": 0.5e-4, "cikis": -0.5e-4, "son_neg": False},
        "Üç coinlik nakit-carry sepeti. Son 7 günün ortalama fonlaması 8 saatte %0,005'i geçince girilir, "
        "−%0,005'in altına inince çıkılır (taban fonlamada da pozisyonda kalır).",
    ),
    (
        "fonlama_carry_btc_surekli",
        "carry",
        "BTCUSDT",
        "4h",
        {"n": 0, "giris": 0.0, "cikis": 0.0, "son_neg": False},
        "BTC nakit-carry, ilk fonlama kaydından sonra sürekli pozisyonda (spot uzun 0,5 + vadeli kısa 0,5). "
        "Referans: dev_valid'de yeni işlem açmadığından işlem sayısı şartını yapısal olarak geçemez.",
    ),
    (
        "fonlama_negatif_uzun_sepet3",
        "yonlu",
        "SEPET3",
        "4h",
        {"n": 1, "olcek": "mutlak", "yon": "uzun", "alt": -0.5e-4, "ust": 1.0, "filtre": "yok", "m": 100, "tut": 2},
        "Üç coinlik vadeli sepet (her coin 1/3). Son 1 günün ortalama fonlaması 8 saatte −%0,005'in altına "
        "inince (kalabalık kısa) o coinde vadeli uzun; sinyal 2 gün geçerli.",
    ),
)

CANDIDATE_RESULT = {
    "fonlama_carry_sepet3_hizli": "candidate_check: GEÇMEDİ (dev_valid'de 12 işlem < 20; getiri, 2× maliyet ve Sharpe şartları geçti).",
    "fonlama_carry_sepet3_yavas_dusuk": "candidate_check: GEÇMEDİ (dev_valid'de 2 işlem < 20; getiri, 2× maliyet ve Sharpe şartları geçti).",
    "fonlama_carry_btc_surekli": "candidate_check: GEÇMEDİ (dev_valid'de 0 işlem < 20; getiri, 2× maliyet ve Sharpe şartları geçti).",
    "fonlama_negatif_uzun_sepet3": "candidate_check: GEÇMEDİ (dev_valid net −%13,17, 2× −%14,18, Sharpe −0,68).",
}


def specs() -> list[StrategySpec]:
    """Dondurulan ve dev_valid'de bir kez değerlendirilen yapılandırmalar."""
    return [
        make_spec(name, kind, universe, interval, dict(params), f"{desc} {CANDIDATE_RESULT[name]}")
        for name, kind, universe, interval, params, desc in FROZEN
    ]
