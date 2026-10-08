"""Takvim / mevsimsellik ailesi ("mevsimsellik").

Bütün sinyaller nedenseldir. t barındaki hedef pozisyon, t barının kapanışında
bilinen bilgiyle verilir ve t+1 barında (bir sonraki açılıştan sonraki
açılışa kadar) tutulur. Takvim sinyalleri yalnızca **bir sonraki barın
başlangıç zamanına** bakar (takvim önceden bilinir); uyarlamalı yöntemler
yalnızca geçmiş barların getirisini (geriye dönük pencere, ``shift(+k)``)
kullanır. Fonlama kaydı yalnızca zaman damgası barın kapanışından önce/eşitse
kullanılır. Vadeli bacakta, coinin ilk fonlama kaydından önce pozisyon 0'dır
(aksi halde fonlama sessizce eksik kalır).

Yöntemler (``yontem`` parametresi):

- ``ay_donumu``: Ay dönümü. Ayın son ``a`` günü ve sonraki ayın ilk ``b``
  günü (UTC günleri, ``kayma_saat`` saat kaydırılabilir) boyunca alım, diğer
  zamanlarda nakit (vadelide ``yon="uzun_kisa"`` ise açığa satış).
- ``ay_donumu_kademeli``: a ∈ [``a_alt``, ``a_ust``] ve b ∈ [``b_alt``,
  ``b_ust``] ay dönümü pencerelerinin ortalaması (kademeli, 0…1 pozisyon).
- ``hafta_gunu``: Haftanın belirli günlerinde (``gunler``, 0 = Pazartesi, UTC)
  alım.
- ``saat``: Günün belirli saatlerinde (``saatler_uzun``; vadelide ayrıca
  ``saatler_kisa``) pozisyon. ``tz`` ile saat dilimi (ör. America/New_York,
  yaz saati dahil), ``hafta_ici`` ile yalnız hafta içi.
- ``fonlama``: Fonlama anı S (00/08/16 UTC) çevresindeki
  [S + ``bas_dk``, S + ``bas_dk`` + ``tut_dk``) penceresinde, S'den **bir
  önceki** fonlama oranı (S − 8 saat) ``esik``'in üstündeyse alım
  (``yon="kisa"`` ise açığa satış). Kullanılan oran pencerenin ilk kararından
  önce kaydedilmiştir.
- ``uyarlamali_saat``: Günün her saati için son ``L`` günün (o saate ait)
  bar getirisi ortalaması; ortalama ``esik_bp`` baz puanın üstündeyse o saatte
  alım, ``-esik_bp``'nin altındaysa (vadelide) açığa satış. Yalnız geçmiş günler
  kullanılır (ileriye yürüyen tahmin).
- ``uyarlamali_ay``: Ay içindeki her gün konumu (baştan 1..15, sondan
  -1..-16) için geçmiş ``L_ay`` ayın (``L_ay=0``: bütün geçmiş) aynı konumdaki
  günlük getiri ortalaması ile genel ortalama farkı ``esik_bp``'nin üstündeyse
  o gün alım. Yalnız geçmiş günler kullanılır.

`specs()` yalnızca dondurulup dev_valid'de bir kez değerlendirilen
yapılandırmaları döndürür (bkz. `arastirma/mevsimsellik/RAPOR.md`). Dört
yapılandırmanın hiçbiri aday şartlarını geçmedi: ay dönümü etkisi dev_train'de
güçlüydü, dev_valid'de (2024 – 2025/6) tersine döndü.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from grafik_analiz.research.evaluate import StrategySpec

FAMILY = "mevsimsellik"

COINS = ("BTCUSDT", "ETHUSDT", "SOLUSDT")

_MS = pd.Timedelta(milliseconds=1)


def legs_for(market: str, universe: str) -> tuple:
    """`universe`: tek coin sembolü, 'PORT3' (üç coin eşit) ya da 'PORT2' (BTC + ETH)."""
    if universe == "PORT3":
        return tuple((market, c) for c in COINS)
    if universe == "PORT2":
        return tuple((market, c) for c in COINS[:2])
    return ((market, universe),)


# ---------------------------------------------------------------- yardımcılar


def _next_start(df: pd.DataFrame) -> pd.DatetimeIndex:
    """Her barın kapanışından hemen sonraki barın başlangıç zamanı (takvimden, ileri bakışsız)."""
    ct = pd.DatetimeIndex(df["close_time"])
    return (ct + _MS).floor("s")


def _rel_day(ts: pd.DatetimeIndex) -> np.ndarray:
    """Ay içi gün konumu: ayın başından 1..15, sonundan -1..-16 (son gün -1)."""
    dom = np.asarray(ts.day)
    dim = np.asarray(ts.days_in_month)
    return np.where(dom <= 15, dom, dom - dim - 1)


def _futures_allowed(df: pd.DataFrame, fund: pd.DataFrame | None) -> np.ndarray:
    """Vadelide pozisyon ancak ilk fonlama kaydı barın kapanışında biliniyorsa açılır."""
    if fund is None or len(fund) == 0:
        return np.zeros(len(df), dtype=bool)
    first = fund.index.min()
    ct = pd.DatetimeIndex(df["close_time"])
    return np.asarray(ct >= first)


def _last_rate_at(times: pd.DatetimeIndex, fund: pd.DataFrame) -> np.ndarray:
    """Her zaman için damgası <= o zaman olan son fonlama oranı (yoksa NaN)."""
    if fund is None or len(fund) == 0:
        return np.full(len(times), np.nan)
    ft = fund.index
    rates = fund["funding_rate"].to_numpy(float)
    pos = ft.searchsorted(times, side="right") - 1
    out = np.full(len(times), np.nan)
    ok = pos >= 0
    out[ok] = rates[pos[ok]]
    return out


def _close_to_close(df: pd.DataFrame) -> pd.Series:
    """Barın kapanışında bilinen getiri (kapanıştan kapanışa)."""
    return df["close"].pct_change()


# ---------------------------------------------------------------- yöntemler


def _w_ay_donumu(df: pd.DataFrame, p: dict) -> np.ndarray:
    a = int(p["a"])
    b = int(p["b"])
    ns = _next_start(df) - pd.Timedelta(hours=float(p.get("kayma_saat", 0)))
    rel = _rel_day(ns)
    inside = ((rel >= -a) & (rel < 0)) | ((rel >= 1) & (rel <= b))
    return inside.astype(float)


def _w_ay_donumu_kademeli(df: pd.DataFrame, p: dict) -> np.ndarray:
    """a ∈ [a_alt, a_ust], b ∈ [b_alt, b_ust] ay dönümü pencerelerinin eşit ağırlıklı ortalaması.

    Ay sonundan k. gün (-k): a >= k olan pencerelerin payı; ay başından k. gün:
    b >= k olan pencerelerin payı. Sonuç ay sonuna doğru artan, ay başından sonra
    azalan kademeli (yamuk) pozisyondur; tek bir (a, b) seçimine bağlı kalmaz.
    """
    a_vals = np.arange(int(p["a_alt"]), int(p["a_ust"]) + 1)
    b_vals = np.arange(int(p["b_alt"]), int(p["b_ust"]) + 1)
    ns = _next_start(df) - pd.Timedelta(hours=float(p.get("kayma_saat", 0)))
    rel = _rel_day(ns)
    out = np.zeros(len(df))
    end = rel < 0
    k_end = -rel[end]
    out[end] = (a_vals[None, :] >= k_end[:, None]).mean(axis=1)
    start = rel > 0
    k_start = rel[start]
    out[start] = (b_vals[None, :] >= k_start[:, None]).mean(axis=1)
    return out


def _w_hafta_gunu(df: pd.DataFrame, p: dict) -> np.ndarray:
    gunler = [int(g) for g in p["gunler"]]
    ns = _next_start(df) - pd.Timedelta(hours=float(p.get("kayma_saat", 0)))
    return np.isin(np.asarray(ns.dayofweek), gunler).astype(float)


def _w_saat(df: pd.DataFrame, p: dict) -> np.ndarray:
    ns = _next_start(df)
    tz = p.get("tz", "UTC")
    loc = ns.tz_convert(tz) if tz != "UTC" else ns
    hour = np.asarray(loc.hour)
    out = np.zeros(len(df))
    out[np.isin(hour, [int(h) for h in p.get("saatler_uzun", [])])] = 1.0
    out[np.isin(hour, [int(h) for h in p.get("saatler_kisa", [])])] = -1.0
    if p.get("hafta_ici"):
        out[np.asarray(loc.dayofweek) >= 5] = 0.0
    return out


def _w_fonlama(df: pd.DataFrame, fund: pd.DataFrame | None, p: dict) -> np.ndarray:
    """Fonlama anı S (00/08/16 UTC) çevresinde [S + bas_dk, S + bas_dk + tut_dk) penceresi.

    Koşul, S'den bir önceki fonlama (S - 8 saat) oranıdır; bu oran pencerenin
    ilk kararından önce kaydedilmiştir (bas_dk > -480 olmalı).
    """
    bas = float(p.get("bas_dk", 0))
    if bas <= -480:
        raise ValueError("bas_dk > -480 olmalı")
    ns = _next_start(df)
    shifted = ns - pd.Timedelta(minutes=bas)
    settle = shifted.floor("8h")
    since_min = np.asarray((shifted - settle).total_seconds() / 60.0)
    in_win = since_min < float(p["tut_dk"])
    prev_rate = _last_rate_at(settle - pd.Timedelta(hours=8), fund)
    esik = float(p["esik"])
    cond = prev_rate > esik
    val = -1.0 if p.get("yon", "uzun") == "kisa" else 1.0
    return np.where(in_win & cond, val, 0.0)


def _rows_before(index: pd.Index, keys) -> np.ndarray:
    """Her anahtar için index'te anahtardan kesinlikle önceki son satırın konumu (yoksa -1)."""
    return index.searchsorted(keys, side="left") - 1


def _w_uyarlamali_saat(df: pd.DataFrame, p: dict) -> np.ndarray:
    L = int(p["L"])
    esik = float(p["esik_bp"]) / 1e4
    r = _close_to_close(df)
    # r'nin zamanı: barın kapanışı. Bar başlangıç saati = index saati.
    day = r.index.floor("1D")
    hour = r.index.hour
    tab = pd.DataFrame({"d": day, "h": hour, "r": r.to_numpy()}).pivot_table(index="d", columns="h", values="r", aggfunc="mean")
    tab = tab.reindex(columns=range(24))
    est = tab.rolling(L, min_periods=max(20, L // 2)).mean()
    ns = _next_start(df)
    # D günü H saati için tahmin: D'den kesinlikle önceki son günün satırı (son L gün).
    rows = _rows_before(est.index, ns.floor("1D"))
    nh = np.asarray(ns.hour)
    vals = np.full(len(df), np.nan)
    ok = rows >= 0
    vals[ok] = est.to_numpy()[rows[ok], nh[ok]]
    out = np.zeros(len(df))
    out[vals > esik] = 1.0
    if p.get("kisa", True):
        out[vals < -esik] = -1.0
    return out


def _w_uyarlamali_ay(df: pd.DataFrame, p: dict) -> np.ndarray:
    """Günlük barlarla: her gün konumunun geçmiş ortalaması − genel geçmiş ortalama."""
    L = int(p.get("L_ay", 0))
    esik = float(p["esik_bp"]) / 1e4
    min_ay = int(p.get("min_ay", 12))
    r = _close_to_close(df)  # gün D'nin getirisi, D kapanışında bilinir
    rel = _rel_day(r.index)
    month_start = r.index.tz_localize(None).to_period("M").to_timestamp()
    tab = pd.DataFrame({"m": month_start, "k": rel, "r": r.to_numpy()}).pivot_table(index="m", columns="k", values="r", aggfunc="mean")
    allm = pd.Series(r.to_numpy(), index=month_start).groupby(level=0).mean()
    if L > 0:
        pos_mean = tab.rolling(L, min_periods=min_ay).mean()
        gen = allm.rolling(L, min_periods=min_ay).mean()
    else:
        pos_mean = tab.expanding(min_periods=min_ay).mean()
        gen = allm.expanding(min_periods=min_ay).mean()
    est = pos_mean.sub(gen, axis=0)
    ns = _next_start(df)
    nmonth = ns.tz_localize(None).to_period("M").to_timestamp()
    # M ayı için tahmin: M'den kesinlikle önceki aylar.
    rows = _rows_before(est.index, nmonth)
    cols = est.columns.get_indexer(_rel_day(ns))
    vals = np.full(len(df), np.nan)
    ok = (rows >= 0) & (cols >= 0)
    vals[ok] = est.to_numpy()[rows[ok], cols[ok]]
    out = np.zeros(len(df))
    out[vals > esik] = 1.0
    return out


def sinyal(data: dict, funding: dict, yontem: str = "ay_donumu", yon: str = "uzun", **p) -> dict:
    out = {}
    for leg, df in data.items():
        market, sym = leg
        fund = funding.get(sym) if market == "futures" else None
        p2 = dict(p, yon=yon)
        if yontem == "ay_donumu":
            w = _w_ay_donumu(df, p2)
        elif yontem == "ay_donumu_kademeli":
            w = _w_ay_donumu_kademeli(df, p2)
        elif yontem == "hafta_gunu":
            w = _w_hafta_gunu(df, p2)
        elif yontem == "saat":
            w = _w_saat(df, p2)
        elif yontem == "fonlama":
            w = _w_fonlama(df, fund, p2)
        elif yontem == "uyarlamali_saat":
            w = _w_uyarlamali_saat(df, p2)
        elif yontem == "uyarlamali_ay":
            w = _w_uyarlamali_ay(df, p2)
        else:
            raise ValueError(f"bilinmeyen yöntem: {yontem}")
        w = np.asarray(w, dtype=float)
        if yontem in ("ay_donumu", "hafta_gunu"):
            if yon == "uzun_kisa":
                w = np.where(w > 0, 1.0, -1.0)
            elif yon == "kisa":
                w = -w
        if market == "spot":
            w = np.clip(w, 0.0, 1.0)
        else:
            w = np.clip(w, -1.0, 1.0)
            w = np.where(_futures_allowed(df, fund), w, 0.0)
        out[leg] = pd.Series(w, index=df.index)
    return out


def make_spec(name: str, interval: str, market: str, universe: str, params: dict, description: str = "") -> StrategySpec:
    return StrategySpec(
        name=name,
        family=FAMILY,
        interval=interval,
        legs=legs_for(market, universe),
        signal_fn=sinyal,
        params=dict(params),
        description=description,
    )


# ---------------------------------------------------------------- dondurulmuş yapılandırmalar


FROZEN: list[dict] = [
    {
        "name": "tom_1d_fut_PORT3_a4_b5",
        "interval": "1d",
        "market": "futures",
        "universe": "PORT3",
        "params": {"yontem": "ay_donumu", "a": 4, "b": 5},
        "description": "Ay dönümü: ayın son 4 günü + sonraki ayın ilk 5 günü (UTC) vadeli alım, BTC/ETH/SOL eşit ağırlık. candidate_check GEÇMEDİ: dev_valid net -%44,2 (2x: -%45,6), Sharpe -0,98.",
    },
    {
        "name": "tom_1d_spot_PORT3_a4_b5",
        "interval": "1d",
        "market": "spot",
        "universe": "PORT3",
        "params": {"yontem": "ay_donumu", "a": 4, "b": 5},
        "description": "Ay dönümü: ayın son 4 günü + sonraki ayın ilk 5 günü (UTC) spot alım, BTC/ETH/SOL eşit ağırlık. candidate_check GEÇMEDİ: dev_valid net -%42,2 (2x: -%44,6), Sharpe -0,91.",
    },
    {
        "name": "tom_1d_fut_PORT2_a4_b5",
        "interval": "1d",
        "market": "futures",
        "universe": "PORT2",
        "params": {"yontem": "ay_donumu", "a": 4, "b": 5},
        "description": "Ay dönümü: ayın son 4 günü + sonraki ayın ilk 5 günü (UTC) vadeli alım, yalnız BTC+ETH eşit ağırlık. candidate_check GEÇMEDİ: dev_valid net -%40,5 (2x: -%42,0), Sharpe -1,01.",
    },
    {
        "name": "tomk_1d_fut_PORT3_a2-5_b2-5",
        "interval": "1d",
        "market": "futures",
        "universe": "PORT3",
        "params": {"yontem": "ay_donumu_kademeli", "a_alt": 2, "a_ust": 5, "b_alt": 2, "b_ust": 5},
        "description": "Kademeli ay dönümü: a, b = 2..5 pencerelerinin ortalaması (ay sonundan 5 gün önce 0,25'ten 1'e çıkar, ayın 3. gününden sonra 0'a iner), vadeli alım, BTC/ETH/SOL eşit ağırlık. candidate_check GEÇMEDİ: dev_valid net -%36,2 (2x: -%37,8), Sharpe -0,94.",
    },
]
"""Arama bitince donduruldu (bkz. arastirma/mevsimsellik/NOTLAR.md): dev_valid'de bir kez değerlendirilen yapılandırmalar."""


def specs() -> list[StrategySpec]:
    return [make_spec(f["name"], f["interval"], f["market"], f["universe"], f["params"], f.get("description", "")) for f in FROZEN]
