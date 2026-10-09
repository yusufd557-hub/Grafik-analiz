"""t2_cift ailesi (protokol sürüm 2): çift / yayılım ortalamaya dönüşü, piyasa nötr, vadeli.

Çiftler: ETH/BTC, SOL/BTC, SOL/ETH (A/B: A uzun + B kısa "yayılım uzun" demektir).
Her iki bacak USDⓈ-M vadelidir; fonlama backtest'te bacak bacak hesaplanır.

Yayılım ve hedge oranı (``hedge``), hepsi geriye dönük kayan pencerelerle:

- ``bir``: 1:1 dolar nötr; yayılım S = log A − log B.
- ``oyn``: oynaklık oranı h = σ(rA)/σ(rB), ``hedge_win`` barlık bar getirilerinden.
- ``beta``: B'ye göre OLS getiri betası h = cov(rA, rB)/var(rB), ``hedge_win`` bar.
  ``oyn`` ve ``beta`` için yayılım, bir önceki barın oranıyla hedge'lenmiş log
  getirilerin kümülatif toplamıdır: S_t = Σ (rA_t − h_{t−1}·rB_t).
- ``ols``: log fiyat düzeylerinde kayan OLS (log A = c + h·log B, ``z_win`` bar).
  z = (log A − c − h·log B) / artık std; aynı pencerenin katsayılarıyla.

z-skoru (``bir``/``oyn``/``beta``): z = (S − SMA_L(S)) / std_L(S), L = ``z_win``.

Durum makinesi (çift başına, baştan ileri doğru yürür):

- Pozisyon yokken z > ``z_in`` → yayılım kısa (A −, B +); z < −``z_in`` → yayılım uzun.
  ``teyit``: giriş için z'nin dönmeye başlamış olması gerekir (|z_t| < |z_{t−1}|).
- Çıkış: uzunda z ≥ −``z_exit``, kısada z ≤ ``z_exit`` (z_exit = 0 → ortalamada).
- Durdurma: |z| ≥ ``z_stop`` (yapı kırılması) ya da ``max_bar`` bar dolunca.
  Durdurmadan sonra |z| < ``z_in`` olana kadar yeni giriş açılmaz.
- Hedge oranı girişte dondurulur; işlem boyunca bacak pozisyonları sabittir.
  Bacak büyüklükleri (1, h)/max(1, h); h, [``h_min``, ``h_max``] aralığına kırpılır.

Rejim filtresi (``rejim``), yalnız yeni girişleri engeller:

- ``trend``: uzun pencereli z (``rejim_win`` bar) aynı yönde ``rejim_esik``'i
  aşıyorsa (yayılım uzun vadede o yöne trend yapıyorsa) giriş yok.
- ``yo``: kayan AR(1) yarı ömrü (``rejim_win`` bar) ``rejim_esik`` bardan uzunsa
  (ortalamaya dönüş zayıfsa) giriş yok.

Portföy: birden çok çift verilirse coin başına net pozisyon = Σ çift birimleri / m
(m: bir coinin en çok kaç çiftte geçtiği). Bacak ağırlıkları eşittir (toplam 1);
bacak pozisyonu −1…1 aralığındadır, kaldıraç yoktur.

Limit emir (``limit_bps``): pozisyon değişimi (``limit_mod="giris"``: yalnız
maruziyet artarken; ``"tum"``: her değişimde) ilk ``limit_bar`` bar boyunca
kapanış ∓ ``limit_bps`` fiyatından limit emirle denenir, sonra piyasa emrine
döner. Emrin dolup dolmadığını strateji bilmez; backtest bacak bacak simüle eder
(bir bacağın dolup diğerinin dolmaması da dahil).

Fonlama koruması: bir coinin ilk fonlama kaydı barın kapanışından sonra ise o
coinle pozisyon açılmaz. Verisi olmayan (ya da o barda boşlukta olan) coinle
yeni giriş yapılmaz.

Bütün hesaplar nedenseldir: t barındaki değer yalnız t ve önceki barların
kapanmış verisiyle hesaplanır (rolling pencereler, ``shift(+k)``, ileri yürüyen
durum makinesi). Tam örneklem istatistiği ya da ``shift(-k)`` yoktur.

`specs()` yalnız dondurulup iç doğrulamada bir kez ölçülen yapılandırmaları
döndürür (bkz. ``arastirma/tur2/t2_cift/RAPOR.md``).
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd

from grafik_analiz.research.evaluate import StrategySpec

FAMILY = "t2_cift"
FUT = "futures"
COINS = ("BTCUSDT", "ETHUSDT", "SOLUSDT")
PAIRS = {
    "ETHBTC": ("ETHUSDT", "BTCUSDT"),
    "SOLBTC": ("SOLUSDT", "BTCUSDT"),
    "SOLETH": ("SOLUSDT", "ETHUSDT"),
}


# ---------------------------------------------------------------- yardımcılar


def _panel(data: dict) -> tuple[pd.DataFrame, pd.DataFrame, pd.Series]:
    """(kapanış ileri doldurulmuş, gerçek bar maskesi, bar kapanış anı) — semboller sütunda."""
    index = None
    for frame in data.values():
        index = frame.index if index is None else index.union(frame.index)
    close, real = {}, {}
    delta = None
    for (market, sym), frame in data.items():
        c = frame["close"].astype(float).reindex(index)
        real[sym] = c.notna()
        close[sym] = c.ffill()
        if delta is None and "close_time" in frame and len(frame):
            delta = pd.Timestamp(frame["close_time"].iloc[0]) - frame.index[0]
    if delta is None:
        delta = (index[1] - index[0]) if len(index) > 1 else pd.Timedelta(0)
    bar_close = pd.Series(index + delta, index=index)
    return pd.DataFrame(close, index=index), pd.DataFrame(real, index=index), bar_close


def _spread_z(
    la: pd.Series,
    lb: pd.Series,
    hedge: str,
    hedge_win: int,
    z_win: int,
    z_tur: str = "duzey",
    k: int = 1,
    vol_win: int = 500,
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """(z, h, S): z-skoru, o barda bilinen hedge oranı ve yayılım serisi.

    ``z_tur="duzey"``: yayılımın kayan ortalamadan sapması (z_win).
    ``z_tur="sok"``: son ``k`` barlık yayılım hareketi / (hareketten önceki ``vol_win``
    barlık bar başı yayılım oynaklığı × √k).
    """
    if z_tur == "sok" and hedge == "ols":
        raise ValueError("sok modu ols hedge ile kullanılmaz")
    if hedge == "bir":
        s = la - lb
        h = pd.Series(1.0, index=la.index)
    elif hedge in ("oyn", "beta"):
        ra, rb = la.diff(), lb.diff()
        if hedge == "oyn":
            h = ra.rolling(hedge_win, min_periods=hedge_win).std() / rb.rolling(hedge_win, min_periods=hedge_win).std()
        else:
            cov = ra.rolling(hedge_win, min_periods=hedge_win).cov(rb)
            var = rb.rolling(hedge_win, min_periods=hedge_win).var()
            h = cov / var
        r_s = ra - h.shift(1) * rb
        s = r_s.cumsum()
        s[r_s.isna()] = np.nan
    elif hedge == "ols":
        mx = lb.rolling(z_win, min_periods=z_win).mean()
        my = la.rolling(z_win, min_periods=z_win).mean()
        vx = lb.rolling(z_win, min_periods=z_win).var()
        vy = la.rolling(z_win, min_periods=z_win).var()
        cxy = la.rolling(z_win, min_periods=z_win).cov(lb)
        h = cxy / vx
        c = my - h * mx
        resid = la - c - h * lb
        rvar = (vy - h * cxy).clip(lower=0.0)
        z = resid / np.sqrt(rvar)
        return z.replace([np.inf, -np.inf], np.nan), h, resid
    else:
        raise ValueError(f"bilinmeyen hedge: {hedge}")
    if z_tur == "sok":
        vol = s.diff().rolling(vol_win, min_periods=vol_win).std().shift(k)
        z = (s - s.shift(k)) / (vol * math.sqrt(k))
        return z.replace([np.inf, -np.inf], np.nan), h, s
    if z_tur != "duzey":
        raise ValueError(f"bilinmeyen z_tur: {z_tur}")
    m = s.rolling(z_win, min_periods=z_win).mean()
    sd = s.rolling(z_win, min_periods=z_win).std()
    z = (s - m) / sd
    return z.replace([np.inf, -np.inf], np.nan), h, s


def _regime(s: pd.Series, rejim: str | None, win: int | None) -> pd.Series | None:
    if not rejim:
        return None
    if rejim == "trend":
        m = s.rolling(win, min_periods=win).mean()
        sd = s.rolling(win, min_periods=win).std()
        return (s - m) / sd
    if rejim == "yo":
        ds = s.diff()
        lag = s.shift(1)
        b = ds.rolling(win, min_periods=win).cov(lag) / lag.rolling(win, min_periods=win).var()
        hl = pd.Series(np.inf, index=s.index)
        neg = (b < 0) & (b > -1)
        hl[neg] = -math.log(2.0) / np.log1p(b[neg])
        hl[b.isna()] = np.nan
        return hl
    raise ValueError(f"bilinmeyen rejim: {rejim}")


def _pair_state(
    z: np.ndarray,
    h: np.ndarray,
    can_enter: np.ndarray,
    z_in: float,
    z_exit: float | None,
    z_stop: float | None,
    max_bar: int | None,
    allow_long: np.ndarray,
    allow_short: np.ndarray,
    teyit: bool,
    h_min: float,
    h_max: float,
    block_after_exit: bool = False,
) -> tuple[np.ndarray, np.ndarray]:
    """Çift durum makinesi → (A bacağı birimi, B bacağı birimi), her bar kapanışında hedef."""
    n = len(z)
    ua = np.zeros(n)
    ub = np.zeros(n)
    state = 0
    a_sz = b_sz = 0.0
    bars = 0
    blocked = False
    zs = z_stop if z_stop is not None else np.inf
    mb = max_bar if max_bar is not None else 10**12
    prev = np.nan
    for t in range(n):
        zt = z[t]
        if state != 0:
            bars += 1
            if not np.isnan(zt):
                if z_exit is not None and ((state == 1 and zt >= -z_exit) or (state == -1 and zt <= z_exit)):
                    state = 0
                    blocked = block_after_exit
                elif abs(zt) >= zs or bars >= mb:
                    state = 0
                    blocked = True
            elif bars >= mb:
                state = 0
                blocked = True
        else:
            if blocked and not np.isnan(zt) and abs(zt) < z_in:
                blocked = False
            if not blocked and can_enter[t] and not np.isnan(zt) and not np.isnan(h[t]):
                turned = (not teyit) or (not np.isnan(prev) and abs(zt) < abs(prev))
                go = 0
                if zt > z_in and allow_short[t] and turned and abs(zt) < zs:
                    go = -1
                elif zt < -z_in and allow_long[t] and turned and abs(zt) < zs:
                    go = 1
                if go:
                    state = go
                    bars = 0
                    hh = min(max(float(h[t]), h_min), h_max)
                    scale = max(1.0, hh)
                    a_sz, b_sz = 1.0 / scale, hh / scale
        prev = zt
        if state != 0:
            ua[t] = state * a_sz
            ub[t] = -state * b_sz
    return ua, ub


# ---------------------------------------------------------------- sinyal


def sinyal_cift(
    data: dict,
    funding: dict,
    ciftler=("ETHBTC",),
    hedge: str = "bir",
    hedge_win: int = 500,
    z_win: int = 200,
    z_tur: str = "duzey",
    k: int = 1,
    vol_win: int = 500,
    z_in: float = 2.0,
    z_exit: float | None = 0.0,
    z_stop: float | None = None,
    max_bar: int | None = None,
    rejim: str | None = None,
    rejim_win: int | None = None,
    rejim_esik: float | None = None,
    teyit: bool = False,
    h_min: float = 0.2,
    h_max: float = 5.0,
    limit_bps: float | None = None,
    limit_bar: int = 1,
    limit_mod: str = "giris",
) -> dict:
    close, real, bar_close = _panel(data)
    index = close.index
    logp = np.log(close)

    # Fonlama koruması: ilk fonlama kaydı bar kapanışından önce olmalı.
    funded = {}
    for sym in close.columns:
        f = funding.get(sym)
        if f is None or f.empty:
            funded[sym] = np.zeros(len(index), dtype=bool)
        else:
            funded[sym] = (bar_close >= f.index[0]).to_numpy()

    pairs = [PAIRS[p] if isinstance(p, str) else tuple(p) for p in ciftler]
    count: dict[str, int] = {}
    for a, b in pairs:
        count[a] = count.get(a, 0) + 1
        count[b] = count.get(b, 0) + 1
    m = max(count.values())

    units = {sym: np.zeros(len(index)) for sym in close.columns}
    for a, b in pairs:
        z, h, s = _spread_z(logp[a], logp[b], hedge, hedge_win, z_win, z_tur, k, vol_win)
        can = (real[a] & real[b]).to_numpy() & funded[a] & funded[b] & close[a].notna().to_numpy() & close[b].notna().to_numpy()
        allow_l = np.ones(len(index), dtype=bool)
        allow_s = np.ones(len(index), dtype=bool)
        reg = _regime(s, rejim, rejim_win)
        if reg is not None:
            r = reg.to_numpy()
            if rejim == "trend":
                allow_s = ~(r > rejim_esik)  # NaN → izin yok değil; NaN karşılaştırması False → izin var
                allow_l = ~(r < -rejim_esik)
                nan = np.isnan(r)
                allow_s &= ~nan
                allow_l &= ~nan
            else:  # yo
                ok = (r <= rejim_esik) & ~np.isnan(r)
                allow_s = ok.copy()
                allow_l = ok.copy()
        ua, ub = _pair_state(
            z.to_numpy(), h.to_numpy(), can, z_in, z_exit, z_stop, max_bar, allow_l, allow_s, teyit, h_min, h_max,
            block_after_exit=(z_tur == "sok"),
        )
        units[a] += ua
        units[b] += ub

    out = {}
    for leg, frame in data.items():
        sym = leg[1]
        tgt = pd.Series(np.clip(units.get(sym, np.zeros(len(index))) / m, -1.0, 1.0), index=index)
        if limit_bps is None:
            out[leg] = tgt.reindex(frame.index).fillna(0.0)
            continue
        out[leg] = _with_limit(tgt, close[sym], limit_bps, limit_bar, limit_mod).reindex(frame.index)
        out[leg]["target"] = out[leg]["target"].fillna(0.0)
    return out


def _with_limit(tgt: pd.Series, close: pd.Series, bps: float, bars: int, mode: str) -> pd.DataFrame:
    """Hedef değişiminden sonraki ilk `bars` bar için limit fiyatı (kapanış ∓ bps)."""
    t = tgt.to_numpy()
    c = close.to_numpy()
    n = len(t)
    lim = np.full(n, np.nan)
    last_change = -(10**9)
    direction = 0.0
    use = False
    prev = 0.0
    for i in range(n):
        if t[i] != prev:
            last_change = i
            direction = np.sign(t[i] - prev)
            if mode == "tum":
                use = True
            else:
                use = abs(t[i]) > abs(prev) or np.sign(t[i]) * np.sign(prev) < 0
            prev = t[i]
        if use and i - last_change < bars and direction != 0 and not np.isnan(c[i]):
            lim[i] = c[i] * (1.0 - direction * bps / 1e4)
    return pd.DataFrame({"target": tgt, "limit": lim}, index=tgt.index)


# ---------------------------------------------------------------- spec


def legs_for(ciftler) -> tuple:
    syms = []
    for p in ciftler:
        a, b = PAIRS[p] if isinstance(p, str) else tuple(p)
        for s in (a, b):
            if s not in syms:
                syms.append(s)
    order = [s for s in COINS if s in syms] + [s for s in syms if s not in COINS]
    return tuple((FUT, s) for s in order)


def make_spec(name: str, interval: str, description: str = "", **params) -> StrategySpec:
    if not name.startswith(FAMILY + "_"):
        name = f"{FAMILY}_{name}"
    ciftler = params.get("ciftler", ("ETHBTC",))
    params = dict(params)
    params["ciftler"] = list(ciftler)
    return StrategySpec(
        name=name,
        family=FAMILY,
        interval=interval,
        legs=legs_for(ciftler),
        signal_fn=sinyal_cift,
        params=params,
        description=description,
    )


def specs() -> list[StrategySpec]:
    """Dondurulmuş yapılandırmalar (iç doğrulamada bir kez ölçülenler)."""
    return []
