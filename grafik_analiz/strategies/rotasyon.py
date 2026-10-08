"""Rotasyon ailesi: BTC, ETH ve SOL arasında kesitsel momentum / göreli güç.

Üç sinyal türü vardır:

- ``sinyal_rotasyon`` (spot): her yeniden dengelemede geriye dönük getirisi
  (veya oynaklığa bölünmüş getirisi) en güçlü ``top_k`` coini tutar. Filtre
  geçmezse o coinin payı nakitte kalır.
- ``sinyal_uzun_kisa`` (vadeli): en güçlü coinde uzun, en zayıf coinde kısa
  pozisyon (piyasa nötr). ``ls_trend`` modunda uzun yalnızca güçlü coin kendi
  trendinin üstündeyken, kısa yalnızca zayıf coin trendinin altındayken açılır.
- ``sinyal_oran`` (vadeli çift): ALT/BAZ oranı kendi hareketli ortalamasının
  üstündeyse ALT uzun + BAZ kısa, altındaysa tersi (``ls``) veya nakit
  (``yukari``).

Bütün sinyaller nedenseldir: t barındaki değer yalnızca t barının kapanışına
kadar bilinen kapanış fiyatlarından hesaplanır (geriye dönük pencereler).
Verisi henüz olmayan coin seçilemez (hedef 0). Vadeli bacaklarda, o coinin
ilk fonlama kaydından önce pozisyon açılmaz (fonlama verisi olmayan dönemi
maliyetsiz saymamak için).

Bacak ağırlıkları eşittir (toplam 1); bacak başına pozisyon 0…1 (spot) veya
−1…1 (vadeli). Bu yüzden tek coin tutan bir rotasyonun toplam pozisyonu
1/bacak sayısı kadardır (kaldıraç yok).
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd

from ..research.evaluate import StrategySpec

FAMILY = "rotasyon"
_EPOCH_MONDAY = pd.Timestamp("1970-01-05", tz="UTC")


# ---------------------------------------------------------------- yardımcılar


def _panel(data: dict, field: str = "close") -> pd.DataFrame:
    """Bacakların bir sütununu ortak (birleşim) indekste yan yana dizer."""
    index = None
    for frame in data.values():
        index = frame.index if index is None else index.union(frame.index)
    cols = {}
    for leg, frame in data.items():
        cols[leg] = frame[field].astype(float).reindex(index)
    return pd.DataFrame(cols, index=index)


def _rebalance_mask(index: pd.DatetimeIndex, every: int) -> np.ndarray:
    """Günlük barlarda her ``every`` günde bir yeniden dengeleme (takvime bağlı).

    every=7 için pazar barının kapanışında karar verilir, işlem pazartesi
    açılışında yapılır. Takvime bağlı olduğu için seri kısaltılınca değişmez.
    """
    if every <= 1:
        return np.ones(len(index), dtype=bool)
    days = np.asarray((index - _EPOCH_MONDAY) // pd.Timedelta(days=1), dtype=np.int64)
    return (days % every) == (every - 1)


def _score(close: pd.DataFrame, lookback: int, skor: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    """(skor, mutlak filtre için getiri). Skor: 'getiri' = L günlük log getiri,
    'risk' = L günlük log getiri / (günlük oynaklık × √L), 'karma' = L/2, L, 2L
    ufuklarının ölçekli ortalaması (mutlak filtre bu birleşik skoru kullanır)."""
    logc = np.log(close)
    mom = logc - logc.shift(lookback)
    if skor == "getiri":
        return mom, mom
    if skor == "risk":
        win = max(lookback, 20)
        vol = logc.diff().rolling(win, min_periods=win).std() * math.sqrt(lookback)
        return mom / vol.replace(0.0, np.nan), mom
    if skor == "karma":
        # L/2, L ve 2L günlük log getirilerin √ufuk ile ölçeklenmiş ortalaması.
        hs = (max(2, lookback // 2), lookback, 2 * lookback)
        sc = sum((logc - logc.shift(h)) / math.sqrt(h) for h in hs) / len(hs)
        return sc, sc
    raise ValueError(f"bilinmeyen skor: {skor}")


def _trend_ok(close: pd.DataFrame, ma: int) -> pd.DataFrame:
    sma = close.rolling(ma, min_periods=ma).mean()
    return close > sma


def _futures_allowed(data: dict, funding: dict) -> pd.DataFrame:
    """Vadeli bacakta, coinin ilk fonlama kaydı kapanıştan önce biliniyorsa True."""
    out = {}
    index = _panel(data).index
    for leg, frame in data.items():
        market, symbol = leg
        if market != "futures":
            out[leg] = pd.Series(True, index=index)
            continue
        f = funding.get(symbol)
        if f is None or f.empty:
            out[leg] = pd.Series(False, index=index)
            continue
        first = f.index.min()
        ok = (frame["close_time"] >= first).reindex(index).fillna(False).astype(bool)
        out[leg] = ok
    return pd.DataFrame(out, index=index)


def _to_legs(panel: pd.DataFrame, data: dict) -> dict:
    return {leg: panel[leg].reindex(frame.index).fillna(0.0).astype(float) for leg, frame in data.items()}


# ---------------------------------------------------------------- 1) spot rotasyon


def sinyal_rotasyon(
    data,
    funding,
    lookback: int = 28,
    skor: str = "getiri",
    top_k: int = 1,
    every: int = 7,
    filtre: str = "yok",
    tampon: float = 0.0,
    gunluk_filtre: bool = False,
):
    """En güçlü ``top_k`` coini tut.

    filtre: 'yok' | 'mutlak' (L günlük getiri > 0) | 'ma<N>' (kapanış > N günlük SMA).
    tampon: elde tutulan coinin skoruna eklenen bonus (gereksiz geçişleri azaltır).
    gunluk_filtre: True ise filtre her bar uygulanır (filtre bozulunca bir sonraki
    yeniden dengelemeyi beklemeden nakde geçilir, düzelince geri girilir).
    """
    close = _panel(data)
    score, mom = _score(close, lookback, skor)
    elig = score.notna()
    if filtre == "mutlak":
        filt = mom > 0
    elif filtre.startswith("ma"):
        filt = _trend_ok(close, int(filtre[2:]))
    elif filtre == "yok":
        filt = pd.DataFrame(True, index=close.index, columns=close.columns)
    else:
        raise ValueError(f"bilinmeyen filtre: {filtre}")
    elig = elig & filt
    rebal = _rebalance_mask(close.index, every)

    s = score.to_numpy(dtype=float)
    e = elig.to_numpy(dtype=bool)
    n, m = s.shape
    held = np.zeros((n, m), dtype=float)
    cur = np.zeros(m, dtype=bool)
    for i in range(n):
        if rebal[i]:
            adj = np.where(e[i], s[i] + tampon * cur, -np.inf)
            order = np.argsort(-adj, kind="stable")
            new = np.zeros(m, dtype=bool)
            for j in order[:top_k]:
                if e[i, j]:
                    new[j] = True
            cur = new
        held[i] = cur
    pos = pd.DataFrame(held, index=close.index, columns=close.columns)
    if gunluk_filtre:
        pos = pos * filt.fillna(False).astype(float)
    return _to_legs(pos, data)


# ---------------------------------------------------------------- 2) vadeli uzun/kısa


def sinyal_uzun_kisa(
    data,
    funding,
    lookback: int = 28,
    skor: str = "getiri",
    every: int = 7,
    mod: str = "ls",
    ma: int = 100,
    vol_esit: int = 0,
):
    """En güçlü coinde +1, en zayıf coinde −1 (en az iki uygun coin varsa).

    vol_esit > 0 ise iki tarafın oynaklığı eşitlenir: son ``vol_esit`` günün
    günlük oynaklığı yüksek olan tarafın pozisyonu düşük/yüksek oranına
    küçültülür (düşük oynaklıklı taraf 1).
    """
    close = _panel(data)
    score, _ = _score(close, lookback, skor)
    allowed = _futures_allowed(data, funding)
    elig = score.notna() & allowed
    up = _trend_ok(close, ma).to_numpy(dtype=bool)
    down = (close < close.rolling(ma, min_periods=ma).mean()).to_numpy(dtype=bool)
    rebal = _rebalance_mask(close.index, every)
    if vol_esit > 0:
        vol = np.log(close).diff().rolling(vol_esit, min_periods=vol_esit).std().to_numpy(dtype=float)
    else:
        vol = np.ones(close.shape)

    s = score.to_numpy(dtype=float)
    e = elig.to_numpy(dtype=bool)
    n, m = s.shape
    out = np.zeros((n, m))
    cur = np.zeros(m)
    for i in range(n):
        if rebal[i]:
            cur = np.zeros(m)
            idx = np.flatnonzero(e[i])
            if len(idx) >= 2:
                top = idx[np.argmax(s[i, idx])]
                bot = idx[np.argmin(s[i, idx])]
                vt, vb = vol[i, top], vol[i, bot]
                if vol_esit > 0 and np.isfinite(vt) and np.isfinite(vb) and vt > 0 and vb > 0:
                    st, sb = min(1.0, vb / vt), min(1.0, vt / vb)
                else:
                    st = sb = 1.0
                if mod == "ls":
                    cur[top], cur[bot] = st, -sb
                elif mod == "ls_trend":
                    if up[i, top]:
                        cur[top] = st
                    if down[i, bot]:
                        cur[bot] = -sb
                else:
                    raise ValueError(f"bilinmeyen mod: {mod}")
        # Uygunluğunu yitiren bacak (ör. veri yok) kapatılır.
        out[i] = np.where(e[i] | (cur == 0), cur, 0.0)
    pos = pd.DataFrame(out, index=close.index, columns=close.columns)
    return _to_legs(pos, data)


# ---------------------------------------------------------------- 3) oran trendi


def sinyal_oran(
    data,
    funding,
    alt: str = "ETHUSDT",
    baz: str = "BTCUSDT",
    n: int = 50,
    mod: str = "ls",
    every: int = 1,
):
    """ALT/BAZ oranı n günlük SMA'sının üstündeyse ALT +1 / BAZ −1.

    mod 'ls': altındaysa ALT −1 / BAZ +1. mod 'yukari': altındaysa nakit.
    """
    close = _panel(data)
    legs = list(data)
    la = next(l for l in legs if l[1] == alt)
    lb = next(l for l in legs if l[1] == baz)
    allowed = _futures_allowed(data, funding)
    ratio = np.log(close[la]) - np.log(close[lb])
    sma = ratio.rolling(n, min_periods=n).mean()
    valid = (ratio.notna() & sma.notna() & allowed[la] & allowed[lb]).to_numpy(dtype=bool)
    up = (ratio > sma).to_numpy(dtype=bool)
    rebal = _rebalance_mask(close.index, every)

    T = len(close)
    a = np.zeros(T)
    b = np.zeros(T)
    ca = cb = 0.0
    for i in range(T):
        if rebal[i]:
            if not valid[i]:
                ca = cb = 0.0
            elif up[i]:
                ca, cb = 1.0, -1.0
            elif mod == "ls":
                ca, cb = -1.0, 1.0
            elif mod == "yukari":
                ca = cb = 0.0
            else:
                raise ValueError(f"bilinmeyen mod: {mod}")
        if not valid[i]:
            ca = cb = 0.0
        a[i], b[i] = ca, cb
    pos = pd.DataFrame(0.0, index=close.index, columns=close.columns)
    pos[la] = a
    pos[lb] = b
    return _to_legs(pos, data)


SIGNALS = {
    "rotasyon": sinyal_rotasyon,
    "uzun_kisa": sinyal_uzun_kisa,
    "oran": sinyal_oran,
}

SPOT3 = (("spot", "BTCUSDT"), ("spot", "ETHUSDT"), ("spot", "SOLUSDT"))
SPOT2 = (("spot", "BTCUSDT"), ("spot", "ETHUSDT"))
FUT3 = (("futures", "BTCUSDT"), ("futures", "ETHUSDT"), ("futures", "SOLUSDT"))
FUT2 = (("futures", "BTCUSDT"), ("futures", "ETHUSDT"))


def make_spec(name: str, kind: str, legs, params: dict, interval: str = "1d", description: str = "") -> StrategySpec:
    return StrategySpec(
        name=name,
        family=FAMILY,
        interval=interval,
        legs=tuple(tuple(l) for l in legs),
        signal_fn=SIGNALS[kind],
        params=dict(params),
        description=description,
    )


# ---------------------------------------------------------------- dondurulmuş yapılandırmalar

# Parametreler yalnız dev_train (2023 sonuna kadar) sonuçlarıyla seçildi; her biri
# dev_valid'de bir kez değerlendirildi. Açıklamalar candidate_check sonucunu içerir.
_SB = (("futures", "SOLUSDT"), ("futures", "BTCUSDT"))

FROZEN: list[dict] = [
    dict(
        name="rotasyon_spot_top1_L14_gunluk",
        kind="rotasyon",
        legs=SPOT3,
        params=dict(lookback=14, skor="getiri", top_k=1, every=7, filtre="mutlak", gunluk_filtre=True),
        description=(
            "Spot BTC/ETH/SOL: her pazar kapanışında son 14 günün en güçlüsü tutulur (sermayenin 1/3'ü); "
            "o coinin 14 günlük getirisi negatife dönerse her gün nakde geçilir."
            " candidate_check GEÇMEDİ: dev_valid net +%9,63 (2× +%5,84) ama Sharpe 0,42 < 0,5."
        ),
    ),
    dict(
        name="rotasyon_spot_top2_L28_gunluk",
        kind="rotasyon",
        legs=SPOT3,
        params=dict(lookback=28, skor="getiri", top_k=2, every=7, filtre="mutlak", gunluk_filtre=True),
        description=(
            "Spot BTC/ETH/SOL: haftalık, son 28 günün en güçlü iki coini (her biri sermayenin 1/3'ü); "
            "28 günlük getirisi negatif olan coin her gün nakde çevrilir."
            " candidate_check GEÇMEDİ: dev_valid net −%4,09, Sharpe 0,04."
        ),
    ),
    dict(
        name="rotasyon_vadeli_uzunkisa_karma28",
        kind="uzun_kisa",
        legs=FUT3,
        params=dict(lookback=28, skor="karma", every=7, mod="ls", ma=100),
        description=(
            "Vadeli BTC/ETH/SOL piyasa nötr: haftalık, 14/28/56 günlük karma momentumu en yüksek coinde uzun, "
            "en düşük coinde kısa (her biri sermayenin 1/3'ü), fonlama dahil."
            " candidate_check GEÇMEDİ: dev_valid net −%39,22, Sharpe −1,70."
        ),
    ),
    dict(
        name="rotasyon_vadeli_uzunkisa_L21_volesit",
        kind="uzun_kisa",
        legs=FUT3,
        params=dict(lookback=21, skor="getiri", every=1, mod="ls", ma=100, vol_esit=30),
        description=(
            "Vadeli BTC/ETH/SOL piyasa nötr: günlük, 21 günlük getirisi en yüksek coinde uzun, en düşükte kısa; "
            "iki tarafın 30 günlük oynaklığı eşitlenir (oynak taraf küçültülür), fonlama dahil."
            " candidate_check GEÇMEDİ: dev_valid net −%6,92, Sharpe −0,25."
        ),
    ),
    dict(
        name="rotasyon_oran_SOLBTC_n50_yukari",
        kind="oran",
        legs=_SB,
        params=dict(alt="SOLUSDT", baz="BTCUSDT", n=50, mod="yukari", every=1),
        description=(
            "Vadeli SOL/BTC oran trendi: oran 50 günlük ortalamasının üstündeyse SOL uzun + BTC kısa "
            "(her biri sermayenin yarısı), altındaysa nakit; fonlama dahil."
            " candidate_check GEÇMEDİ: dev_valid net −%27,62, Sharpe −1,22."
        ),
    ),
]


def specs() -> list[StrategySpec]:
    return [make_spec(**cfg) for cfg in FROZEN]
