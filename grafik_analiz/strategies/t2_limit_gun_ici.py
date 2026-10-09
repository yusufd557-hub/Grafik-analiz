"""Limit emirli gün içi strateji ailesi (tur 2): `t2_limit_gun_ici`.

Tur 1'de taker maliyeti yüzünden ölen gün içi fikirler (ortalamaya dönüş,
açılış aralığı kırılımı, saat etkisi), protokol sürüm 2'nin limit emir
modeliyle yeniden sınanır (bkz. ``research.backtest._backtest_limit``):

- Strateji her bar için ``target`` (hedef pozisyon) ve ``limit`` (emir fiyatı)
  döndürür. ``limit`` doluysa pozisyon değişimi bir sonraki barda limit emirle
  denenir: emir açılışta piyasanın öbür tarafındaysa piyasa emri sayılır;
  değilse fiyat limitin 2 bps ötesine geçerse limit fiyattan, maker
  komisyonuyla dolar; dolmazsa bar sonunda iptal olur.
- Sinyal fonksiyonu, emrin dolup dolmadığını backtest'in kuralını birebir
  tekrarlayarak **o barın kapanışında** bilir (dolum barın düşüğü/yükseği ve
  açılışıyla belirlenir; bunlar barın kapanışında bilinir). Böylece durum
  makinesi gerçek pozisyonu izler: dolmayan emir yeniden verilebilir ya da
  bırakılabilir, dolan pozisyon için çıkış emri verilir.

Ortak motor (``_motor``), bar başına:

1. Önceki kapanışta verilen emir bu barda çözülür (backtest ile aynı kural).
2. Kapanışta karar:
   - Pozisyon varsa: tutulan bar sayısı ``H``'ye ulaştıysa ya da zorunlu çıkış
     (gün sonu, saat penceresi sonu) ya da stop varsa çıkış başlar. Çıkış
     ``cikis_bps`` verilmişse kapanışın o kadar lehine limitle, ``cikis_m``
     bar denenir, sonra piyasa emri; verilmemişse doğrudan piyasa emri. Hedef
     kâr (``tp_sig``/``tp_bps``) verilmişse giriş fiyatından o kadar lehteki
     limit emir her bar yeniden verilir.
   - Pozisyon yoksa: ham sinyal (yön) varsa giriş bölümü başlar. Giriş emri
     referans fiyatın ``d = d_bps/1e4 + d_sig·σ`` kadar lehine limit emirdir
     (alışta altında, satışta üstünde); ``giris="piyasa"`` ise piyasa emri.
     Emir ``m`` bar boyunca (dolana kadar) yeniden verilir. Referans: o barın
     kapanışı (``ref="kapanis"``) ya da sinyal barının kapanışı
     (``ref="sinyal"``); ORB'de kırılan seviye.

Yöntemler (``yontem``):

- ``fitil``: her bar, pozisyon yokken (ve filtre izin veriyorsa) kapanışın
  k·σ altına alış limiti (``yon="kisa"`` ise üstüne satış). Bekleyen derin
  limitle hızlı düşüş fitillerini yakalama. σ: son ``sig_n`` barın log
  getiri std'si (kapanışta bilinir).
- ``donus``: tur 1 ``ret`` ölçüsü: n barlık log getiri / (hareketten önceki
  ``vol_n`` barlık std × √n). Skor ≤ −eşik → alım, ≥ +eşik → açığa satış.
- ``orb``: günün (UTC) ilk ``or_saat`` saatinin aralığı; aralık bittikten
  sonra kapanış aralığın dışına ilk çıktığında kırılım yönünde giriş (gün
  başına yön başına bir kez); gün sonunda zorunlu çıkış.
- ``saat``: bir sonraki bar UTC ``bas_saat`` … ``bas_saat+sure_saat`` penceresi
  içindeyse pozisyon (giriş limitle, pencere bitince çıkış).

Filtreler: ``trend_gun`` (gün cinsinden SMA; ``trend_mod="ile"`` alım yalnız
kapanış SMA üstündeyken, açığa satış altındayken; ``"karsi"`` tersi),
``yon`` (``uzun`` / ``kisa`` / ``iki``).

Bütün hesaplar nedenseldir: kayan pencereler, ``shift(+k)``, baştan ileri
yürüyen durum makinesi; ``shift(-k)``, ortalanmış pencere ya da tam örneklem
istatistiği yoktur. Zorunlu çıkış ve saat penceresi bir sonraki barın
başlangıç zamanına bakar (takvim önceden bilinir).

``specs()`` yalnız dondurulup dev_valid'de bir kez değerlendirilen
yapılandırmaları döndürür (bkz. ``arastirma/tur2/t2_limit_gun_ici/RAPOR.md``).
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd

from grafik_analiz.research.evaluate import StrategySpec
from grafik_analiz.research.protocol import LIMIT_PENETRATION

FAMILY = "t2_limit_gun_ici"
COINS = ("BTCUSDT", "ETHUSDT", "SOLUSDT")
NAN = float("nan")


def legs_for(market: str = "futures", universe: str = "PORT3") -> tuple:
    if universe == "PORT3":
        return tuple((market, c) for c in COINS)
    return ((market, universe),)


def _bar_delta(index: pd.DatetimeIndex) -> pd.Timedelta:
    # Çubuk aralığı: ardışık iki zaman damgasının farklarının en küçüğü (sabit aralıklı veri).
    if len(index) < 2:
        return pd.Timedelta(minutes=5)
    k = min(len(index), 50)
    return pd.Timedelta((index[1:k] - index[: k - 1]).min())


# ---------------------------------------------------------------- motor


def _motor(
    o: np.ndarray,
    h: np.ndarray,
    lo: np.ndarray,
    c: np.ndarray,
    sig: np.ndarray,
    ref: np.ndarray,
    dist: np.ndarray,
    m: int,
    H: int,
    zorla: np.ndarray | None = None,
    tp: np.ndarray | None = None,
    sl: np.ndarray | None = None,
    cikis_bps: float | None = None,
    cikis_m: int = 1,
    ref_sabit: bool = False,
    kayit: bool = False,
):
    """Hedef ve limit dizilerini üretir; backtest dolum kuralını birebir izler.

    sig[i]: i kapanışında ham giriş sinyali (−1/0/+1). ref[i]: giriş limitinin
    referans fiyatı. dist[i]: referanstan lehe uzaklık (oran); NaN → piyasa emri.
    tp[i]/sl[i]: giriş barındaki hedef/stop uzaklığı (oran; NaN → yok).
    """
    n = len(c)
    pen = LIMIT_PENETRATION
    O = o.tolist()
    Hh = h.tolist()
    L = lo.tolist()
    C = c.tolist()
    S = sig.tolist()
    R = ref.tolist()
    D = dist.tolist()
    Z = zorla.tolist() if zorla is not None else None
    TP = tp.tolist() if tp is not None else None
    SL = sl.tolist() if sl is not None else None
    tgt = [0.0] * n
    lim = [NAN] * n
    isnan = math.isnan

    pos = 0
    held = 0
    entry_px = NAN
    tp_px = NAN
    sl_px = NAN
    ep_side = 0  # giriş bölümü: yön
    ep_left = 0  # kalan deneme
    ep_ref = NAN
    ep_bas = -1  # giriş bölümünün başladığı karar barı (tanı kaydı için)
    ep_dist = NAN
    ex_on = False  # çıkış bölümü
    ex_left = 0
    pend_t = 0.0
    pend_l = NAN
    orders = [] if kayit else None  # (bar, yön, limit, doldu, fiyat, piyasa, bölüm başı)
    exits = [] if kayit else None
    posv = [0] * n if kayit else None
    for i in range(n):
        # 1) önceki kapanışta verilen emir bu barda çözülür
        if i > 0:
            change = pend_t - pos
            if change != 0.0:
                lp = pend_l
                if isnan(lp) or (change > 0 and lp >= O[i]) or (change < 0 and lp <= O[i]):
                    filled, px, mkt = True, O[i], True
                else:
                    filled = (L[i] < lp * (1.0 - pen)) if change > 0 else (Hh[i] > lp * (1.0 + pen))
                    px, mkt = lp, False
                if kayit and pos == 0:
                    orders.append((i, int(pend_t), lp, filled, px, mkt, ep_bas))
                if filled:
                    if pos == 0:
                        pos = int(pend_t)
                        held = 0
                        entry_px = px
                        ex_on = False
                        ep_side = 0
                        tp_px = NAN
                        sl_px = NAN
                        if TP is not None and not isnan(TP[i - 1]):
                            tp_px = px * (1.0 + pos * TP[i - 1])
                        if SL is not None and not isnan(SL[i - 1]):
                            sl_px = px * (1.0 - pos * SL[i - 1])
                    else:
                        if kayit:
                            exits.append((i, pos, entry_px, px, mkt))
                        pos = int(pend_t)
                        ex_on = False
                        if pos != 0:  # yön değişimi (kullanılmaz ama tutarlılık için)
                            held = 0
                            entry_px = px
        if kayit:
            posv[i] = pos
        # 2) kapanışta karar
        t = 0.0
        lp = NAN
        if pos != 0:
            held += 1
            if not ex_on:
                stop = False
                if not isnan(sl_px):
                    stop = (C[i] <= sl_px) if pos > 0 else (C[i] >= sl_px)
                if stop:
                    t, lp = 0.0, NAN
                    pend_t, pend_l = t, lp
                    tgt[i], lim[i] = t, lp
                    continue
                if held >= H or (Z is not None and Z[i]):
                    if cikis_bps is None:
                        tgt[i], lim[i] = 0.0, NAN
                        pend_t, pend_l = 0.0, NAN
                        continue
                    ex_on = True
                    ex_left = cikis_m
            if ex_on:
                if ex_left > 0:
                    ex_left -= 1
                    t, lp = 0.0, C[i] * (1.0 + pos * cikis_bps / 1e4)
                else:
                    t, lp = 0.0, NAN
            elif not isnan(tp_px):
                t, lp = 0.0, tp_px
            else:
                t, lp = float(pos), NAN
        elif Z is not None and Z[i]:
            ep_side = 0  # zorunlu çıkış barında (gün/pencere sonu) bekleyen giriş iptal
        else:
            s = S[i]
            if s != 0 and not isnan(R[i]):
                if not (ref_sabit and ep_side == s and ep_left > 0):
                    ep_side, ep_left, ep_ref, ep_dist = s, m, R[i], D[i]
                    ep_bas = i
            if ep_side != 0 and ep_left > 0:
                r = R[i] if not ref_sabit else ep_ref
                d = D[i] if not ref_sabit else ep_dist
                if isnan(r):
                    r = C[i]
                t = float(ep_side)
                lp = NAN if isnan(d) else r * (1.0 - ep_side * d)
                ep_left -= 1
                if ep_left == 0:
                    ep_side = 0
        tgt[i], lim[i] = t, lp
        pend_t, pend_l = t, lp
    out = (np.asarray(tgt), np.asarray(lim))
    if kayit:
        return out + (orders, exits, np.asarray(posv))
    return out


# ---------------------------------------------------------------- yöntemler


def _sigma(close: pd.Series, n: int) -> pd.Series:
    lr = np.log(close).diff()
    return lr.rolling(n, min_periods=n).std()


def _yon_maskesi(df: pd.DataFrame, bars_per_day: float, yon: str, trend_gun: float, trend_mod: str):
    close = df["close"].astype(float)
    n = len(df)
    long_ok = np.ones(n, dtype=bool)
    short_ok = np.ones(n, dtype=bool)
    if yon == "uzun":
        short_ok[:] = False
    elif yon == "kisa":
        long_ok[:] = False
    elif yon != "iki":
        raise ValueError(f"bilinmeyen yön: {yon}")
    if trend_gun and trend_mod != "yok":
        tn = max(2, int(round(trend_gun * bars_per_day)))
        ma = close.rolling(tn, min_periods=tn).mean()
        known = ma.notna().to_numpy()
        up = (close > ma).to_numpy() & known
        dn = (close < ma).to_numpy() & known
        if trend_mod == "ile":
            long_ok &= up
            short_ok &= dn
        elif trend_mod == "karsi":
            long_ok &= dn
            short_ok &= up
        else:
            raise ValueError(f"bilinmeyen trend modu: {trend_mod}")
    return long_ok, short_ok


def _dist(sigma: np.ndarray, d_bps: float, d_sig: float, giris: str) -> np.ndarray:
    if giris == "piyasa":
        return np.full(len(sigma), np.nan)
    if d_sig == 0.0:
        return np.full(len(sigma), d_bps / 1e4)
    return d_bps / 1e4 + d_sig * sigma


def leg_plan(df: pd.DataFrame, p: dict) -> dict:
    """Bir bacak için motor girdileri (yönteme göre)."""
    yontem = p.get("yontem", "fitil")
    close = df["close"].astype(float)
    c = close.to_numpy()
    n = len(df)
    delta = _bar_delta(df.index)
    bars_per_day = pd.Timedelta(days=1) / delta
    sig_n = int(p.get("sig_n", 288))
    sigma = _sigma(close, sig_n).to_numpy()
    long_ok, short_ok = _yon_maskesi(df, bars_per_day, p.get("yon", "uzun"), float(p.get("trend_gun", 0)), p.get("trend_mod", "yok"))
    giris = p.get("giris", "limit")
    d_bps = float(p.get("d_bps", 0.0))
    d_sig = float(p.get("d_sig", 0.0))
    sig = np.zeros(n)
    ref = c.copy()
    zorla = None
    m = int(p.get("m", 1))
    ref_sabit = p.get("ref", "kapanis") == "sinyal"

    if yontem == "fitil":
        k = float(p["k"])
        ok_s = np.isfinite(sigma)
        sig = np.where(long_ok & ok_s, 1.0, np.where(short_ok & ok_s, -1.0, 0.0))
        if p.get("yon", "uzun") == "iki" and p.get("trend_mod", "yok") == "yok":
            # Tek emir hakkı: son barın yönünün tersine (düşen barın ardından alış).
            last = np.sign(np.diff(c, prepend=c[0]))
            sig = np.where(ok_s, np.where(last <= 0, 1.0, -1.0), 0.0)
        dist = d_bps / 1e4 + k * sigma
        m = 1
    elif yontem == "donus":
        nn = int(p.get("n", 4))
        vol_n = int(p.get("vol_n", 500))
        lr = np.log(close).diff()
        move = np.log(close / close.shift(nn))
        sd = lr.rolling(vol_n, min_periods=vol_n).std().shift(nn)
        score = (move / (sd * math.sqrt(nn)).replace(0.0, np.nan)).to_numpy()
        e = float(p["esik"])
        sc = np.nan_to_num(score, nan=0.0)
        sig = np.where((sc <= -e) & long_ok, 1.0, np.where((sc >= e) & short_ok, -1.0, 0.0))
        dist = _dist(sigma, d_bps, d_sig, giris)
    elif yontem == "orb":
        or_saat = float(p.get("or_saat", 1.0))
        idx = df.index
        day = idx.floor("1D")
        mins = ((idx - day) / pd.Timedelta(minutes=1)).to_numpy()
        in_or = mins < or_saat * 60
        frame = pd.DataFrame({"h": df["high"].astype(float).where(in_or), "l": df["low"].astype(float).where(in_or), "d": day})
        rh = frame.groupby("d")["h"].cummax().to_numpy()
        rl = frame.groupby("d")["l"].cummin().to_numpy()
        # Aralık yalnız aralık bittikten sonra (aralığın son barı kapandıktan sonra) kullanılır.
        rh = pd.Series(rh).groupby(day.to_numpy()).ffill().to_numpy()
        rl = pd.Series(rl).groupby(day.to_numpy()).ffill().to_numpy()
        after = mins >= or_saat * 60
        nxt_day = (idx + delta).floor("1D")
        last_bar = (nxt_day != day)
        son_giris_saat = float(p.get("son_giris_saat", 20.0))
        can_enter = after & (mins < son_giris_saat * 60) & ~last_bar
        up = (c > rh) & can_enter
        dn = (c < rl) & can_enter
        # Gün içinde yön başına ilk kırılım.
        up_first = up & (pd.Series(up.astype(int)).groupby(day.to_numpy()).cumsum().to_numpy() == 1)
        dn_first = dn & (pd.Series(dn.astype(int)).groupby(day.to_numpy()).cumsum().to_numpy() == 1)
        # Tersine dönüş modu: kırılımın tersine (başarısız kırılım).
        if p.get("orb_mod", "kirilim") == "ters":
            up_first, dn_first = dn_first, up_first
        sig = np.where(up_first & long_ok, 1.0, np.where(dn_first & short_ok, -1.0, 0.0))
        if giris == "seviye":
            # Kırılan seviyeye geri çekilmede limit (alışta aralık üstü, satışta aralık altı).
            lvl = np.where(c > rh, rh, np.where(c < rl, rl, c))
            if p.get("orb_mod", "kirilim") == "ters":
                lvl = c
            ref = lvl
            dist = _dist(sigma, d_bps, d_sig, "limit")
        else:
            dist = _dist(sigma, d_bps, d_sig, giris)
        ref_sabit = True
        zorla = last_bar
    elif yontem == "saat":
        bas = int(p["bas_saat"])
        sure = int(p["sure_saat"])
        nb = df.index + delta
        hr = nb.hour.to_numpy()
        in_w = ((hr - bas) % 24) < sure
        if p.get("hafta_ici", False):
            in_w &= nb.dayofweek.to_numpy() < 5
        side = 1.0 if p.get("yon", "uzun") == "uzun" else -1.0
        sig = np.where(in_w, side, 0.0)
        dist = _dist(sigma, d_bps, d_sig, giris)
        zorla = ~in_w
        m = 1
    else:
        raise ValueError(f"bilinmeyen yöntem: {yontem}")

    tp_bps = p.get("tp_bps")
    tp_sig = p.get("tp_sig")
    tp = None
    if tp_bps is not None or tp_sig is not None:
        tp = (float(tp_bps or 0.0) / 1e4) + float(tp_sig or 0.0) * np.nan_to_num(sigma, nan=0.0)
    sl = None
    if p.get("sl_sig") is not None:
        sl = float(p["sl_sig"]) * np.where(np.isfinite(sigma), sigma, np.nan)
    H = int(p.get("H", 12))
    if zorla is not None and "H" not in p:
        H = 10**9
    return dict(
        o=df["open"].to_numpy(dtype=float),
        h=df["high"].to_numpy(dtype=float),
        lo=df["low"].to_numpy(dtype=float),
        c=c,
        sig=sig.astype(float),
        ref=np.asarray(ref, dtype=float),
        dist=np.asarray(dist, dtype=float),
        m=m,
        H=H,
        zorla=None if zorla is None else np.asarray(zorla, dtype=bool),
        tp=tp,
        sl=sl,
        cikis_bps=None if p.get("cikis_bps") is None else float(p["cikis_bps"]),
        cikis_m=int(p.get("cikis_m", 1)),
        ref_sabit=ref_sabit,
    )


def leg_signal(df: pd.DataFrame, p: dict) -> pd.DataFrame:
    plan = leg_plan(df, p)
    tgt, lim = _motor(**plan)
    return pd.DataFrame({"target": tgt, "limit": lim}, index=df.index)


def leg_orders(df: pd.DataFrame, p: dict):
    """Tanılama: hedef/limit dizileri ile giriş emirleri ve çıkışların listesi."""
    plan = leg_plan(df, p)
    return _motor(**plan, kayit=True)


def sinyal(data: dict, funding: dict, **params) -> dict:
    return {leg: leg_signal(df, params) for leg, df in data.items()}


def make_spec(name: str, interval: str, market: str = "futures", universe: str = "PORT3", description: str = "", **params) -> StrategySpec:
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


_T50 = dict(trend_gun=50, trend_mod="ile")

FROZEN: tuple = (
    # (ad, aralık, parametreler, açıklama)
    (
        "fitil_1h_k4_H3_t50",
        "1h",
        dict(yontem="fitil", k=4, H=3, sig_n=168, **_T50),
        "Fitil yakalama 1h: kapanış 50 günlük SMA üstündeyken her saat kapanışın 4σ (σ: son 168 saatin "
        "log getiri std'si) altına alış limiti; dolarsa 3 saat tut, piyasa emriyle çık. Vadeli BTC/ETH/SOL. "
        "candidate_check: GEÇMEDİ (dev_valid 1× %+2,76, 2× %−1,97, Sharpe 0,30, alfa %+1,7).",
    ),
    (
        "fitil_5m_k8_H24_t50",
        "5m",
        dict(yontem="fitil", k=8, H=24, sig_n=288, **_T50),
        "Fitil yakalama 5m: kapanış 50 günlük SMA üstündeyken her 5 dakikada kapanışın 8σ (σ: son 288 barın "
        "log getiri std'si) altına alış limiti; dolarsa 2 saat tut, piyasa emriyle çık. Vadeli BTC/ETH/SOL. "
        "candidate_check: GEÇMEDİ (dev_valid 1× %−5,89, Sharpe −0,46, alfa %−3,3).",
    ),
    (
        "donus_1h_n4_e3_t50_H12_lim1.0s_m3",
        "1h",
        dict(yontem="donus", n=4, esik=3, vol_n=500, yon="uzun", trend_gun=50, trend_mod="ile", H=12, sig_n=168,
             giris="limit", d_sig=1.0, m=3),
        "Yükselen trendde dip alımı, limit giriş: 4 saatlik getiri ≤ −3σ ve kapanış 50 günlük SMA üstünde "
        "ise kapanışın 1σ altına alış limiti (3 saat denenir); 12 saat tut, piyasa emriyle çık. Vadeli BTC/ETH/SOL. "
        "candidate_check: GEÇTİ (dev_valid 1× %+7,18, 2× %+5,74, Sharpe 0,81, 45 işlem, alfa %+4,1, t 1,06).",
    ),
    (
        "donus_15m_n16_e3_t50_H48_lim1.0s_m12",
        "15m",
        dict(yontem="donus", n=16, esik=3, vol_n=2000, yon="uzun", trend_gun=50, trend_mod="ile", H=48, sig_n=96,
             giris="limit", d_sig=1.0, m=12),
        "Yükselen trendde dip alımı, 15m, limit giriş: 4 saatlik getiri ≤ −3σ ve trend yukarı ise kapanışın "
        "1σ (15m) altına alış limiti (3 saat denenir); 12 saat tut, piyasa emriyle çık. Vadeli BTC/ETH/SOL. "
        "candidate_check: GEÇMEDİ (dev_valid 1× %−5,05, Sharpe −0,54, alfa %−2,9).",
    ),
    (
        "donus_1h_n4_e3_t50_H12_piyasa",
        "1h",
        dict(yontem="donus", n=4, esik=3, vol_n=500, yon="uzun", trend_gun=50, trend_mod="ile", H=12, sig_n=168,
             giris="piyasa"),
        "KONTROL: 3 numaralı kuralın piyasa emirli sürümü (limit etkisini ölçmek için). Vadeli BTC/ETH/SOL. "
        "candidate_check: GEÇMEDİ (dev_valid 1× %−1,74, Sharpe −0,18, alfa %−0,9).",
    ),
)
"""Dondurulan yapılandırmalar (bkz. arastirma/tur2/t2_limit_gun_ici/NOTLAR.md, bölüm 4)."""


def specs() -> list[StrategySpec]:
    return [make_spec(name, interval, description=desc, **params) for name, interval, params, desc in FROZEN]
