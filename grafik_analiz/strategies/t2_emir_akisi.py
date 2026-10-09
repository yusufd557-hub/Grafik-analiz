"""Emir akışı ailesi (tur 2): mumlardaki taker alım hacminden dengesizlik sinyalleri.

Bar başına alıcı-taker dengesizliği ``imb = (2·taker_buy_base − volume) / volume``
(−1…1) ve kümülatif hacim deltası ``CVD = Σ (2·taker_buy_base − volume)``.

Skor S (pozitif = akış, fiyata göre alım yönünde), ``kind``:

- ``akis``: n barlık normalleştirilmiş CVD değişimi ``Σ_n delta / Σ_n hacim``,
  L barlık kayan z-skoru.
- ``patlama``: tek bar dengesizliğinin L barlık z-skoru; ``vol_v`` verilirse
  yalnız hacim / L barlık ortalama hacim ≥ ``vol_v`` olan barlarda.
- ``uyumsuzluk``: akış z-skoru − n barlık log getiri z-skoru (CVD–fiyat
  uyumsuzluğu: akış güçlü ama fiyat zayıfsa pozitif).
- ``akis_artik``: n barlık akışın aynı n barlık log getiriyle açıklanamayan
  kısmı (L barlık kayan regresyon artığı), L barlık z-skoru.
- ``getiri``: kontrol amaçlı, akış içermeyen n barlık log getiri z-skoru
  (akışın fiyat momentumundan fazlasını taşıyıp taşımadığını ölçmek için).
- ``getiri_artik``: n barlık getirinin aynı n barlık akışla açıklanamayan kısmı
  (L barlık kayan regresyon artığı), L barlık z-skoru; dönüş yönüyle
  kullanılır (fiyat akışın gerektirdiğinden fazla düştüyse alım).
- ``cvd_aralik``: CVD'nin n barlık aralık içindeki konumu − kapanışın n barlık
  aralık içindeki konumu (−1…1; klasik CVD uyumsuzluğu).
- ``spot_vadeli``: aynı coinin spot akışı − vadeli akışı (n bar), L barlık
  z-skoru. Diğer piyasanın mumları ``research.data.load(scope="dev")`` ile
  yüklenir ve geçirilen verinin son barına açıkça kesilir.

Kural: |S| > k olduğunda tetik. ``mode="devam"`` S yönünde, ``mode="donus"``
S'nin tersine pozisyon. Pozisyon son tetikten sonra ``hold`` bar tutulur
(aynı yönde yeni tetik süreyi uzatır, ters tetik yön değiştirir).
``exit_z`` verilirse skor normale dönünce (devamda S·yön < exit_z) erken
çıkılır. ``side``: ``iki`` / ``uzun`` / ``kisa``.

Yürütme (``exec``): ``piyasa`` (protokol maliyetleri) ya da ``limit``.
Limitte giriş emri sinyal barının kapanışından ``lim_in`` bps uzakta
(alışta altında, satışta üstünde), çıkış emri ``lim_out`` bps uzakta verilir;
``lim_in``/``lim_out`` None ise o taraf piyasa emridir. ``out_timeout`` bar
sonra dolmamış çıkış piyasa emrine döner. Dolum kuralları
``research.backtest._backtest_limit`` içindedir.

Bütün hesaplar nedenseldir: kayan pencereler (``rolling``), baştan kümülatif
toplam, ``diff(+n)``; ``shift(-k)``, ortalanmış pencere ya da tam örneklem
istatistiği kullanılmaz. Tetik/tutma mantığı yalnız geçmiş barlara bakar.

``specs()`` yalnız dondurulup dev_valid'de bir kez değerlendirilen
yapılandırmaları döndürür (bkz. ``arastirma/tur2/t2_emir_akisi/RAPOR.md``).
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd

from grafik_analiz.research.evaluate import StrategySpec

FAMILY = "t2_emir_akisi"
COINS = ("BTCUSDT", "ETHUSDT", "SOLUSDT")


def legs_for(market: str, universe: str = "PORT3") -> tuple:
    if universe == "PORT3":
        return tuple((market, c) for c in COINS)
    return ((market, universe),)


# ---------------------------------------------------------------- ölçüler


def _delta(df: pd.DataFrame) -> tuple[pd.Series, pd.Series]:
    vol = df["volume"].astype(float)
    tbb = df["taker_buy_base"].astype(float)
    return 2.0 * tbb - vol, vol


def _zscore(x: pd.Series, L: int) -> pd.Series:
    mu = x.rolling(L, min_periods=L).mean()
    sd = x.rolling(L, min_periods=L).std(ddof=0)
    return (x - mu) / sd.where(sd > 0)


def _flow_from(delta: pd.Series, vol: pd.Series, n: int) -> pd.Series:
    sd = delta.rolling(n, min_periods=n).sum()
    sv = vol.rolling(n, min_periods=n).sum()
    f = sd / sv.where(sv > 0)
    # Hacimsiz pencere (borsa kesintisi): dengesizlik 0 kabul edilir.
    return f.where(~(sv <= 0), 0.0)


def flow(df: pd.DataFrame, n: int) -> pd.Series:
    d, v = _delta(df)
    return _flow_from(d, v, n)


def _bar_label(df: pd.DataFrame) -> str:
    """İlk barın açılış–kapanış farkından zaman dilimi (yalnız ilk satır)."""
    minutes = int(math.ceil((df["close_time"].iloc[0] - df.index[0]).total_seconds() / 60.0))
    return {5: "5m", 15: "15m", 60: "1h", 240: "4h", 1440: "1d"}[minutes]


def _other_market(leg: tuple, df: pd.DataFrame) -> pd.DataFrame:
    """Aynı coinin diğer piyasadaki mumları, geçirilen verinin son barına kesilmiş."""
    from grafik_analiz.research.data import load

    market, symbol = leg
    other = "spot" if market == "futures" else "futures"
    frame = load(symbol, _bar_label(df), other, scope="dev")
    # Açık kesim: geçirilen verinin son barından sonrası kullanılmaz.
    frame = frame[frame.index <= df.index[-1]]
    return frame.reindex(df.index)


def score(df: pd.DataFrame, kind: str, n: int, L: int, leg: tuple | None = None, vol_v: float | None = None) -> pd.Series:
    close = df["close"].astype(float)
    if kind == "akis":
        return _zscore(flow(df, n), L)
    if kind == "patlama":
        s = _zscore(flow(df, 1), L)
        if vol_v:
            vol = df["volume"].astype(float)
            ratio = vol / vol.rolling(L, min_periods=L).mean()
            s = s.where(ratio >= vol_v, 0.0)
        return s
    if kind == "uyumsuzluk":
        zf = _zscore(flow(df, n), L)
        zr = _zscore(np.log(close).diff(n), L)
        return zf - zr
    if kind == "akis_artik":
        # Akışın fiyat hareketiyle açıklanamayan kısmı: f − b·r, b = kayan cov(f, r) / var(r).
        f = flow(df, n)
        r = np.log(close).diff(n)
        b = f.rolling(L, min_periods=L).cov(r) / r.rolling(L, min_periods=L).var()
        return _zscore(f - b * r, L)
    if kind == "getiri":
        # Kontrol (akış değil): n barlık log getirinin z-skoru; akışın fiyat momentumundan
        # fazla bir şey taşıyıp taşımadığını ölçmek için.
        return _zscore(np.log(close).diff(n), L)
    if kind == "getiri_artik":
        # Fiyat hareketinin aynı n barlık akışla açıklanamayan kısmı: r − c·f,
        # c = kayan cov(r, f) / var(f); L barlık z-skoru (dönüş yönüyle kullanılır).
        f = flow(df, n)
        r = np.log(close).diff(n)
        c = r.rolling(L, min_periods=L).cov(f) / f.rolling(L, min_periods=L).var()
        return _zscore(r - c * f, L)
    if kind == "cvd_aralik":
        d, _ = _delta(df)
        cvd = d.cumsum()
        lo, hi = close.rolling(n, min_periods=n).min(), close.rolling(n, min_periods=n).max()
        clo, chi = cvd.rolling(n, min_periods=n).min(), cvd.rolling(n, min_periods=n).max()
        ppos = (close - lo) / (hi - lo).where(hi > lo)
        cpos = (cvd - clo) / (chi - clo).where(chi > clo)
        return cpos - ppos
    if kind == "spot_vadeli":
        if leg is None:
            raise ValueError("spot_vadeli için bacak gerekli")
        other = _other_market(leg, df)
        d_o, v_o = _delta(other)
        f_other = _flow_from(d_o.fillna(0.0), v_o.fillna(0.0), n)
        f_self = flow(df, n)
        spot_minus_fut = (f_self - f_other) if leg[0] == "spot" else (f_other - f_self)
        return _zscore(spot_minus_fut, L)
    raise ValueError(f"bilinmeyen skor türü: {kind}")


# ---------------------------------------------------------------- pozisyon


def positions(
    S: pd.Series,
    k: float,
    mode: str = "devam",
    hold: int = 12,
    side: str = "iki",
    exit_z: float | None = None,
) -> pd.Series:
    sgn = 1.0 if mode == "devam" else -1.0
    s = S.to_numpy(dtype=float)
    trig = np.where(s > k, 1.0, np.where(s < -k, -1.0, 0.0)) * sgn
    if side == "uzun":
        trig[trig < 0] = 0.0
    elif side == "kisa":
        trig[trig > 0] = 0.0
    if exit_z is None:
        t = pd.Series(trig, index=S.index)
        if hold <= 1:
            return t
        return t.replace(0.0, np.nan).ffill(limit=hold - 1).fillna(0.0)
    out = np.zeros(len(s))
    pos, age = 0.0, 0
    for i in range(len(s)):
        tr = trig[i]
        if tr != 0.0:
            pos, age = tr, 0
        elif pos != 0.0:
            age += 1
            aligned = sgn * pos * s[i]
            if age >= hold or (not np.isnan(aligned) and aligned < exit_z):
                pos, age = 0.0, 0
        out[i] = pos
    return pd.Series(out, index=S.index)


def with_limit(
    target: pd.Series,
    close: pd.Series,
    lim_in: float | None,
    lim_out: float | None,
    out_timeout: int | None = None,
) -> pd.DataFrame:
    """Hedef serisine limit fiyatları ekler (bps, sinyal barı kapanışına göre)."""
    t = target.to_numpy(dtype=float)
    c = close.to_numpy(dtype=float)
    n = len(t)
    prev = np.concatenate([[0.0], t[:-1]])
    changed = t != prev
    d = pd.Series(np.where(changed, np.sign(t - prev), np.nan)).ffill().to_numpy()
    idx = np.arange(n)
    last_change = pd.Series(np.where(changed, idx, np.nan)).ffill().to_numpy()
    age = idx - last_change
    lim = np.full(n, np.nan)
    has = ~np.isnan(d)
    if lim_in is not None:
        m = has & (t != 0.0)
        lim[m] = c[m] * (1.0 - d[m] * lim_in / 1e4)
    if lim_out is not None:
        m = has & (t == 0.0)
        if out_timeout is not None:
            m &= age < out_timeout
        lim[m] = c[m] * (1.0 - d[m] * lim_out / 1e4)
    return pd.DataFrame({"target": t, "limit": lim}, index=target.index)


# ---------------------------------------------------------------- sinyal


def sinyal(
    data: dict,
    funding: dict,
    kind: str = "akis",
    n: int = 12,
    L: int = 2000,
    k: float = 2.0,
    mode: str = "devam",
    hold: int = 12,
    side: str = "iki",
    exit_z: float | None = None,
    vol_v: float | None = None,
    exec: str = "piyasa",
    lim_in: float | None = None,
    lim_out: float | None = None,
    out_timeout: int | None = None,
) -> dict:
    out = {}
    for leg, df in data.items():
        S = score(df, kind, n, L, leg=leg, vol_v=vol_v)
        pos = positions(S, k, mode, hold, side, exit_z)
        if leg[0] == "spot":
            pos = pos.clip(lower=0.0)
        if leg[0] == "futures" and leg[1] in funding and len(funding[leg[1]]):
            # Fonlama kaydı başlamadan vadeli pozisyon açılmaz.
            first = funding[leg[1]].index[0]
            pos = pos.where(df["close_time"] >= first, 0.0)
        if exec == "limit":
            out[leg] = with_limit(pos, df["close"].astype(float), lim_in, lim_out, out_timeout)
        else:
            out[leg] = pos
    return out


def make_spec(name: str, market: str, interval: str, universe: str = "PORT3", description: str = "", **params) -> StrategySpec:
    if not name.startswith(FAMILY + "_"):
        name = f"{FAMILY}_{name}"
    return StrategySpec(
        name=name,
        family=FAMILY,
        interval=interval,
        legs=legs_for(market, universe),
        signal_fn=sinyal,
        params=dict(params),
        description=description,
    )


def specs() -> list[StrategySpec]:
    """Dondurulan ve dev_valid'de bir kez değerlendirilen yapılandırmalar."""
    return []
