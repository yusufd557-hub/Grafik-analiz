"""Trend takibi ailesi: zaman serisi momentumu, ortalama filtreleri, Donchian kırılımı.

Bütün sinyaller nedenseldir: t barındaki hedef pozisyon yalnızca t ve önceki
barların kapanmış verisiyle hesaplanır (geriye dönük pencereler, `shift(+k)`,
baştan ileri doğru yürüyen durum makineleri). Tam örneklem istatistiği,
ortalanmış pencere veya `shift(-k)` kullanılmaz.

Sinyal bileşenleri (her biri −1…1, spot / yalnız alımda 0…1):

- ``tsmom``: N günlük getirinin işareti.
- ``sma``: kapanışın N günlük basit ortalamaya göre konumu (işaret).
- ``emax``: EMA(N/4) ile EMA(N) farkının işareti.
- ``donch``: Donchian kırılımı. Kapanış önceki N günün en yükseğini geçince
  alım, önceki N/2 günün en düşüğünün altına inince çıkış (alım-satımda
  simetrik açığa satış). İsteğe bağlı ATR iz süren stop.

Topluluk: verilen bütün (fikir, bakış süresi) bileşenlerinin ortalaması.
İsteğe bağlı oynaklık hedefleme: boyut × min(1, hedef / gerçekleşen oynaklık).
Yeniden dengeleme bandı küçük boyut değişikliklerinde işlem yapmayı önler.

`specs()` yalnızca dondurulup dev_valid'de bir kez değerlendirilen
yapılandırmaları döndürür (bkz. `arastirma/trend/RAPOR.md`).
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd

from grafik_analiz.indicators import atr, ema
from grafik_analiz.research.evaluate import StrategySpec

FAMILY = "trend"

BARS_PER_DAY = {"1h": 24, "4h": 6, "1d": 1}

COINS = ("BTCUSDT", "ETHUSDT", "SOLUSDT")


def legs_for(market: str, universe: str) -> tuple:
    """`universe`: tek coin sembolü ya da üç coinlik eşit ağırlıklı portföy için 'PORT3'."""
    if universe == "PORT3":
        return tuple((market, c) for c in COINS)
    return ((market, universe),)


# ---------------------------------------------------------------- bileşenler


def _sign(x: pd.Series) -> pd.Series:
    return np.sign(x).where(x.notna())


def _donchian_state(
    df: pd.DataFrame,
    n_entry: int,
    n_exit: int,
    allow_short: bool,
    atr_mult: float | None = None,
    atr_n: int = 20,
) -> pd.Series:
    """Baştan ileri yürüyen kırılım durum makinesi (1 alım, −1 satım, 0 nakit)."""
    high = df["high"]
    low = df["low"]
    close = df["close"].to_numpy(dtype=float)
    up = high.shift(1).rolling(n_entry, min_periods=n_entry).max().to_numpy()
    dn = low.shift(1).rolling(n_entry, min_periods=n_entry).min().to_numpy()
    xup = high.shift(1).rolling(n_exit, min_periods=n_exit).max().to_numpy()
    xdn = low.shift(1).rolling(n_exit, min_periods=n_exit).min().to_numpy()
    a = atr(df, atr_n).to_numpy() if atr_mult else None

    out = np.full(len(close), np.nan)
    state = 0
    extreme = np.nan
    for i in range(len(close)):
        c = close[i]
        if np.isnan(up[i]) or np.isnan(dn[i]) or np.isnan(xup[i]) or np.isnan(xdn[i]):
            continue
        if state == 1:
            extreme = max(extreme, c)
            stop = a is not None and not np.isnan(a[i]) and c < extreme - atr_mult * a[i]
            if c < xdn[i] or stop:
                state = 0
        elif state == -1:
            extreme = min(extreme, c)
            stop = a is not None and not np.isnan(a[i]) and c > extreme + atr_mult * a[i]
            if c > xup[i] or stop:
                state = 0
        if state == 0:
            if c > up[i]:
                state, extreme = 1, c
            elif allow_short and c < dn[i]:
                state, extreme = -1, c
        out[i] = state
    return pd.Series(out, index=df.index)


def component(
    df: pd.DataFrame,
    kind: str,
    days: float,
    bpd: int,
    allow_short: bool,
    atr_mult: float | None = None,
) -> pd.Series:
    close = df["close"]
    n = max(2, int(round(days * bpd)))
    if kind == "tsmom":
        s = _sign(close / close.shift(n) - 1.0)
    elif kind == "sma":
        s = _sign(close - close.rolling(n, min_periods=n).mean())
    elif kind == "emax":
        s = _sign(ema(close, max(2, n // 4)) - ema(close, n))
    elif kind == "donch":
        s = _donchian_state(df, n, max(2, n // 2), allow_short, atr_mult, atr_n=max(2, int(round(20 * bpd))))
    else:
        raise ValueError(f"bilinmeyen bileşen: {kind}")
    if not allow_short:
        s = s.clip(lower=0.0)
    return s


def _apply_band(target: np.ndarray, band: float) -> np.ndarray:
    """Hedef ile mevcut pozisyon farkı banttan küçükse pozisyonu değiştirmez.

    Sıfıra iniş ve yön değişimi her zaman uygulanır. Baştan ileri yürür (nedensel).
    """
    out = np.zeros(len(target))
    cur = 0.0
    for i, t in enumerate(target):
        if not np.isfinite(t):
            t = 0.0
        if t == 0.0 or np.sign(t) != np.sign(cur) or abs(t - cur) >= band:
            cur = t
        out[i] = cur
    return out


def leg_target(
    df: pd.DataFrame,
    kinds: tuple,
    lookbacks: tuple,
    bpd: int,
    allow_short: bool,
    target_vol: float | None = None,
    vol_days: int = 30,
    band: float = 0.0,
    atr_mult: float | None = None,
) -> pd.Series:
    parts = [component(df, k, d, bpd, allow_short, atr_mult) for k in kinds for d in lookbacks]
    # Bütün bileşenler hazır olana kadar NaN (ısınma) → pozisyon 0.
    sig = pd.concat(parts, axis=1).mean(axis=1, skipna=False)
    if target_vol:
        n = max(2, int(round(vol_days * bpd)))
        lr = np.log(df["close"]).diff()
        rv = lr.rolling(n, min_periods=n).std() * math.sqrt(365.0 * bpd)
        sig = sig * (target_vol / rv).clip(upper=1.0)
    pos = sig.to_numpy(dtype=float)
    if band > 0:
        pos = _apply_band(pos, band)
    else:
        pos = np.where(np.isfinite(pos), pos, 0.0)
    return pd.Series(pos, index=df.index)


def trend_signal(
    data: dict,
    funding: dict,
    kinds=("tsmom",),
    lookbacks=(20,),
    bpd: int = 1,
    mode: str = "long",
    target_vol: float | None = None,
    vol_days: int = 30,
    band: float = 0.0,
    atr_mult: float | None = None,
) -> dict:
    """`mode`: 'long' (yalnız alım / nakit) ya da 'longshort' (yalnız vadelide −1…1)."""
    out = {}
    for leg, df in data.items():
        allow_short = mode == "longshort" and leg[0] == "futures"
        out[leg] = leg_target(
            df,
            tuple(kinds),
            tuple(lookbacks),
            int(bpd),
            allow_short,
            target_vol=target_vol,
            vol_days=int(vol_days),
            band=float(band),
            atr_mult=atr_mult,
        )
    return out


def make_spec(
    name: str,
    market: str,
    universe: str,
    interval: str,
    kinds=("tsmom",),
    lookbacks=(20,),
    mode: str = "long",
    target_vol: float | None = None,
    vol_days: int = 30,
    band: float = 0.0,
    atr_mult: float | None = None,
    description: str = "",
) -> StrategySpec:
    params = {
        "kinds": tuple(kinds),
        "lookbacks": tuple(lookbacks),
        "bpd": BARS_PER_DAY[interval],
        "mode": mode,
        "target_vol": target_vol,
        "vol_days": vol_days,
        "band": band,
        "atr_mult": atr_mult,
    }
    return StrategySpec(name, FAMILY, interval, legs_for(market, universe), trend_signal, params, description=description)


# ---------------------------------------------------------------- dondurulmuş yapılandırmalar


ENS_KINDS = ("tsmom", "sma", "emax", "donch")
ENS_LOOKBACKS = (20, 40, 80)


def specs() -> list[StrategySpec]:
    """Dondurulan ve dev_valid'de bir kez değerlendirilen yapılandırmalar.

    Hepsi 4 fikir × (20, 40, 80) gün = 12 bileşenli topluluk sinyali kullanır.
    """
    common = {"kinds": ENS_KINDS, "lookbacks": ENS_LOOKBACKS}
    return [
        make_spec(
            "trend_ens_spot_port3_1d",
            "spot",
            "PORT3",
            "1d",
            mode="long",
            description=DESCRIPTIONS["trend_ens_spot_port3_1d"],
            **common,
        ),
        make_spec(
            "trend_ens_spot_port3_4h",
            "spot",
            "PORT3",
            "4h",
            mode="long",
            band=0.15,
            description=DESCRIPTIONS["trend_ens_spot_port3_4h"],
            **common,
        ),
        make_spec(
            "trend_ens_spot_port3_4h_vt",
            "spot",
            "PORT3",
            "4h",
            mode="long",
            target_vol=0.6,
            vol_days=30,
            band=0.1,
            description=DESCRIPTIONS["trend_ens_spot_port3_4h_vt"],
            **common,
        ),
        make_spec(
            "trend_ens_vadeli_port3_4h_alim",
            "futures",
            "PORT3",
            "4h",
            mode="long",
            description=DESCRIPTIONS["trend_ens_vadeli_port3_4h_alim"],
            **common,
        ),
        make_spec(
            "trend_ens_vadeli_port3_4h_ls_vt",
            "futures",
            "PORT3",
            "4h",
            mode="longshort",
            target_vol=0.6,
            vol_days=30,
            band=0.1,
            description=DESCRIPTIONS["trend_ens_vadeli_port3_4h_ls_vt"],
            **common,
        ),
    ]


DESCRIPTIONS = {
    "trend_ens_spot_port3_1d": (
        "Spot BTC/ETH/SOL eşit ağırlık, günlük. 12 bileşenli trend topluluğu "
        "(N günlük getiri işareti, N günlük ortalama üstü, EMA(N/4)>EMA(N), Donchian N/N/2; N=20,40,80) "
        "ortalaması kadar alım, gerisi nakit. candidate_check: GEÇTİ (dev_valid +%32,5, Sharpe 0,69; al-tut +%73,7)."
    ),
    "trend_ens_spot_port3_4h": (
        "Spot BTC/ETH/SOL eşit ağırlık, 4 saatlik. Aynı 12 bileşenli trend topluluğu (gün cinsinden "
        "bakış süreleri ×6 bar), yalnız alım; 0,15'ten küçük pozisyon değişiklikleri yapılmaz. "
        "candidate_check: GEÇTİ (dev_valid +%38,6, Sharpe 0,77; al-tut +%74,3)."
    ),
    "trend_ens_spot_port3_4h_vt": (
        "Spot BTC/ETH/SOL eşit ağırlık, 4 saatlik. 12 bileşenli trend topluluğu × min(1, 0,6 / 30 günlük "
        "gerçekleşen yıllık oynaklık); yalnız alım, 0,1 yeniden dengeleme bandı. "
        "candidate_check: GEÇTİ (dev_valid +%42,7, Sharpe 0,91; al-tut +%74,3)."
    ),
    "trend_ens_vadeli_port3_4h_alim": (
        "USDⓈ-M vadeli BTC/ETH/SOL eşit ağırlık, 4 saatlik. 12 bileşenli trend topluluğu, yalnız alım "
        "(fonlama ödenir), kaldıraçsız. candidate_check: GEÇTİ (dev_valid +%26,5, Sharpe 0,60; "
        "vadeli al-tut +%50,8)."
    ),
    "trend_ens_vadeli_port3_4h_ls_vt": (
        "USDⓈ-M vadeli BTC/ETH/SOL eşit ağırlık, 4 saatlik. 12 bileşenli trend topluluğu −1…1 (alım ve "
        "açığa satış) × min(1, 0,6 / 30 günlük gerçekleşen oynaklık), 0,1 band, kaldıraçsız. "
        "candidate_check: GEÇMEDİ (dev_valid −%3,3, Sharpe 0,12)."
    ),
}
