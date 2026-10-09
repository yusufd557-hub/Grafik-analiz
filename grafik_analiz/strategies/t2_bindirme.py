"""Tur 2 bindirme (overlay) ve portföy ailesi ("t2_bindirme").

Ortak çerçeve: her coin için bir **maruziyet sinyali** E(t) ∈ [0, 1] ve bu
maruziyeti kaldıraçsız uygulayan bir **yürütme biçimi**.

Maruziyet sinyalleri (``sinyal``; hepsi geriye dönük):

- ``trend``: tur 1 trend topluluğu (`grafik_analiz.strategies.trend.leg_target`,
  yalnız alım; fikirler ``kinds`` × bakış süreleri ``lookbacks`` gün), 0…1.
- ``vol``: min(1, ``hedef_vol`` / σ), σ son ``vol_gun`` günün kapanış log
  getirilerinin kayan std'si (yıllık). Coin başına uygulanınca ters oynaklık
  ağırlığıdır.
- ``trend_vol``: trend × vol.
- ``sabit``: sabit E = ``sabit`` (1 al-tut, 0 saf carry; taban çizgileri).

E'deki ``bant``'tan küçük değişiklikler uygulanmaz (0'a iniş her zaman
uygulanır); baştan ileri yürür.

Yürütme biçimleri (``bicim``):

- ``nakit``: yalnız spot bacaklar (her coin 1/3). Spot = E.
- ``tam``: her coinde spot ve vadeli bacak (her biri 1/6). Carry açıkken spot
  = 1, vadeli = 2E − 1 (E=0 saf nakit-carry, E=1 tam uzun). Carry kapalıyken
  spot = min(1, 2E), vadeli = max(0, 2E − 1).
- ``yarim``: aynı bacaklar; vadeli hiç uzun olmaz. Carry açıkken spot = 1,
  vadeli = −(1 − E). Kapalıyken spot = E, vadeli = 0.

Carry açık/kapalı: ``fon_n = 0`` ise fonlama verisi başladıktan sonra hep
açık; değilse son ``fon_n`` günün ortalama fonlaması (8 saatlik eşdeğer)
``fon_giris``'i geçince açılır, ``fon_cikis``'in altına inince kapanır.
Fonlama kaydı yalnız zaman damgası ≤ bar açılışı ise kullanılır. Carry'li
biçimlerde coinin ilk fonlama kaydından önce iki bacakta da pozisyon yoktur.

**Portföy** (``portfoy_signal``): tur 1'in dondurulmuş, bütün bacakları vadeli
yapılandırmalarından önceden yazılmış bir kuralla (bkz.
`arastirma/tur2/t2_bindirme/NOTLAR.md`) seçilen bileşenlerin eşit riskli
toplamı. Spec 1 saatlik, vadeli BTC/ETH/SOL (bacak başına 1/3). Her bileşen
kendi zaman diliminde, kendi `signal_fn`'iyle hesaplanır; verisi
`grafik_analiz.research.data.load(..., scope="dev")` ile yüklenir ve **verilen
1s verinin son barının kapanışına kadar** açıkça kesilir. 1s barın kararı,
kapanışı o 1s barın kapanışından sonra olmayan son bileşen barından gelir.
Coin c'deki vadeli bacak pozisyonu = kırp(3 · Σ_k b_k · w_kc · p_kc, −1, 1);
b_k eğitimde sabitlenen çarpandır (kaldıraç yok: bacak pozisyonu ±1'de
kırpılır).

`specs()` yalnızca dondurulup dev_valid'de bir kez değerlendirilen
yapılandırmaları döndürür (bkz. `arastirma/tur2/t2_bindirme/RAPOR.md`).
"""

from __future__ import annotations

import importlib
import math
from functools import lru_cache

import numpy as np
import pandas as pd

from grafik_analiz.research.evaluate import StrategySpec

FAMILY = "t2_bindirme"

COINS = ("BTCUSDT", "ETHUSDT", "SOLUSDT")

BARS_PER_DAY = {"1h": 24, "4h": 6, "1d": 1}

ENS_KINDS = ("tsmom", "sma", "emax", "donch")

ROUND1_MODULES = (
    "trend",
    "rotasyon",
    "ortalamaya_donus",
    "kirilim",
    "fonlama_carry",
    "mevsimsellik",
    "makine_ogrenmesi",
    "formasyon",
)


# ---------------------------------------------------------------- yardımcılar


def _ns(index: pd.DatetimeIndex) -> np.ndarray:
    return index.as_unit("ns").asi8


def _asof(series: pd.Series, index: pd.DatetimeIndex) -> np.ndarray:
    """Her bar açılışında, zaman damgası ≤ bar açılışı olan en son kayıt değeri."""
    if series.empty:
        return np.full(len(index), np.nan)
    pos = np.searchsorted(_ns(series.index), _ns(index), side="right") - 1
    vals = series.to_numpy(dtype=float)
    return np.where(pos >= 0, vals[np.clip(pos, 0, None)], np.nan)


def _fund_avg(f: pd.DataFrame, n_days: float) -> pd.Series:
    """Kayıt serisinde (t − n gün, t] fonlama toplamının 8 saatlik eşdeğer ortalaması; ilk n gün NaN."""
    r = f["funding_rate"].astype(float)
    s = r.rolling(pd.Timedelta(days=n_days)).sum() / (3.0 * n_days)
    return s.where(r.index >= r.index.min() + pd.Timedelta(days=n_days))


def _hysteresis(enter: np.ndarray, exit_: np.ndarray) -> np.ndarray:
    """Giriş şartında 1, çıkış şartında 0 (çıkış öncelikli), arada önceki durum."""
    s = pd.Series(np.where(exit_, 0.0, np.where(enter, 1.0, np.nan)))
    return s.ffill().fillna(0.0).to_numpy()


def _band(x: np.ndarray, band: float) -> np.ndarray:
    """Hedefteki `band`'dan küçük değişiklikleri yok sayar; 0'a iniş her zaman uygulanır."""
    out = np.zeros(len(x))
    cur = 0.0
    for i, t in enumerate(x):
        if not np.isfinite(t):
            t = 0.0
        if band <= 0 or t == 0.0 or abs(t - cur) >= band:
            cur = t
        out[i] = cur
    return out


def _realised_vol(close: pd.Series, n_days: float, bpd: int) -> pd.Series:
    n = max(2, int(round(n_days * bpd)))
    lr = np.log(close.astype(float)).diff()
    return lr.rolling(n, min_periods=n).std() * math.sqrt(365.0 * bpd)


def exposure(
    df: pd.DataFrame,
    bpd: int,
    sinyal: str = "trend",
    kinds=ENS_KINDS,
    lookbacks=(20, 40, 80),
    hedef_vol: float = 0.6,
    vol_gun: float = 30,
    sabit: float = 1.0,
) -> pd.Series:
    """Coin maruziyeti E(t) ∈ [0, 1] (ısınmada 0)."""
    close = df["close"].astype(float)
    if sinyal == "sabit":
        return pd.Series(float(sabit), index=df.index)
    parts = []
    if sinyal in ("trend", "trend_vol"):
        from grafik_analiz.strategies.trend import leg_target

        parts.append(leg_target(df, tuple(kinds), tuple(lookbacks), int(bpd), False))
    if sinyal in ("vol", "trend_vol"):
        rv = _realised_vol(close, vol_gun, bpd)
        parts.append((float(hedef_vol) / rv).clip(upper=1.0).fillna(0.0))
    if not parts:
        raise ValueError(f"bilinmeyen sinyal: {sinyal}")
    e = parts[0]
    for p in parts[1:]:
        e = e * p
    return e.clip(0.0, 1.0).fillna(0.0)


# ---------------------------------------------------------------- bindirme sinyali


def overlay_signal(
    data: dict,
    funding: dict,
    sinyal: str = "trend",
    bicim: str = "nakit",
    bpd: int = 6,
    kinds=ENS_KINDS,
    lookbacks=(20, 40, 80),
    hedef_vol: float = 0.6,
    vol_gun: float = 30,
    sabit: float = 1.0,
    bant: float = 0.0,
    fon_n: float = 0,
    fon_giris: float = 0.0,
    fon_cikis: float = 0.0,
    **_,
) -> dict:
    out = {}
    for c in COINS:
        spot = data[("spot", c)]
        e_spot = exposure(spot, bpd, sinyal, kinds, lookbacks, hedef_vol, vol_gun, sabit)
        if bicim == "nakit":
            out[("spot", c)] = pd.Series(_band(e_spot.to_numpy(), float(bant)), index=spot.index)
            continue
        fut = data[("futures", c)]
        idx = spot.index.union(fut.index)
        # Spot barı olmayan anlarda en son bilinen maruziyet (yalnız geçmiş).
        E = _band(e_spot.reindex(idx).ffill().fillna(0.0).to_numpy(), float(bant))
        f = funding.get(c, pd.DataFrame())
        if f is None or f.empty:
            out[("spot", c)] = pd.Series(0.0, index=spot.index)
            out[("futures", c)] = pd.Series(0.0, index=fut.index)
            continue
        allowed = np.asarray(idx >= f.index.min())
        if float(fon_n) <= 0:
            on = np.ones(len(idx), dtype=bool)
        else:
            F = _asof(_fund_avg(f, float(fon_n)), idx)
            with np.errstate(invalid="ignore"):
                on = _hysteresis(F > float(fon_giris), (F < float(fon_cikis)) | np.isnan(F)) > 0
        if bicim == "tam":
            s = np.where(on, 1.0, np.minimum(1.0, 2.0 * E))
            fp = np.where(on, 2.0 * E - 1.0, np.maximum(0.0, 2.0 * E - 1.0))
        elif bicim == "yarim":
            s = np.where(on, 1.0, E)
            fp = np.where(on, -(1.0 - E), 0.0)
        else:
            raise ValueError(f"bilinmeyen biçim: {bicim}")
        s = np.where(allowed, s, 0.0)
        fp = np.where(allowed, fp, 0.0)
        out[("spot", c)] = pd.Series(s, index=idx).reindex(spot.index).astype(float)
        out[("futures", c)] = pd.Series(fp, index=idx).reindex(fut.index).astype(float)
    return out


def legs_for(bicim: str) -> tuple:
    if bicim == "nakit":
        return tuple(("spot", c) for c in COINS)
    return tuple(leg for c in COINS for leg in (("spot", c), ("futures", c)))


def make_spec(name: str, interval: str, description: str = "", **params) -> StrategySpec:
    p = {"sinyal": "trend", "bicim": "nakit", **params, "bpd": BARS_PER_DAY[interval]}
    if p["sinyal"] in ("trend", "trend_vol"):
        p.setdefault("kinds", ENS_KINDS)
        p.setdefault("lookbacks", (20, 40, 80))
        p["kinds"] = tuple(p["kinds"])
        p["lookbacks"] = tuple(p["lookbacks"])
    return StrategySpec(name, FAMILY, interval, legs_for(p["bicim"]), overlay_signal, p, description=description)


# ---------------------------------------------------------------- tur 1 bileşenleri


@lru_cache(maxsize=1)
def _round1_registry() -> dict:
    reg = {}
    for m in ROUND1_MODULES:
        mod = importlib.import_module(f"grafik_analiz.strategies.{m}")
        for s in mod.specs():
            reg[s.name] = s
    return reg


def round1_spec(name: str) -> StrategySpec:
    return _round1_registry()[name]


def round1_futures_pool() -> list[str]:
    """Tur 1 dondurulmuşlarından bütün bacakları vadeli ve zaman dilimi 1s/4s/1g olanlar."""
    out = []
    for name, s in _round1_registry().items():
        if s.interval not in ("1h", "4h", "1d"):
            continue
        w = s.leg_weights()
        if all(leg[0] == "futures" for leg in s.legs if w.get(leg, 0.0) > 0):
            out.append(name)
    return out


def _bilesen_signal(data: dict, funding: dict, bilesen: str = "", **_) -> dict:
    s = round1_spec(bilesen)
    return s.signal_fn(data, funding, **s.params)


def bilesen_spec(name: str) -> StrategySpec:
    """Tur 1 yapılandırmasının bu ailenin defterine yazılmak üzere yeniden etiketlenmiş hali."""
    s = round1_spec(name)
    return StrategySpec(
        f"{FAMILY}_bilesen_{name}",
        FAMILY,
        s.interval,
        s.legs,
        _bilesen_signal,
        {"bilesen": name},
        s.weights,
        f"Tur 1 yapılandırması {name} (değiştirilmeden), portföy bileşeni adayı.",
    )


def _component_exposure(name: str, data: dict, funding: dict, last_close: pd.Timestamp) -> dict:
    """Bileşenin coin başına sermaye payı cinsinden maruziyeti (kendi bar zamanlarında, kapanışa göre)."""
    from grafik_analiz.research.data import load

    s = round1_spec(name)
    comp_data = {}
    for leg in s.legs:
        frame = load(leg[1], s.interval, leg[0], "dev")
        comp_data[leg] = frame[frame["close_time"] <= last_close].copy()
    comp_fund = {}
    for leg in s.legs:
        if leg[0] == "futures":
            f = funding.get(leg[1])
            if f is None:
                from grafik_analiz.research.data import load_funding

                f = load_funding(leg[1], "dev")
            comp_fund[leg[1]] = f[f.index < last_close].copy()
    sig = s.signal_fn(comp_data, comp_fund, **s.params)
    w = s.leg_weights()
    out = {}
    for leg in s.legs:
        if leg[0] != "futures" or w.get(leg, 0.0) <= 0:
            continue
        p = sig[leg]
        if isinstance(p, pd.DataFrame):
            p = p["target"]
        p = pd.Series(p, dtype=float).reindex(comp_data[leg].index).fillna(0.0).clip(-1.0, 1.0)
        out[leg[1]] = (w[leg] * p, comp_data[leg]["close_time"])
    return out


def portfoy_signal(data: dict, funding: dict, bilesenler=(), carpanlar=(), **_) -> dict:
    # Açık kesim: bileşen verisi, verilen verinin son barının kapanışından sonrasını içeremez.
    last_close = max(df["close_time"].max() for df in data.values() if len(df))
    total = {leg: np.zeros(len(df)) for leg, df in data.items()}
    for name, b in zip(bilesenler, carpanlar):
        expo = _component_exposure(name, data, funding, last_close)
        for leg, df in data.items():
            if leg[1] not in expo or len(df) == 0:
                continue
            e, comp_close = expo[leg[1]]
            pos = np.searchsorted(_ns(pd.DatetimeIndex(comp_close)), _ns(pd.DatetimeIndex(df["close_time"])), side="right") - 1
            vals = e.to_numpy(dtype=float)
            mapped = np.where(pos >= 0, vals[np.clip(pos, 0, None)], 0.0)
            total[leg] += float(b) * mapped
    n_legs = len(data)
    return {leg: pd.Series(np.clip(n_legs * x, -1.0, 1.0), index=data[leg].index) for leg, x in total.items()}


def make_portfolio_spec(name: str, bilesenler, carpanlar, description: str = "", **extra) -> StrategySpec:
    legs = tuple(("futures", c) for c in COINS)
    params = {"bilesenler": tuple(bilesenler), "carpanlar": tuple(float(round(b, 6)) for b in carpanlar), **extra}
    return StrategySpec(name, FAMILY, "1h", legs, portfoy_signal, params, description=description)


# ---------------------------------------------------------------- dondurulmuş yapılandırmalar


FON_F7 = {"fon_n": 7, "fon_giris": 0.5e-4, "fon_cikis": -0.5e-4}
"""Carry süzgeci: 7 günlük ortalama fonlama 8 saatte %0,005'i geçince açık, −%0,005'in altına inince kapalı."""

PORTFOY_BILESENLER = (
    "ml_1h_fu_PORT3_hgb_clf_H6_k3.0_ortusen_iki_temel_egspot",
    "od_dip_ret4h_fut_port3_1h",
    "kirilim_kanal4h_vadeli_iki",
    "formasyon_ucgen_kama_4h_hacim_iki",
)
PORTFOY_CARPANLAR = (0.224846, 0.453969, 0.108209, 0.212975)
"""Eşit risk: b_k ∝ 1 / σ_k (2020-01 – 2024-12 eğitim günlük getiri std'si: 0,2389 / 0,1183 / 0,4963 / 0,2522), Σ b = 1."""

FROZEN: tuple = (
    (
        "t2_bindirme_vol_nakit_1d_h0.4_n40_b0.1",
        "1d",
        {"sinyal": "vol", "bicim": "nakit", "hedef_vol": 0.4, "vol_gun": 40, "bant": 0.1},
        "(b) Oynaklık yönetimli maruziyet, kıyas. Spot BTC/ETH/SOL (her biri 1/3), günlük; coin başına "
        "pozisyon = min(1, 0,4 / son 40 günün yıllık oynaklığı) (ters oynaklık ağırlığı), 0,1 bant; "
        "zamanlama sinyali yok.",
    ),
    (
        "t2_bindirme_trend_yarim_4h_L15_b0.15_f7",
        "4h",
        {"sinyal": "trend", "bicim": "yarim", "lookbacks": (15, 30, 60), "bant": 0.15, **FON_F7},
        "(a) Trend + carry. Her coinde spot ve vadeli bacak (her biri 1/6), 4 saatlik. E = tur 1 trend "
        "topluluğu (getiri işareti, SMA, EMA kesişimi, Donchian; 15/30/60 gün), 0,15 bant. Carry açıkken "
        "spot 1, vadeli −(1−E) (trend kapalı kısım nakit-carry); 7 günlük fonlama ortalaması −%0,005'in "
        "altına inince carry kapanır (spot E, vadeli 0).",
    ),
    (
        "t2_bindirme_trendvol_tam_4h_L10_h0.3_n30_b0.1_f7",
        "4h",
        {"sinyal": "trend_vol", "bicim": "tam", "lookbacks": (10, 20, 40), "hedef_vol": 0.3, "vol_gun": 30,
         "bant": 0.1, **FON_F7},
        "(a') Trend × oynaklık + carry. Her coinde spot ve vadeli bacak (her biri 1/6), 4 saatlik. "
        "E = trend topluluğu (10/20/40 gün) × min(1, 0,3 / 30 günlük oynaklık), 0,1 bant. Carry açıkken "
        "spot 1, vadeli 2E−1; kapalıyken spot min(1, 2E), vadeli max(0, 2E−1). Carry süzgeci 7 günlük fonlama.",
    ),
    (
        "t2_bindirme_portfoy_esit_risk_sermaye",
        "portfoy",
        {},
        "(c) Önceden yazılmış kuralla (yalnız eğitim ölçüleri) seçilen 4 tur 1 yapılandırmasının eşit riskli "
        "portföyü, 1 saatlik vadeli BTC/ETH/SOL: ML sınıflandırıcı H6 iki yön, dip alımı ret4h, 4s kanal "
        "kırılımı iki yön, üçgen/kama kırılımı iki yön; çarpanlar 1/σ ile orantılı, toplam 1.",
    ),
)

FROZEN_CHECK: dict = {
    "t2_bindirme_vol_nakit_1d_h0.4_n40_b0.1": (
        "GEÇMEDİ (dev_valid 1× −%13,31, 2× −%13,60, Sharpe −0,01, 0 işlem, alfa −%4,26, beta 0,64; "
        "kıyas olarak donduruldu)."
    ),
    "t2_bindirme_trend_yarim_4h_L15_b0.15_f7": (
        "GEÇTİ (dev_valid 1× +%13,77, 2× +%11,57, Sharpe 0,58, 55 işlem, alfa +%7,45, alfa t 0,93, "
        "beta 0,16; DSR 0,076, istatistiksel olarak anlamlı değil)."
    ),
    "t2_bindirme_trendvol_tam_4h_L10_h0.3_n30_b0.1_f7": (
        "GEÇTİ (dev_valid 1× +%18,84, 2× +%16,00, Sharpe 0,69, 98 işlem, alfa +%10,14, alfa t 1,08, "
        "beta 0,18; DSR 0,0945, istatistiksel olarak anlamlı değil; trend+carry ile günlük korelasyon 0,96)."
    ),
    "t2_bindirme_portfoy_esit_risk_sermaye": (
        "GEÇMEDİ (dev_valid 1× −%1,50, 2× −%4,73, Sharpe −0,11, 297 işlem, alfa −%0,65, beta 0,00)."
    ),
}
"""dev_valid tek seferlik değerlendirmesinin candidate_check sonucu (yalnız açıklama metni;
parametreleri ve sinyali etkilemez)."""


def specs() -> list[StrategySpec]:
    """Dondurulup dev_valid'de bir kez değerlendirilen yapılandırmalar."""
    out = []
    for name, interval, params, desc in FROZEN:
        durum = FROZEN_CHECK.get(name)
        if durum:
            desc = f"{desc} candidate_check: {durum}"
        if interval == "portfoy":
            out.append(make_portfolio_spec(name, PORTFOY_BILESENLER, PORTFOY_CARPANLAR, description=desc))
        else:
            out.append(make_spec(name, interval, description=desc, **params))
    return out
