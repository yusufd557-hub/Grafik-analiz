"""Ortalamaya dönüş ailesi: kısa vadeli aşırı sapmalardan geri dönüş (5m–4h).

Bütün sinyaller nedenseldir: t barındaki hedef pozisyon yalnızca t ve önceki
barların kapanmış verisiyle hesaplanır (geriye dönük pencereler, `shift(+k)`,
baştan ileri doğru yürüyen durum makinesi). Tam örneklem istatistiği,
ortalanmış pencere veya `shift(-k)` kullanılmaz.

Sapma ölçüsü (``kind``), negatif değer "aşırı satılmış" demektir:

- ``z``: (kapanış − SMA(n)) / std(n)  (Bollinger z-skoru).
- ``vwap``: (kapanış − kayan VWAP(n)) / ATR(n).
- ``rsi``: (RSI(n) − 50) / 10  (giriş 3 → RSI 20 / 80).
- ``ret``: n barlık log getiri / (n bar önceki ``vol_n`` barlık bar getirisi
  std'si × √n). Olağandışı büyük hareketten sonra ters yönde işlem.

Durum makinesi (bacak başına):

- Pozisyon yokken skor ≤ −giriş ise alım, skor ≥ +giriş ise açığa satış
  (``side`` ve rejim filtrelerinin izin verdiği yönlerde).
- Alımdan çıkış: skor ≥ −çıkış (ortalamaya dönüş), ``max_hold`` bar dolması
  ya da isteğe bağlı ATR stop (giriş kapanışı − ``stop_atr`` × ATR). Açığa
  satışta simetrik.

Rejim filtreleri (isteğe bağlı):

- ``trend_n``: aynı zaman dilimindeki SMA(trend_n). ``trend_mode="with"``
  ise alım yalnız kapanış SMA üstündeyken, açığa satış yalnız altındayken
  açılır (üst zaman dilimi trendi yönünde geri çekilme alımı/satımı).
- ``trend2_n``: ikinci, daha uzun SMA filtresi (alım yalnız kapanış her iki
  SMA'nın da üstündeyken).
- ``adx_max``: giriş yalnız ADX(14) < adx_max iken (yatay piyasa).
- ``confirm``: giriş barı dönüş yönünde kapanmalı (alımda kapanış > açılış).

Topluluk (``components``): her bileşen ayrı bir durum makinesidir; bacak
pozisyonu bileşen pozisyonlarının ortalamasıdır (ortak parametreler, örneğin
trend filtresi, bütün bileşenlere uygulanır).

Araştırmanın sonucu: iki yönlü (alım + açığa satış) saf ortalamaya dönüş
maliyet öncesi bile zarar etti; yalnızca yükselen trendde (kapanış uzun SMA
üstünde) dip alımı dev_train'de pozitif brüt kenar gösterdi.

`specs()` yalnızca dondurulup dev_valid'de bir kez değerlendirilen
yapılandırmaları döndürür (bkz. `arastirma/ortalamaya_donus/RAPOR.md`).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from grafik_analiz.indicators import adx, atr, rolling_vwap, rsi
from grafik_analiz.research.evaluate import StrategySpec

FAMILY = "ortalamaya_donus"

COINS = ("BTCUSDT", "ETHUSDT", "SOLUSDT")


def legs_for(market: str, universe: str) -> tuple:
    """`universe`: tek coin sembolü ya da üç coinlik eşit ağırlıklı portföy için 'PORT3'."""
    if universe == "PORT3":
        return tuple((market, c) for c in COINS)
    return ((market, universe),)


# ---------------------------------------------------------------- sapma ölçüleri


def score(df: pd.DataFrame, kind: str, n: int, vol_n: int = 500) -> pd.Series:
    close = df["close"].astype(float)
    if kind == "z":
        mid = close.rolling(n, min_periods=n).mean()
        sd = close.rolling(n, min_periods=n).std(ddof=0)
        return (close - mid) / sd.replace(0.0, np.nan)
    if kind == "vwap":
        vw = rolling_vwap(df, n)
        a = atr(df, n)
        return (close - vw) / a.replace(0.0, np.nan)
    if kind == "rsi":
        return (rsi(close, n) - 50.0) / 10.0
    if kind == "ret":
        lr = np.log(close).diff()
        move = np.log(close / close.shift(n))
        # Hareketten önceki oynaklık: son n bar hariç.
        sd = lr.rolling(vol_n, min_periods=vol_n).std().shift(n)
        return move / (sd * np.sqrt(n)).replace(0.0, np.nan)
    raise ValueError(f"bilinmeyen sapma ölçüsü: {kind}")


# ---------------------------------------------------------------- durum makinesi


def _state_machine(
    s: np.ndarray,
    close: np.ndarray,
    atr_v: np.ndarray | None,
    long_ok: np.ndarray,
    short_ok: np.ndarray,
    entry: float,
    exit_: float | None,
    max_hold: int,
    stop_atr: float | None,
) -> np.ndarray:
    out = np.zeros(len(s))
    pos = 0
    held = 0
    stop_level = np.nan
    for i in range(len(s)):
        si = s[i]
        if pos != 0:
            held += 1
            leave = held >= max_hold
            if not leave and exit_ is not None and np.isfinite(si):
                leave = si >= -exit_ if pos == 1 else si <= exit_
            if not leave and stop_atr is not None and np.isfinite(stop_level):
                leave = close[i] <= stop_level if pos == 1 else close[i] >= stop_level
            if leave:
                pos = 0
                out[i] = 0.0
                continue
        elif np.isfinite(si):
            if si <= -entry and long_ok[i]:
                pos, held = 1, 0
            elif si >= entry and short_ok[i]:
                pos, held = -1, 0
            if pos != 0 and stop_atr is not None:
                a = atr_v[i] if atr_v is not None else np.nan
                stop_level = close[i] - pos * stop_atr * a if np.isfinite(a) else np.nan
        out[i] = pos
    return out


def leg_signal(
    df: pd.DataFrame,
    market: str,
    kind: str = "z",
    n: int = 20,
    entry: float = 2.0,
    exit: float | None = 0.0,
    max_hold: int = 24,
    side: str = "both",
    trend_n: int = 0,
    trend_mode: str = "none",
    adx_max: float | None = None,
    stop_atr: float | None = None,
    confirm: bool = False,
    vol_n: int = 500,
    trend2_n: int = 0,
) -> pd.Series:
    close = df["close"].astype(float)
    s = score(df, kind, n, vol_n).to_numpy(dtype=float)
    long_ok = np.ones(len(df), dtype=bool)
    short_ok = np.ones(len(df), dtype=bool)
    if side == "long" or market == "spot":
        short_ok[:] = False
    if side == "short":
        long_ok[:] = False
    if trend_n and trend_mode != "none":
        ma = close.rolling(trend_n, min_periods=trend_n).mean()
        up = (close > ma).to_numpy()
        dn = (close < ma).to_numpy()
        known = ma.notna().to_numpy()
        if trend_mode == "with":
            long_ok &= up & known
            short_ok &= dn & known
        elif trend_mode == "against":
            long_ok &= dn & known
            short_ok &= up & known
        else:
            raise ValueError(f"bilinmeyen trend modu: {trend_mode}")
    if trend2_n:
        # İkinci (uzun vadeli) trend filtresi: alım yalnız kapanış SMA(trend2_n) üstündeyken.
        ma2 = close.rolling(trend2_n, min_periods=trend2_n).mean()
        long_ok &= (close > ma2).to_numpy() & ma2.notna().to_numpy()
        short_ok &= (close < ma2).to_numpy() & ma2.notna().to_numpy()
    if adx_max is not None:
        ax = adx(df, 14)["adx"].to_numpy()
        flat = np.nan_to_num(ax, nan=np.inf) < adx_max
        long_ok &= flat
        short_ok &= flat
    if confirm:
        o = df["open"].to_numpy(dtype=float)
        c = close.to_numpy()
        long_ok &= c > o
        short_ok &= c < o
    atr_v = atr(df, 14).to_numpy() if stop_atr is not None else None
    pos = _state_machine(s, close.to_numpy(), atr_v, long_ok, short_ok, float(entry), exit, int(max_hold), stop_atr)
    return pd.Series(pos, index=df.index)


def leg_signal_ens(df: pd.DataFrame, market: str, components: list, **common) -> pd.Series:
    """Topluluk: bileşen pozisyonlarının ortalaması (her bileşen 0/±1, sonuç −1…1)."""
    parts = [leg_signal(df, market, **{**common, **comp}) for comp in components]
    return sum(parts) / len(parts)


def sinyal(data: dict, funding: dict, **params) -> dict:
    if "components" in params:
        return {leg: leg_signal_ens(df, leg[0], **params) for leg, df in data.items()}
    return {leg: leg_signal(df, leg[0], **params) for leg, df in data.items()}


def make_spec(name: str, market: str, universe: str, interval: str, description: str = "", **params) -> StrategySpec:
    return StrategySpec(
        name=name,
        family=FAMILY,
        interval=interval,
        legs=legs_for(market, universe),
        signal_fn=sinyal,
        params=params,
        description=description,
    )


# ---------------------------------------------------------------- dondurulan yapılandırmalar

# Topluluk bileşenleri (1h barlarla). Hepsi yalnız alım, yükselen trendde dip alımı.
COMP_1H = [
    {"kind": "ret", "n": 4, "entry": 3.0, "exit": None, "max_hold": 12},
    {"kind": "ret", "n": 1, "entry": 4.0, "exit": None, "max_hold": 12},
    {"kind": "vwap", "n": 72, "entry": 3.0, "exit": 0.0, "max_hold": 48},
    {"kind": "rsi", "n": 6, "entry": 3.5, "exit": 0.0, "max_hold": 48},
]
# Aynı bileşenlerin 15m karşılıkları (bar sayıları ×4; RSI(6) ölçeklenmedi).
COMP_15M = [
    {"kind": "ret", "n": 16, "entry": 3.0, "exit": None, "max_hold": 48},
    {"kind": "ret", "n": 4, "entry": 4.0, "exit": None, "max_hold": 48},
    {"kind": "vwap", "n": 288, "entry": 3.0, "exit": 0.0, "max_hold": 192},
    {"kind": "rsi", "n": 6, "entry": 3.5, "exit": 0.0, "max_hold": 96},
]

DESCRIPTIONS = {
    "od_dip_ens4_fut_port3_1h": (
        "Vadeli BTC/ETH/SOL (eşit ağırlık), 1h. Yalnız alım: kapanış 50 ve 200 günlük SMA üstündeyken "
        "dört dip ölçüsünden (4 saatlik −3σ düşüş, 1 saatlik −4σ düşüş, VWAP(72)'nin 3 ATR altı, RSI(6)<15) "
        "her biri pozisyonun 1/4'ünü açar. candidate_check: GEÇTİ (dev_valid 1× +%7,47, 2× +%4,08, Sharpe 0,86, 140 işlem)."
    ),
    "od_dip_ens4_fut_port3_15m": (
        "Vadeli BTC/ETH/SOL (eşit ağırlık), 15m. 1h topluluğunun 15 dakikalık karşılığı (bar sayıları ×4), "
        "50 ve 200 günlük SMA filtresi, yalnız alım. candidate_check: GEÇMEDİ (dev_valid 2× maliyette −%1,17)."
    ),
    "od_dip_ret4h_fut_port3_1h": (
        "Vadeli BTC/ETH/SOL (eşit ağırlık), 1h. Tek kural: 4 saatlik getiri önceki oynaklığa göre −3σ'dan "
        "düşükse ve kapanış 50 günlük SMA üstündeyse al, 12 saat tut. candidate_check: GEÇTİ (dev_valid 1× +%13,87, 2× +%10,42, Sharpe 1,09, 66 işlem)."
    ),
    "od_dip_ens4_spot_port3_1h": (
        "Spot BTC/ETH/SOL (eşit ağırlık), 1h. Vadeli 1h topluluğunun aynısı (50 ve 200 günlük SMA filtresi, "
        "yalnız alım), spot maliyetiyle. candidate_check: GEÇMEDİ (dev_valid 2× maliyette −%0,14)."
    ),
}

_COMMON_1H = {"side": "long", "trend_n": 1200, "trend_mode": "with"}
_COMMON_15M = {"side": "long", "trend_n": 4800, "trend_mode": "with", "vol_n": 2000}


def specs() -> list[StrategySpec]:
    """Dondurulan ve dev_valid'de bir kez değerlendirilen yapılandırmalar (parametreler dev_train'de seçildi)."""
    return [
        make_spec(
            "od_dip_ens4_fut_port3_1h",
            "futures",
            "PORT3",
            "1h",
            description=DESCRIPTIONS["od_dip_ens4_fut_port3_1h"],
            components=COMP_1H,
            trend2_n=4800,
            **_COMMON_1H,
        ),
        make_spec(
            "od_dip_ens4_fut_port3_15m",
            "futures",
            "PORT3",
            "15m",
            description=DESCRIPTIONS["od_dip_ens4_fut_port3_15m"],
            components=COMP_15M,
            trend2_n=19200,
            **_COMMON_15M,
        ),
        make_spec(
            "od_dip_ret4h_fut_port3_1h",
            "futures",
            "PORT3",
            "1h",
            description=DESCRIPTIONS["od_dip_ret4h_fut_port3_1h"],
            kind="ret",
            n=4,
            entry=3.0,
            exit=None,
            max_hold=12,
            **_COMMON_1H,
        ),
        make_spec(
            "od_dip_ens4_spot_port3_1h",
            "spot",
            "PORT3",
            "1h",
            description=DESCRIPTIONS["od_dip_ens4_spot_port3_1h"],
            components=COMP_1H,
            trend2_n=4800,
            **_COMMON_1H,
        ),
    ]
