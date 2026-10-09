"""t2_lead_lag ailesi (protokol sürüm 2): öncü–izleyen (lead–lag) ilişkileri, USDⓈ-M vadeli.

Beş sinyal türü (``tur``), hepsi aynı zaman diliminde, aynı açılış zamanlı mumlarla:

- ``yetis`` — coinler arası yetişme: izleyen coinin (``islem``) son ``k`` barlık
  getirisi ile liderin (``lider``) getirisinin kayan betayla ölçeklenmiş hali
  arasındaki fark (artık) e = r_iz(k) − β·r_lid(k). z = e / σ_e (σ_e: 1 barlık
  artığın ``win`` barlık kayan std'si × √k; β ve σ bir önceki bara kadar).
  Skor s = −z: izleyen geride kaldıysa (s > 0) liderin yönünde alınır.
  ``lider_esik`` verilirse liderin kendi z-skoru da bu eşiği aynı yönde
  aşmalıdır (BTC büyük hareket etti, izleyen geride kaldı).
  ``hedge=True``: izleyen bacaklar sermayenin yarısını eşit paylaşır, lider
  bacağı diğer yarıdır ve −ortalama(β·izleyen pozisyonu) tutar (dolar/beta
  yaklaşık nötr).
- ``lider`` — izleyen, liderin son ``k`` barlık getirisinin z-skoru yönünde
  (``yon=-1`` ile ters yönde) tutulur; izleyenin kendi hareketi yok sayılır.
- ``spot_vadeli`` — spot öncülüğü: kaynak coinlerin (``kaynak``: "kendi",
  coin sembolü ya da "hepsi") spot getirisi − vadeli getirisi (aynı bar, k bar
  toplamı), 1 barlık farkın kayan std'sine göre z. Skor s = z (spot vadeliden
  çok yükseldiyse vadeli uzun).
- ``baz`` — vadeli/spot log fiyat farkı (baz) düzeyinin kayan z-skoru;
  s = −z (vadeli spota göre pahalıysa kısa).
- ``prim`` — Binance prim endeksi (vadeli prim, ``prim_dilim`` mumları)
  kapanışının kayan z-skoru; s = −z. Prim verisi ``research.data.load_premium
  (scope="dev")`` ile yüklenir, geçirilen verinin son bar kapanışına kesilir
  ve her bara yalnız kapanış anı barın kapanışından sonra olmayan prim mumu
  eşlenir.

Tetik: |s| > ``esik`` → yön = ``yon`` · sign(s). Pozisyon son tetikten sonra
``tut`` bar tutulur; yeni tetik süreyi uzatır, ters tetik yönü çevirir.
``taraf="uzun"`` (ya da ``"kisa"``) yalnız o yöndeki tetikleri kullanır
(varsayılan ``"iki"``: iki yön).

Bilgi bacakları: sinyal için gereken ama işlem görmeyen vadeli seriler
(örneğin yalnız ETH/SOL işlenirken BTC vadeli) sıfır ağırlıklı bacak olarak
verilir; hedefleri hep 0'dır. Spot mumları ise ``research.data.load(scope=
"dev")`` ile signal_fn içinde yüklenir ve geçirilen verinin son bar
kapanışına kesilir (sıfır ağırlıklı spot bacağı 15m/1h'de birleşik indeksi
vadeli verinin başlangıcından öteye uzatırdı). Böylece ileri bakış denetimi
(`assert_causal`) bu serileri de keser.

Limit emir (``limit_bps``): pozisyon değişimi sinyal barının kapanışından
``limit_bps`` uzakta (alışta altında, satışta üstünde) limit emirle denenir.
``limit_mod``: "giris" (yalnız maruziyet artarken ya da yön dönerken), "cikis"
(yalnız azalırken), "tum" (her değişimde). Dolmazsa sonraki barlarda o barın
kapanışından yeniden denenir; ``limit_bar`` verilirse değişimden bu kadar bar
sonra piyasa emrine dönülür. Emrin dolup dolmadığını strateji bilmez; backtest
bacak bacak simüle eder.

Hizalama ve nedensellik: diğer coinlerin/piyasaların mumları işlem bacağının
açılış zamanlarına göre eşlenir (aynı anda kapanan barlar); eksik barda sinyal
yoktur. Bütün istatistikler geriye dönük kayan pencerelerledir (``shift(+1)``),
tam örneklem istatistiği ya da ``shift(-k)`` yoktur.

`specs()` yalnız dondurulup iç doğrulamada bir kez ölçülen yapılandırmaları
döndürür (bkz. ``arastirma/tur2/t2_lead_lag/RAPOR.md``).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from grafik_analiz.research.evaluate import StrategySpec

FAMILY = "t2_lead_lag"
FUT = "futures"
SPOT = "spot"
COINS = ("BTCUSDT", "ETHUSDT", "SOLUSDT")
VARSAYILAN_WIN = {"5m": 288, "15m": 96, "1h": 168, "4h": 42}


# ---------------------------------------------------------------- yardımcılar


def _logret(df: pd.DataFrame, index: pd.Index | None = None) -> pd.Series:
    """Kapanıştan kapanışa log getiri. ``index`` verilirse kapanış önce bu açılış
    zamanlarına eşlenir, sonra fark alınır (eksik barda getiri NaN olur; iki
    barlık getiri tek bara yazılmaz)."""
    c = df["close"].astype(float)
    if index is not None:
        c = c.reindex(index)
    return np.log(c).diff()


def _on(series: pd.Series, index: pd.Index) -> pd.Series:
    """Aynı açılış zamanlı barlara eşle (eksik bar → NaN)."""
    return series.reindex(index)


def _last_close(data: dict) -> pd.Timestamp:
    """Geçirilen verideki en son bar kapanışı (ek veriler buna kesilir)."""
    return max(frame["close_time"].max() for frame in data.values())


def _spot_frame(symbol: str, interval: str, data: dict) -> pd.DataFrame:
    """Spot mumları: ``research.data.load(scope="dev")`` ile yüklenir ve geçirilen
    verinin son bar kapanışına kesilir (ileri bakış denetimi kesimi de keser)."""
    from grafik_analiz.research.data import load

    s = load(symbol, interval, SPOT, scope="dev")
    return s[s["close_time"] <= _last_close(data)]


def _sources(tur: str, coin: str, kaynak) -> list[str]:
    if tur not in ("spot_vadeli", "baz"):
        return []
    if kaynak in (None, "kendi"):
        return [coin]
    if kaynak == "hepsi":
        return list(COINS)
    if isinstance(kaynak, (list, tuple)):
        return list(kaynak)
    return [kaynak]


def _hold(trig: pd.Series, tut: int) -> pd.Series:
    """Son tetik yönünü ``tut`` bar boyunca taşı (tetik barı dahil)."""
    t = trig.where(trig != 0)
    return t.ffill(limit=max(0, int(tut) - 1)).fillna(0.0)


def _orders(target: pd.Series, close: pd.Series, bps: float | None, mod: str, bar: int | None):
    if bps is None:
        return target
    t = target.fillna(0.0).astype(float)
    prev = t.shift(1).fillna(0.0)
    chg = t - prev
    changed = chg != 0
    direction = np.sign(chg).where(changed).ffill().fillna(0.0)
    entry = (t.abs() > prev.abs()) | ((np.sign(t) != np.sign(prev)) & (t != 0))
    kind = pd.Series(np.where(changed, np.where(entry, 1.0, -1.0), np.nan), index=t.index).ffill()
    age = t.groupby(changed.cumsum()).cumcount()
    if mod == "tum":
        use = pd.Series(True, index=t.index)
    elif mod == "giris":
        use = kind == 1.0
    elif mod == "cikis":
        use = kind == -1.0
    else:
        raise ValueError(f"bilinmeyen limit_mod: {mod}")
    if bar is not None:
        use = use & (age < int(bar))
    lim = close.astype(float) * (1.0 - direction * float(bps) / 1e4)
    lim = lim.where(use & (direction != 0))
    return pd.DataFrame({"target": t, "limit": lim})


def _premium_on(symbol: str, frame: pd.DataFrame, dilim: str) -> pd.Series:
    """Prim endeksi kapanışı, her bara yalnız kapanmış prim mumu (kesik veriyle)."""
    from grafik_analiz.research.data import load_premium

    p = load_premium(symbol, dilim, scope="dev")
    last = frame["close_time"].max()
    p = p[p["close_time"] <= last]  # geçirilen verinin son bar kapanışına kes
    left = pd.DataFrame({"t": frame["close_time"].to_numpy()}, index=frame.index)
    right = pd.DataFrame({"t": p["close_time"].to_numpy(), "p": p["close"].astype(float).to_numpy()})
    left["t"] = left["t"].astype("datetime64[ns, UTC]")
    right["t"] = right["t"].astype("datetime64[ns, UTC]")
    # Eski prim mumu taşınmasın: en fazla bir prim dilimi geriden gelen mum kullanılır.
    merged = pd.merge_asof(
        left.reset_index(), right.sort_values("t"), on="t", direction="backward", tolerance=pd.Timedelta(dilim)
    )
    return pd.Series(merged["p"].to_numpy(), index=frame.index)


def _zscore_level(x: pd.Series, win: int) -> pd.Series:
    mu = x.rolling(win, min_periods=win // 2).mean().shift(1)
    sd = x.rolling(win, min_periods=win // 2).std().shift(1)
    return (x - mu) / sd


# ---------------------------------------------------------------- skorlar


def _score_yetis(data, coin, lider, k, win, lider_esik):
    f = data[(FUT, coin)]
    idx = f.index
    rf = _logret(f)
    rl = _logret(data[(FUT, lider)], idx)
    mp = max(2, win // 2)
    beta = (rf.rolling(win, min_periods=mp).cov(rl) / rl.rolling(win, min_periods=mp).var()).shift(1)
    res1 = rf - beta * rl
    sd_e = res1.rolling(win, min_periods=mp).std().shift(1) * np.sqrt(k)
    e = rf.rolling(k).sum() - beta * rl.rolling(k).sum()
    s = -(e / sd_e)
    if lider_esik is not None:
        zl = rl.rolling(k).sum() / (rl.rolling(win, min_periods=mp).std().shift(1) * np.sqrt(k))
        ok = (zl.abs() > lider_esik) & (np.sign(zl) == np.sign(s))
        s = s.where(ok, 0.0)
    return s, beta


def _score_lider(data, coin, lider, k, win):
    """Liderin son k barlık getirisinin z-skoru (izleyenin kendi hareketi yok sayılır)."""
    idx = data[(FUT, coin)].index
    rl = _logret(data[(FUT, lider)], idx)
    mp = max(2, win // 2)
    return rl.rolling(k).sum() / (rl.rolling(win, min_periods=mp).std().shift(1) * np.sqrt(k))


def _score_spot_vadeli(data, coin, kaynak, k, win, interval):
    idx = data[(FUT, coin)].index
    zs = []
    mp = max(2, win // 2)
    for src in _sources("spot_vadeli", coin, kaynak):
        fut = data[(FUT, src)]
        rf = _logret(fut, idx)
        rs = _logret(_spot_frame(src, interval, data), idx)
        d = rs - rf
        sd = d.rolling(win, min_periods=mp).std().shift(1) * np.sqrt(k)
        zs.append(d.rolling(k).sum() / sd)
    return pd.concat(zs, axis=1).mean(axis=1, skipna=False)


def _score_baz(data, coin, kaynak, win, interval):
    idx = data[(FUT, coin)].index
    zs = []
    for src in _sources("baz", coin, kaynak):
        cf = data[(FUT, src)]["close"].astype(float).reindex(idx)
        cs = _spot_frame(src, interval, data)["close"].astype(float).reindex(idx)
        b = np.log(cf / cs)
        zs.append(-_zscore_level(b, win))
    return pd.concat(zs, axis=1).mean(axis=1, skipna=False)


def _score_prim(data, coin, win, prim_dilim):
    f = data[(FUT, coin)]
    p = _premium_on(coin, f, prim_dilim)
    return -_zscore_level(p, win)


# ---------------------------------------------------------------- sinyal


def signal_fn(
    data: dict,
    funding: dict,
    tur: str = "yetis",
    islem: tuple = ("ETHUSDT", "SOLUSDT"),
    lider: str = "BTCUSDT",
    kaynak=None,
    k: int = 1,
    win: int | None = None,
    esik: float = 3.0,
    lider_esik: float | None = None,
    tut: int = 3,
    yon: int = 1,
    hedge: bool = False,
    prim_dilim: str = "1h",
    limit_bps: float | None = None,
    limit_mod: str = "giris",
    limit_bar: int | None = None,
    taraf: str = "iki",
    interval: str = "5m",
) -> dict:
    win = int(win or VARSAYILAN_WIN.get(interval, 288))
    out: dict = {}
    targets: dict = {}
    betas: dict = {}
    for coin in islem:
        if tur == "yetis":
            s, beta = _score_yetis(data, coin, lider, k, win, lider_esik)
            betas[coin] = beta
        elif tur == "lider":
            s = _score_lider(data, coin, lider, k, win)
        elif tur == "spot_vadeli":
            s = _score_spot_vadeli(data, coin, kaynak, k, win, interval)
        elif tur == "baz":
            s = _score_baz(data, coin, kaynak, win, interval)
        elif tur == "prim":
            s = _score_prim(data, coin, win, prim_dilim)
        else:
            raise ValueError(f"bilinmeyen tür: {tur}")
        trig = np.sign(s).where(s.abs() > esik, 0.0).fillna(0.0) * float(yon)
        if taraf == "uzun":
            trig = trig.clip(lower=0.0)
        elif taraf == "kisa":
            trig = trig.clip(upper=0.0)
        elif taraf != "iki":
            raise ValueError(f"bilinmeyen taraf: {taraf}")
        targets[coin] = _hold(trig, tut)
    if hedge and tur == "yetis":
        idx = data[(FUT, lider)].index
        parts = [(_on(targets[c], idx).fillna(0.0) * _on(betas[c], idx).fillna(1.0).clip(0.0, 2.0)) for c in islem]
        targets[lider] = (-pd.concat(parts, axis=1).mean(axis=1)).clip(-1.0, 1.0)
    for leg, frame in data.items():
        market, coin = leg
        if market == FUT and coin in targets:
            out[leg] = _orders(targets[coin].reindex(frame.index).fillna(0.0), frame["close"], limit_bps, limit_mod, limit_bar)
        else:
            out[leg] = pd.Series(0.0, index=frame.index)
    return out


# ---------------------------------------------------------------- spec


def make_spec(name: str, interval: str, description: str = "", **params) -> StrategySpec:
    tur = params.get("tur", "yetis")
    islem = tuple(params.get("islem", ("ETHUSDT", "SOLUSDT")))
    params["islem"] = list(islem)
    lider = params.get("lider", "BTCUSDT")
    hedge = bool(params.get("hedge", False))
    legs: list = [(FUT, c) for c in islem]
    weights: dict = {}
    if tur in ("yetis", "lider"):
        if lider not in islem:
            legs.append((FUT, lider))
        if hedge and tur == "yetis":
            for c in islem:
                weights[(FUT, c)] = 0.5 / len(islem)
            weights[(FUT, lider)] = 0.5
    # Spot mumları signal_fn içinde yüklenir; yalnız kaynak coinlerin vadeli
    # mumları (işlem görmüyorsa) sıfır ağırlıklı bilgi bacağı olur.
    srcs = sorted({s for c in islem for s in _sources(tur, c, params.get("kaynak"))})
    for s in srcs:
        if (FUT, s) not in legs:
            legs.append((FUT, s))
    if not weights:
        for leg in legs:
            weights[leg] = (1.0 / len(islem)) if (leg[0] == FUT and leg[1] in islem) else 0.0
    full = f"{FAMILY}_{name}" if not name.startswith(FAMILY) else name
    return StrategySpec(
        name=full,
        family=FAMILY,
        interval=interval,
        legs=tuple(legs),
        signal_fn=signal_fn,
        params={**params, "interval": interval},
        weights=weights,
        description=description,
    )


_COINS3 = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
_LIMIT = dict(limit_bps=2.0, limit_mod="tum", limit_bar=2)

DONDURULAN = [
    (
        "baz_5m_kendi_w288_e6_t12_limt2b2",
        "5m",
        dict(tur="baz", islem=_COINS3, kaynak="kendi", win=288, esik=6.0, tut=12, **_LIMIT),
        "Coinin kendi bazı (vadeli/spot log fiyat farkı) 1 günlük kayan z-skoru |z|>6: iskontoda uzun, primde "
        "kısa, 12 bar (1 saat) tut; 5m, iki yön, limit emir.",
    ),
    (
        "baz_15m_kendi_w192_e5_t8_limt2b2",
        "15m",
        dict(tur="baz", islem=_COINS3, kaynak="kendi", win=192, esik=5.0, tut=8, **_LIMIT),
        "Coinin kendi bazı 2 günlük kayan z-skoru |z|>5, 8 bar (2 saat) tut; 15m, iki yön, limit emir.",
    ),
    (
        "sv_5m_hepsi_k6_e4_t36_limt2b2",
        "5m",
        dict(tur="spot_vadeli", islem=_COINS3, kaynak="hepsi", k=6, esik=4.0, tut=36, **_LIMIT),
        "Spot öncülüğü: üç coinin son 6 barlık (30 dk) spot−vadeli getiri farkı z-skorlarının ortalaması |z|>4 "
        "→ vadeli o yönde, 36 bar (3 saat) tut; 5m, iki yön, limit emir.",
    ),
    (
        "baz_5m_hepsi_w288_e5_t12_uzun_limt2b2",
        "5m",
        dict(tur="baz", islem=_COINS3, kaynak="hepsi", win=288, esik=5.0, tut=12, taraf="uzun", **_LIMIT),
        "Üç coinin baz z-skorlarının ortalaması < −5 (vadeli piyasa genelinde iskontoda) → üç vadeliye uzun, "
        "12 bar tut; 5m, yalnız uzun, limit emir.",
    ),
    (
        "sv_5m_hepsi_k4_e4_t12_uzun_limt2b2",
        "5m",
        dict(tur="spot_vadeli", islem=_COINS3, kaynak="hepsi", k=4, esik=4.0, tut=12, taraf="uzun", **_LIMIT),
        "Spot öncülüğü: üç coinin son 4 barlık spot−vadeli getiri farkı z ortalaması > 4 → üç vadeliye uzun, "
        "12 bar tut; 5m, yalnız uzun, limit emir.",
    ),
]
"""Dondurulan yapılandırmalar (ad, zaman dilimi, parametreler, açıklama). Seçim yalnız dev_train'e göre;
gerekçe ``arastirma/tur2/t2_lead_lag/NOTLAR.md`` (dondurma kararı)."""

SONUC: dict[str, str] = {}
"""İç doğrulama sonucu (candidate_check), değerlendirmeden sonra açıklamaya eklenir; parametreleri değiştirmez."""


def specs() -> list[StrategySpec]:
    """Dondurulmuş ve iç doğrulamada bir kez ölçülen yapılandırmalar (RAPOR.md)."""
    out = []
    for ad, iv, params, aciklama in DONDURULAN:
        sonuc = SONUC.get(ad, "")
        desc = aciklama + (f" İç doğrulama: {sonuc}" if sonuc else "")
        out.append(make_spec(ad, iv, description=desc, **{k: (list(v) if isinstance(v, list) else v) for k, v in params.items()}))
    return out
