"""Meta-etiketleme ailesi, araştırma turu 2 ("t2_meta").

López de Prado'nun meta-etiketleme düzeni, BTC/ETH/SOL sürekli vadeli
sözleşmelerinde (1h / 4h):

1. **Birincil olay** kuralla üretilir ve işlemin yönünü verir
   (``birincil``):

   - ``kanal``: Donchian kırılımı. Kapanış önceki ``n`` barın en yükseğini
     ilk kez geçince uzun, en düşüğünün altına ilk kez inince kısa.
   - ``donus``: büyük hareket sonrası dönüş. ``k`` barlık log getirinin,
     hareketten önceki oynaklığa göre z-skoru ``z`` eşiğini ilk kez aşınca
     ters yönde.
   - ``fonlama``: son fonlama kaydının 90 kayıtlık z-skoru ``fz`` eşiğini ilk
     kez aşınca karşıt yönde.
   - ``ema``: ``hizli``/``yavas`` EMA kesişimi, kesişim yönünde.
   - Birden çok birincil ``+`` ile birleştirilebilir (ör. ``kanal+donus``);
     model "birincil türü" özelliğini de görür.

2. Her olayın **kendi işlemi** ileriye doğru izlenen sabit bir çıkış
   kuralıyla tanımlanır (``cikis``):

   - ``bariyer``: olay barının kapanışından ``tp`` × ATR lehte ya da ``sl`` ×
     ATR aleyhte kapanış, ya da en fazla ``H`` bar (``tp=0`` ise kâr al yok).
   - ``iz``: olaydan bu yana en uç kapanıştan ``iz_k`` × ATR geri çekilen
     kapanış, ya da en fazla ``H`` bar.

   ATR olay barındaki ATR(14)'tür. Kararlar bar kapanışında, işlem sonraki
   açılışta (harness ile aynı). Çıkış koşulu yalnız o bara kadarki kapanışlara
   bakar.

3. **Etiket** = olay işleminin net getirisi > 0:
   ``yön × (open[e+1] / open[t+1] − 1) − 2 × 0,0007 − yön × Σ fonlama``
   (fonlama zamanı ``(open[t+1], open[e+1]]`` aralığında). Etiketin bilindiği
   an ``open[e+1]`` barının açılış zamanıdır.

4. **İkincil model** (isteğe bağlı örnek ağırlığı ``agirlik="getiri"``: |net getiri|)
   ileriye yürüyerek eğitilir: her ``yeniden`` ayda bir ay
   başında (T), etiketi T'den **önce** bilinen olaylarla (arındırma), üç coin
   havuzlanarak. [T, sonraki eğitim) aralığındaki olaylar için kazanma
   olasılığı tahmin edilir. Modeller: ``hgb`` (HistGradientBoosting
   sınıflandırıcı), ``logit`` (medyan doldurma + ölçekleme + lojistik
   regresyon; dönüştürücüler yalnız eğitim satırlarına uydurulur), ``hepsi``
   (model yok, aynı takvimle bütün olaylar alınır; karşılaştırma için).

5. **Karar** (``kural``): ``taban``: p > eğitim taban oranı + ``delta``;
   ``mutlak``: p > ``esik``; ``ev``: p × ort. kazanç − (1 − p) × ort. kayıp >
   ``delta`` (ortalamalar eğitim etiketlerinden, getiri birimi).
   Boyut (``boyut``): ``ikili`` (1) ya da ``ev`` (beklenen değerin eğitimdeki
   ortalama kazanca oranı, 0…1).

**Topluluk** (``topluluk``, ör. ``"n=14,20,30,48;cikis=iz,bariyer"``): alt
yapılandırmaların (kartezyen çarpım) her biri ayrı model ve pozisyonla
hesaplanır; bacak pozisyonu bunların ortalamasıdır (−1…1).

Pozisyon coin başına sıralıdır: kabul edilen olay, kendi çıkışına kadar
yön × boyut pozisyon açar; yeni kabul edilen olay eskisinin yerini alır.
Bacak başına 1/3 sermaye; bacak pozisyonu −1…1 (kaldıraç yok). İlk model
eğitilmeden önce pozisyon yoktur. Coinin ilk fonlama kaydından önce olay
üretilmez.

Özellikler (olay barında, yalnız o bara kadarki veriyle; ``d_`` önekliler
olay yönüyle çarpılır):

- Oynaklık rejimi, trend (getiri z-skorları, EMA uzaklıkları, Donchian
  konumu), hacim ve işlem sayısı, taker alım payı, zaman (kapanış saati,
  gün), BTC bağlamı.
- Fonlama: yalnız zaman damgası ≤ bar **açılışı** olan kayıtlar (tur 1 ML ile
  aynı ihtiyat; ``assert_causal`` fonlamayı açılışta keser).
- Konumlanma (``ozellik="tam"``): ``load_metrics(scope="dev")`` ile yüklenir,
  verilen son barın kapanışına kadar **açıkça kesilir**; t barında zaman
  damgası ≤ kapanış − 10 dk olan son kayıt (2 saatten eskiyse yok sayılır).
  OI = 0 kayıtları NaN.
- Prim endeksi (``ozellik="tam"``): ``load_premium(scope="dev")``, son barın
  kapanışına kadar açıkça kesilir; barla aynı açılış zamanlı prim mumunun
  kapanışı.

Bütün normalizasyonlar geriye dönük kayan pencerelerledir; ``shift(-k)``,
ortalanmış pencere, tam örneklem istatistiği kullanılmaz. Olay işleminin
çıkış barı ileriye doğru bulunur ama yalnız etiket için (eğitimde etiketin
bilindiği andan sonra) ve pozisyonun o barda kapanması için kullanılır; çıkış
koşulu o bara kadarki veriyle kontrol edilebilir olduğundan nedenseldir.

`specs()` yalnız dondurulup iç doğrulamada (dev_valid) bir kez ölçülen
yapılandırmaları döndürür (bkz. ``arastirma/tur2/t2_meta/RAPOR.md``).
"""

from __future__ import annotations

import hashlib
import math

import numpy as np
import pandas as pd

from grafik_analiz.indicators import atr as atr_fn
from grafik_analiz.indicators import ema
from grafik_analiz.research.evaluate import StrategySpec

FAMILY = "t2_meta"

COINS = ("BTCUSDT", "ETHUSDT", "SOLUSDT")

PER_SIDE = 0.0007
"""Vadeli piyasa emri, 1× maliyet (0,05 % komisyon + 0,02 % kayma), taraf başına. Yalnız etiket için."""

METRIC_LAG = pd.Timedelta(minutes=10)
METRIC_MAX_AGE = pd.Timedelta(hours=2)
METRIC_COLS = ("oi", "genel_oran", "top_hesap_oran", "top_pozisyon_oran")

DEFAULTS: dict = {
    "birincil": "kanal",
    "n": 48,
    "k": 12,
    "z": 3.0,
    "fz": 2.0,
    "hizli": 20,
    "yavas": 100,
    "cikis": "bariyer",
    "tp": 3.0,
    "sl": 1.5,
    "H": 48,
    "iz_k": 3.0,
    "yon": "iki",
    "model": "hgb",
    "ozellik": "tam",
    "yeniden": 1,
    "min_olay": 300,
    "pencere_gun": 0,
    "kural": "taban",
    "delta": 0.0,
    "esik": 0.5,
    "boyut": "ikili",
    "hgb_iter": 100,
    "hgb_lr": 0.05,
    "hgb_yaprak": 8,
    "hgb_min_yaprak": 40,
    "hgb_l2": 1.0,
    "C": 0.1,
    "agirlik": "yok",
    "topluluk": "",
}

_PRIMARY_CODES = {"kanal": 0, "donus": 1, "fonlama": 2, "ema": 3}


def legs() -> tuple:
    return tuple(("futures", c) for c in COINS)


# ---------------------------------------------------------------- yardımcılar


def _ns(index) -> np.ndarray:
    return pd.DatetimeIndex(index).as_unit("ns").asi8


def _step(frame: pd.DataFrame) -> pd.Timedelta:
    diff = (pd.to_datetime(frame["close_time"], utc=True) - frame.index).median()
    return pd.Timedelta(diff).ceil("min")


def _frame_key(df: pd.DataFrame) -> tuple:
    if df.empty:
        return (0,)
    return (
        len(df),
        int(_ns(df.index[:1])[0]),
        int(_ns(df.index[-1:])[0]),
        float(df["close"].sum()),
        float(df["volume"].sum()),
    )


_FEAT_CACHE: dict = {}
_PRED_CACHE: dict = {}
_CACHE_MAX = 24
_PRED_CACHE_MAX = 64


def _cache_put(cache: dict, key, value) -> None:
    limit = _PRED_CACHE_MAX if cache is _PRED_CACHE else _CACHE_MAX
    if len(cache) >= limit:
        cache.pop(next(iter(cache)))
    cache[key] = value


def _z(x: pd.Series, window: int) -> pd.Series:
    roll = x.rolling(window, min_periods=max(10, window // 2))
    return (x - roll.mean()) / roll.std().replace(0.0, np.nan)


# ---------------------------------------------------------------- ek veriler


def bar_metrics(symbol: str, index: pd.DatetimeIndex, step: pd.Timedelta) -> pd.DataFrame:
    """Her bar için kapanıştan en az ``METRIC_LAG`` önceki son konumlanma kaydı."""
    from grafik_analiz.research.data import load_metrics

    out = pd.DataFrame(np.nan, index=index, columns=list(METRIC_COLS))
    if len(index) == 0:
        return out
    try:
        raw = load_metrics(symbol, scope="dev")
    except FileNotFoundError:
        return out
    # Açık kesme: verilen mumların son barının kapanışından sonraki kayıtlar atılır.
    raw = raw[raw.index < index[-1] + step]
    cutoff = _ns(index + step - METRIC_LAG)
    for col in METRIC_COLS:
        s = raw[col].astype(float)
        s = s.where(s > 0).dropna()
        if s.empty:
            continue
        times = _ns(s.index)
        pos = np.searchsorted(times, cutoff, side="right") - 1
        safe = np.clip(pos, 0, None)
        ok = (pos >= 0) & ((cutoff - times[safe]) <= METRIC_MAX_AGE.value)
        out[col] = np.where(ok, s.to_numpy()[safe], np.nan)
    return out


def bar_premium(symbol: str, index: pd.DatetimeIndex, step: pd.Timedelta) -> pd.Series:
    """Barla aynı açılış zamanlı prim endeksi mumunun kapanışı."""
    from grafik_analiz.research.data import load_premium

    if len(index) == 0:
        return pd.Series(np.nan, index=index)
    iv = "1h" if step == pd.Timedelta(hours=1) else "4h"
    try:
        raw = load_premium(symbol, iv, scope="dev")
    except FileNotFoundError:
        return pd.Series(np.nan, index=index)
    # Açık kesme: son barın kapanışından sonra kapanan prim mumu kullanılmaz.
    raw = raw[pd.to_datetime(raw["close_time"], utc=True) < index[-1] + step]
    return raw["close"].astype(float).reindex(index)


def funding_on_bars(index: pd.DatetimeIndex, fund: pd.DataFrame | None) -> pd.DataFrame:
    """Zaman damgası ≤ bar açılışı olan son fonlama kaydı ve onun kayıt bazlı istatistikleri."""
    cols = ["fon_son", "fon_ort3", "fon_z"]
    if fund is None or fund.empty or len(index) == 0:
        return pd.DataFrame(np.nan, index=index, columns=cols)
    fr = fund["funding_rate"].astype(float).sort_index()
    rec = pd.DataFrame(
        {
            "fon_son": fr * 1e4,
            "fon_ort3": fr.rolling(3, min_periods=1).mean() * 1e4,
            "fon_z": (fr - fr.rolling(90, min_periods=20).mean()) / fr.rolling(90, min_periods=20).std().replace(0.0, np.nan),
        }
    )
    idx = np.searchsorted(_ns(rec.index), _ns(index), side="right") - 1
    vals = rec.to_numpy(dtype=float)
    out = np.full((len(index), len(cols)), np.nan)
    ok = idx >= 0
    out[ok] = vals[idx[ok]]
    return pd.DataFrame(out, index=index, columns=cols)


# ---------------------------------------------------------------- özellikler

FIYAT_COLS = [
    "vol_sl", "vol_ll", "vol_sira", "atr_pct", "aralik", "hacim_z", "hacim_z200", "islem_z",
    "saat_sin", "saat_cos", "gun",
    "d_r1", "d_r4", "d_r24", "d_r96", "d_ema20", "d_ema50", "d_ema200", "d_dc", "d_taker", "d_taker8", "d_btc24",
]
FON_COLS = ["fon_son", "fon_z", "d_fon"]
POZ_COLS = ["oi_d1", "oi_d6", "oi_d24", "oi_z", "genel_log", "genel_d24", "d_genel", "top_hesap_log", "top_poz_log", "prem", "prem_z", "d_prem"]
TEMEL_COLS = ["vol_sira", "vol_sl", "d_r24", "d_ema50", "hacim_z", "d_taker8", "d_fon", "fon_z", "oi_d24", "d_genel", "d_prem"]


def bar_features(
    df: pd.DataFrame, fund: pd.DataFrame | None, symbol: str, btc: pd.DataFrame | None, with_extra: bool
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Bar başına özellikler (``d_`` önekliler sonra olay yönüyle çarpılır) ve bar hizalı fonlama."""
    key = ("feat", symbol, _frame_key(df), _frame_key(btc) if btc is not None else None, with_extra,
           len(fund) if fund is not None else 0)
    if key in _FEAT_CACHE:
        return _FEAT_CACHE[key]
    index = df.index
    step = _step(df)
    bpd = max(1, int(round(pd.Timedelta(days=1) / step)))
    c = df["close"].astype(float)
    h = df["high"].astype(float)
    lo = df["low"].astype(float)
    v = df["volume"].astype(float)
    logc = np.log(c)
    lr = logc.diff()
    sig12 = lr.rolling(12, min_periods=12).std()
    sig48 = lr.rolling(48, min_periods=48).std()
    sig240 = lr.rolling(240, min_periods=120).std()
    a = atr_fn(df, 14)
    f: dict[str, pd.Series] = {}
    f["vol_sl"] = np.log(sig12 / sig48)
    f["vol_ll"] = np.log(sig48 / sig240)
    f["vol_sira"] = sig48.rolling(30 * bpd, min_periods=10 * bpd).rank(pct=True)
    f["atr_pct"] = a / c
    f["aralik"] = (h - lo) / a
    lv = np.log(v.replace(0.0, np.nan))
    f["hacim_z"] = lv - lv.rolling(50, min_periods=25).mean()
    f["hacim_z200"] = lv - lv.rolling(200, min_periods=100).mean()
    lt = np.log(df["trades"].astype(float).replace(0.0, np.nan))
    f["islem_z"] = lt - lt.rolling(50, min_periods=25).mean()
    close_t = index + step
    hour = close_t.hour + close_t.minute / 60.0
    f["saat_sin"] = pd.Series(np.sin(2 * np.pi * hour / 24.0), index=index)
    f["saat_cos"] = pd.Series(np.cos(2 * np.pi * hour / 24.0), index=index)
    f["gun"] = pd.Series(close_t.dayofweek.astype(float), index=index)
    for k in (1, 4, 24, 96):
        f[f"d_r{k}"] = (logc - logc.shift(k)) / (sig48 * math.sqrt(k))
    for n in (20, 50, 200):
        f[f"d_ema{n}"] = (c - ema(c, n)) / a
    hi = h.rolling(100, min_periods=100).max()
    lw = lo.rolling(100, min_periods=100).min()
    f["d_dc"] = (c - lw) / (hi - lw).replace(0.0, np.nan) - 0.5
    tb = df["taker_buy_base"].astype(float) / v.replace(0.0, np.nan) - 0.5
    f["d_taker"] = tb
    f["d_taker8"] = tb.rolling(8, min_periods=8).mean()
    if btc is not None and len(btc):
        bc = np.log(btc["close"].astype(float).reindex(index))
        bs = bc.diff().rolling(48, min_periods=48).std()
        f["d_btc24"] = (bc - bc.shift(24)) / (bs * math.sqrt(24))
    else:
        f["d_btc24"] = pd.Series(np.nan, index=index)
    fon = funding_on_bars(index, fund)
    f["fon_son"] = fon["fon_son"]
    f["fon_z"] = fon["fon_z"]
    f["d_fon"] = fon["fon_son"]
    if with_extra:
        met = bar_metrics(symbol, index, step)
        loi = np.log(met["oi"])
        f["oi_d1"] = loi - loi.shift(1)
        f["oi_d6"] = loi - loi.shift(6)
        f["oi_d24"] = loi - loi.shift(24)
        f["oi_z"] = _z(loi, 30 * bpd)
        lg = np.log(met["genel_oran"])
        f["genel_log"] = lg
        f["genel_d24"] = lg - lg.shift(24)
        f["d_genel"] = _z(lg, 30 * bpd)
        f["top_hesap_log"] = np.log(met["top_hesap_oran"])
        f["top_poz_log"] = np.log(met["top_pozisyon_oran"])
        pr = bar_premium(symbol, index, step) * 1e4
        f["prem"] = pr
        f["prem_z"] = _z(pr, 7 * bpd)
        f["d_prem"] = pr
    out = (pd.DataFrame(f, index=index).replace([np.inf, -np.inf], np.nan), fon)
    _cache_put(_FEAT_CACHE, key, out)
    return out


def feature_columns(ozellik: str) -> list[str]:
    if ozellik == "fiyat":
        return FIYAT_COLS + ["fon_son", "fon_z", "d_fon"]
    if ozellik == "tam":
        return FIYAT_COLS + FON_COLS + POZ_COLS
    if ozellik == "temel":
        return list(TEMEL_COLS)
    raise ValueError(f"bilinmeyen özellik kümesi: {ozellik}")


# ---------------------------------------------------------------- birincil olaylar


def _first(cond: pd.Series) -> np.ndarray:
    c = cond.fillna(False).astype(bool)
    return (c & ~c.shift(1, fill_value=False)).to_numpy()


def primary_events(df: pd.DataFrame, fon: pd.DataFrame, kind: str, p: dict) -> tuple[np.ndarray, np.ndarray]:
    """Olay yönü (+1/−1/0) ve olay gücü (yön-göreli büyüklük)."""
    c = df["close"].astype(float)
    a = atr_fn(df, 14)
    n_bars = len(df)
    if kind == "kanal":
        n = int(p["n"])
        up = df["high"].astype(float).shift(1).rolling(n, min_periods=n).max()
        dn = df["low"].astype(float).shift(1).rolling(n, min_periods=n).min()
        lf = _first(c > up)
        sf = _first(c < dn)
        d = np.where(lf, 1.0, np.where(sf, -1.0, 0.0))
        g = np.where(lf, ((c - up) / a).to_numpy(), np.where(sf, ((dn - c) / a).to_numpy(), np.nan))
    elif kind == "donus":
        k = int(p["k"])
        logc = np.log(c)
        sig = logc.diff().rolling(48, min_periods=48).std().shift(k)
        zz = (logc - logc.shift(k)) / (sig * math.sqrt(k))
        thr = float(p["z"])
        uf = _first(zz > thr)
        df_ = _first(zz < -thr)
        d = np.where(uf, -1.0, np.where(df_, 1.0, 0.0))
        g = np.abs(zz.to_numpy())
    elif kind == "fonlama":
        fz = fon["fon_z"]
        thr = float(p["fz"])
        uf = _first(fz > thr)
        df_ = _first(fz < -thr)
        d = np.where(uf, -1.0, np.where(df_, 1.0, 0.0))
        g = np.abs(fz.to_numpy())
    elif kind == "ema":
        ef = ema(c, int(p["hizli"]))
        es = ema(c, int(p["yavas"]))
        diff = ef - es
        sgn = np.sign(diff)
        prev = sgn.shift(1)
        cross = (sgn != prev) & sgn.notna() & prev.notna() & (sgn != 0)
        d = np.where(cross.to_numpy(), sgn.to_numpy(), 0.0)
        g = np.abs((diff / a).to_numpy())
    else:
        raise ValueError(f"bilinmeyen birincil: {kind}")
    d = np.nan_to_num(d, nan=0.0)
    yon = p.get("yon", "iki")
    if yon == "uzun":
        d = np.where(d > 0, d, 0.0)
    elif yon == "kisa":
        d = np.where(d < 0, d, 0.0)
    assert len(d) == n_bars
    return d, g


def event_exits(df: pd.DataFrame, bars: np.ndarray, dirs: np.ndarray, p: dict) -> np.ndarray:
    """Her olayın çıkış barı (kapanışında çıkış kararı); veri içinde bulunamazsa n."""
    c = df["close"].to_numpy(dtype=float)
    a = atr_fn(df, 14).to_numpy(dtype=float)
    n = len(c)
    H = int(p["H"])
    mode = p["cikis"]
    tp = float(p["tp"])
    sl = float(p["sl"])
    izk = float(p["iz_k"])
    out = np.full(len(bars), n, dtype=np.int64)
    for j, (t, d) in enumerate(zip(bars, dirs)):
        A = a[t]
        if not np.isfinite(A) or A <= 0:
            out[j] = min(t + H, n) if t + H < n else n
            continue
        ref = c[t]
        last = min(t + H, n - 1)
        ext = ref
        e = n
        for i in range(t + 1, last + 1):
            ci = c[i]
            if mode == "bariyer":
                m = d * (ci - ref) / A
                if (tp > 0 and m >= tp) or m <= -sl:
                    e = i
                    break
            else:
                if d > 0:
                    ext = ci if ci > ext else ext
                    if ci < ext - izk * A:
                        e = i
                        break
                else:
                    ext = ci if ci < ext else ext
                    if ci > ext + izk * A:
                        e = i
                        break
            if i == t + H:
                e = i
                break
        out[j] = e
    return out


def event_labels(df: pd.DataFrame, fund: pd.DataFrame | None, bars: np.ndarray, dirs: np.ndarray, exits: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Olay işleminin net getirisi ve bilindiği an (ns). Bilinmiyorsa NaN / int64 max."""
    o = df["open"].to_numpy(dtype=float)
    n = len(o)
    idx_ns = _ns(df.index)
    net = np.full(len(bars), np.nan)
    known = np.full(len(bars), np.iinfo(np.int64).max, dtype=np.int64)
    if fund is not None and not fund.empty:
        f_ns = _ns(fund.index)
        f_cum = np.concatenate([[0.0], np.cumsum(fund["funding_rate"].to_numpy(dtype=float))])
    else:
        f_ns = np.array([], dtype=np.int64)
        f_cum = np.array([0.0])
    for j, (t, d, e) in enumerate(zip(bars, dirs, exits)):
        if e + 1 >= n or t + 1 >= n:
            continue
        a_ns, b_ns = idx_ns[t + 1], idx_ns[e + 1]
        # Fonlama zamanı (a, b] aralığında olan kayıtlar işlem süresince ödenir/alınır.
        lo = np.searchsorted(f_ns, a_ns, side="right")
        hi = np.searchsorted(f_ns, b_ns, side="right")
        fsum = f_cum[hi] - f_cum[lo]
        net[j] = d * (o[e + 1] / o[t + 1] - 1.0) - 2.0 * PER_SIDE - d * fsum
        known[j] = b_ns
    return net, known


# ---------------------------------------------------------------- olay tablosu ve ileriye yürüyen model


def _event_table(data: dict, funding: dict, p: dict) -> pd.DataFrame:
    with_extra = p["ozellik"] in ("tam", "temel")
    btc = data.get(("futures", "BTCUSDT"))
    kinds = str(p["birincil"]).split("+")
    rows = []
    for li, leg in enumerate(data):
        df = data[leg]
        if len(df) < 300:
            continue
        sym = leg[1]
        fund = funding.get(sym)
        feats, fon = bar_features(df, fund, sym, btc, with_extra)
        first_f = fund.index.min() if fund is not None and not fund.empty else None
        allowed = np.ones(len(df), dtype=bool) if first_f is not None else np.zeros(len(df), dtype=bool)
        if first_f is not None:
            allowed &= df.index >= first_f
        for kind in kinds:
            d, g = primary_events(df, fon, kind, p)
            bars = np.flatnonzero((d != 0) & allowed)
            if len(bars) == 0:
                continue
            dirs = d[bars]
            exits = event_exits(df, bars, dirs, p)
            net, known = event_labels(df, fund, bars, dirs, exits)
            part = feats.iloc[bars].copy()
            dcols = [col for col in part.columns if col.startswith("d_")]
            part[dcols] = part[dcols].to_numpy() * dirs[:, None]
            part["guc"] = g[bars]
            part["yon"] = dirs
            part["tur"] = float(_PRIMARY_CODES[kind])
            part["_leg"] = li
            part["_bar"] = bars
            part["_exit"] = exits
            part["_net"] = net
            part["_known"] = known
            part["_ts"] = _ns(df.index[bars])
            rows.append(part.reset_index(drop=True))
    if not rows:
        return pd.DataFrame()
    return pd.concat(rows, ignore_index=True).sort_values(["_ts", "_leg"], kind="mergesort").reset_index(drop=True)


def _make_model(p: dict):
    if p["model"] == "hgb":
        from sklearn.ensemble import HistGradientBoostingClassifier

        return HistGradientBoostingClassifier(
            max_iter=int(p["hgb_iter"]),
            learning_rate=float(p["hgb_lr"]),
            max_leaf_nodes=int(p["hgb_yaprak"]),
            min_samples_leaf=int(p["hgb_min_yaprak"]),
            l2_regularization=float(p["hgb_l2"]),
            early_stopping=False,
            random_state=0,
        )
    if p["model"] == "logit":
        from sklearn.impute import SimpleImputer
        from sklearn.linear_model import LogisticRegression
        from sklearn.pipeline import make_pipeline
        from sklearn.preprocessing import FunctionTransformer, StandardScaler

        return make_pipeline(
            SimpleImputer(strategy="median", keep_empty_features=True),
            StandardScaler(),
            FunctionTransformer(_clip5),
            LogisticRegression(C=float(p["C"]), max_iter=2000),
        )
    raise ValueError(f"bilinmeyen model: {p['model']}")


def _clip5(x):
    return np.clip(x, -5.0, 5.0)


def _month_starts(first: pd.Timestamp, last: pd.Timestamp, step: int) -> list[pd.Timestamp]:
    t = pd.Timestamp(year=first.year, month=first.month, day=1, tz="UTC") + pd.offsets.MonthBegin(1)
    out = []
    while t <= last:
        out.append(t)
        t = t + pd.offsets.MonthBegin(step)
    return out


def _fingerprint(data: dict, funding: dict) -> str:
    hsh = hashlib.sha1()
    for leg in data:
        df = data[leg]
        hsh.update(repr(leg).encode())
        hsh.update(repr(_frame_key(df)).encode())
    for sym in sorted(funding):
        f = funding[sym]
        hsh.update(sym.encode())
        hsh.update(str(len(f)).encode())
        if len(f):
            hsh.update(str(int(_ns(f.index[-1:])[0])).encode())
            hsh.update(str(float(f["funding_rate"].sum())).encode())
    return hsh.hexdigest()


_PRED_KEYS = (
    "birincil", "n", "k", "z", "fz", "hizli", "yavas", "cikis", "tp", "sl", "H", "iz_k", "yon",
    "model", "ozellik", "yeniden", "min_olay", "pencere_gun",
    "hgb_iter", "hgb_lr", "hgb_yaprak", "hgb_min_yaprak", "hgb_l2", "C", "agirlik",
)


def predictions(data: dict, funding: dict, p: dict) -> pd.DataFrame:
    """Olay tablosu + ileriye yürüyen olasılık (``_p``), taban oranı ve eğitim kazanç/kayıp ortalamaları."""
    key = (_fingerprint(data, funding), tuple((k, p[k]) for k in _PRED_KEYS))
    if key in _PRED_CACHE:
        return _PRED_CACHE[key]
    ev = _event_table(data, funding, p)
    if ev.empty:
        _cache_put(_PRED_CACHE, key, ev)
        return ev
    cols = feature_columns(p["ozellik"]) + ["guc", "yon"]
    if "+" in str(p["birincil"]):
        cols = cols + ["tur"]
    X = ev[cols].to_numpy(dtype=float)
    ts = ev["_ts"].to_numpy()
    known = ev["_known"].to_numpy()
    net = ev["_net"].to_numpy(dtype=float)
    y = (net > 0).astype(int)
    prob = np.full(len(ev), np.nan)
    base = np.full(len(ev), np.nan)
    win = np.full(len(ev), np.nan)
    loss = np.full(len(ev), np.nan)
    starts = _month_starts(pd.Timestamp(int(ts.min()), tz="UTC"), pd.Timestamp(int(ts.max()), tz="UTC"), int(p["yeniden"]))
    win_ns = int(pd.Timedelta(days=int(p["pencere_gun"])).value) if int(p["pencere_gun"]) > 0 else None
    for i, T in enumerate(starts):
        a_ns = T.value
        b_ns = starts[i + 1].value if i + 1 < len(starts) else np.iinfo(np.int64).max
        pm = (ts >= a_ns) & (ts < b_ns)
        if not pm.any():
            continue
        tr = known < a_ns
        if win_ns is not None:
            tr &= ts >= a_ns - win_ns
        if tr.sum() < int(p["min_olay"]):
            continue
        ytr = y[tr]
        ntr = net[tr]
        base[pm] = ytr.mean()
        win[pm] = ntr[ntr > 0].mean() if (ntr > 0).any() else 0.0
        loss[pm] = -ntr[ntr <= 0].mean() if (ntr <= 0).any() else 0.0
        if p["model"] == "hepsi":
            prob[pm] = 1.0
            continue
        if len(np.unique(ytr)) < 2:
            continue
        # Eğitim satırlarında en az iki farklı değeri olmayan sütunlar (ör. verinin
        # henüz başlamadığı konumlanma ölçüleri) o eğitimde kullanılmaz.
        Xtr = X[tr]
        use = np.array([np.unique(col[np.isfinite(col)]).size >= 2 for col in Xtr.T])
        if not use.any():
            continue
        model = _make_model(p)
        if p["agirlik"] == "getiri":
            # Örnek ağırlığı: işlemin net getirisinin büyüklüğü (eğitim ortalamasına göre).
            w = np.abs(ntr)
            w = w / w.mean() if w.mean() > 0 else np.ones_like(w)
            if p["model"] == "logit":
                model.fit(Xtr[:, use], ytr, logisticregression__sample_weight=w)
            else:
                model.fit(Xtr[:, use], ytr, sample_weight=w)
        elif p["agirlik"] == "yok":
            model.fit(Xtr[:, use], ytr)
        else:
            raise ValueError(f"bilinmeyen ağırlık: {p['agirlik']}")
        prob[pm] = model.predict_proba(X[pm][:, use])[:, 1]
    ev = ev.copy()
    ev["_p"] = prob
    ev["_base"] = base
    ev["_win"] = win
    ev["_loss"] = loss
    _cache_put(_PRED_CACHE, key, ev)
    return ev


def decisions(ev: pd.DataFrame, p: dict) -> tuple[np.ndarray, np.ndarray]:
    """Kabul bayrağı ve boyut."""
    prob = ev["_p"].to_numpy(dtype=float)
    base = ev["_base"].to_numpy(dtype=float)
    win = ev["_win"].to_numpy(dtype=float)
    loss = ev["_loss"].to_numpy(dtype=float)
    ok = np.isfinite(prob)
    evv = prob * win - (1.0 - prob) * loss
    if p["model"] == "hepsi":
        acc = ok.copy()
    elif p["kural"] == "taban":
        acc = ok & (prob > base + float(p["delta"]))
    elif p["kural"] == "mutlak":
        acc = ok & (prob > float(p["esik"]))
    elif p["kural"] == "ev":
        acc = ok & (evv > float(p["delta"]))
    else:
        raise ValueError(f"bilinmeyen kural: {p['kural']}")
    size = np.ones(len(ev))
    if p["boyut"] == "ev" and p["model"] != "hepsi":
        with np.errstate(invalid="ignore", divide="ignore"):
            size = np.clip(evv / np.where(win > 0, win, np.nan), 0.0, 1.0)
        size = np.nan_to_num(size, nan=0.0)
        acc &= size > 0
    elif p["boyut"] != "ikili" and p["model"] != "hepsi":
        raise ValueError(f"bilinmeyen boyut: {p['boyut']}")
    return acc, size


def positions(n: int, bars: np.ndarray, dirs: np.ndarray, exits: np.ndarray, acc: np.ndarray, size: np.ndarray, prob: np.ndarray) -> np.ndarray:
    """Sıralı pozisyon: kabul edilen olay kendi çıkışına kadar; yeni kabul edilen olay eskisinin yerini alır."""
    pos = np.zeros(n)
    take = np.flatnonzero(acc)
    by_bar: dict[int, int] = {}
    for j in take:
        b = int(bars[j])
        # Aynı barda birden çok kabul edilen olay: olasılığı en yüksek olan.
        if b not in by_bar or (np.nan_to_num(prob[j]) > np.nan_to_num(prob[by_bar[b]])):
            by_bar[b] = j
    cur = 0.0
    cur_exit = -1
    for i in range(n):
        if cur != 0.0 and i >= cur_exit:
            cur = 0.0
        j = by_bar.get(i)
        if j is not None:
            cur = float(dirs[j]) * float(size[j])
            cur_exit = int(exits[j])
        pos[i] = cur
    return pos


def _single(data: dict, funding: dict, p: dict) -> dict:
    ev = predictions(data, funding, p)
    out = {}
    for li, leg in enumerate(data):
        df = data[leg]
        if ev.empty:
            out[leg] = pd.Series(0.0, index=df.index)
            continue
        sub = ev[ev["_leg"] == li]
        if sub.empty:
            out[leg] = pd.Series(0.0, index=df.index)
            continue
        acc, size = decisions(sub, p)
        pos = positions(
            len(df),
            sub["_bar"].to_numpy(),
            sub["yon"].to_numpy(dtype=float),
            sub["_exit"].to_numpy(),
            acc,
            size,
            sub["_p"].to_numpy(dtype=float),
        )
        out[leg] = pd.Series(pos, index=df.index)
    return out


def _parse_value(text: str):
    for cast in (int, float):
        try:
            return cast(text)
        except ValueError:
            pass
    return text


def expand_ensemble(p: dict) -> list[dict]:
    """``topluluk="n=14,20;cikis=iz,bariyer"`` → alt yapılandırmaların kartezyen çarpımı."""
    spec = str(p.get("topluluk") or "").strip()
    if not spec:
        return [p]
    subs = [dict(p, topluluk="")]
    for part in spec.split(";"):
        key, values = part.split("=")
        key = key.strip()
        if key not in DEFAULTS:
            raise ValueError(f"bilinmeyen topluluk parametresi: {key}")
        vals = [_parse_value(v.strip()) for v in values.split(",")]
        subs = [dict(q, **{key: v}) for q in subs for v in vals]
    return subs


def sinyal(data: dict, funding: dict, **params) -> dict:
    """Hedef pozisyon. ``topluluk`` doluysa alt yapılandırmaların pozisyonlarının ortalaması."""
    p = {**DEFAULTS, **params}
    subs = expand_ensemble(p)
    if len(subs) == 1:
        return _single(data, funding, subs[0])
    total = {leg: pd.Series(0.0, index=df.index) for leg, df in data.items()}
    for q in subs:
        one = _single(data, funding, q)
        for leg in data:
            total[leg] = total[leg] + one[leg]
    return {leg: s / len(subs) for leg, s in total.items()}


def make_spec(name: str, interval: str, description: str = "", **params) -> StrategySpec:
    p = {**DEFAULTS, **params}
    return StrategySpec(
        name=name,
        family=FAMILY,
        interval=interval,
        legs=legs(),
        signal_fn=sinyal,
        params=p,
        description=description,
    )


# ---------------------------------------------------------------- dondurulmuş yapılandırmalar

_LOGIT = {"model": "logit", "ozellik": "tam"}

FROZEN: tuple = (
    (
        "t2_meta_4h_kanal_n20_b3.0-1.5-H60_logit_tam_taban0.0",
        "4h",
        {"birincil": "kanal", "n": 20, "cikis": "bariyer", "tp": 3.0, "sl": 1.5, "H": 60, **_LOGIT},
        "4h vadeli BTC/ETH/SOL, iki yön. Birincil: Donchian(20) kırılımı. Olay işlemi: 3 ATR kâr al / "
        "1,5 ATR zarar kes / en fazla 60 bar (kapanışla). Meta model: aylık ileriye yürüyen lojistik "
        "regresyon (fiyat, oynaklık, hacim, fonlama, konumlanma, prim özellikleri); olasılık eğitim taban "
        "oranını geçerse işlem alınır.",
    ),
    (
        "t2_meta_4h_kanal_top[n14-20-30-48]_n48_b3.0-1.5-H60_logit_tam_taban0.0",
        "4h",
        {"birincil": "kanal", "topluluk": "n=14,20,30,48", "cikis": "bariyer", "tp": 3.0, "sl": 1.5, "H": 60, **_LOGIT},
        "4h vadeli BTC/ETH/SOL, iki yön. Dört Donchian uzunluğunun (14, 20, 30, 48) her biri için ayrı "
        "meta-etiketlenmiş strateji (1 numaralı yapılandırmayla aynı çıkış ve model); bacak pozisyonu "
        "dördünün ortalaması.",
    ),
    (
        "t2_meta_1h_kanal_n96_iz4.0-H240_logit_tam_taban0.0",
        "1h",
        {"birincil": "kanal", "n": 96, "cikis": "iz", "iz_k": 4.0, "H": 240, **_LOGIT},
        "1h vadeli BTC/ETH/SOL, iki yön. Birincil: Donchian(96) kırılımı. Olay işlemi: en uç kapanıştan "
        "4 ATR iz süren stop / en fazla 240 bar. Meta model: aylık ileriye yürüyen lojistik regresyon "
        "(tam özellik); olasılık eğitim taban oranını geçerse işlem.",
    ),
    (
        "t2_meta_1h_kanal_n96_iz3.0-H120_logit_tam_taban0.0",
        "1h",
        {"birincil": "kanal", "n": 96, "cikis": "iz", "iz_k": 3.0, "H": 120, **_LOGIT},
        "1h vadeli BTC/ETH/SOL, iki yön. Birincil: Donchian(96) kırılımı. Olay işlemi: 3 ATR iz süren "
        "stop / en fazla 120 bar. Meta model: aylık ileriye yürüyen lojistik regresyon (tam özellik).",
    ),
    (
        "t2_meta_4h_ema_e20-100_b3.0-1.5-H60_logit_tam_taban0.0_min_olay150",
        "4h",
        {"birincil": "ema", "hizli": 20, "yavas": 100, "cikis": "bariyer", "tp": 3.0, "sl": 1.5, "H": 60, "min_olay": 150, **_LOGIT},
        "4h vadeli BTC/ETH/SOL, iki yön. Birincil: EMA(20)/EMA(100) kesişimi. Olay işlemi: 3 ATR kâr al / "
        "1,5 ATR zarar kes / en fazla 60 bar. Meta model: lojistik regresyon, ilk eğitim 150 etiketli olaydan "
        "sonra.",
    ),
)
"""Dev_train'de seçilip dondurulan yapılandırmalar (bkz. arastirma/tur2/t2_meta/NOTLAR.md, bölüm 5)."""

FROZEN_CHECK: dict = {
    "t2_meta_4h_kanal_n20_b3.0-1.5-H60_logit_tam_taban0.0": (
        "GEÇMEDİ (dev_valid 1× %−1,38, 2× %−11,30, Sharpe 0,10 < 0,5; alfa +0,025, t 0,12; 227 işlem)"
    ),
    "t2_meta_4h_kanal_top[n14-20-30-48]_n48_b3.0-1.5-H60_logit_tam_taban0.0": (
        "GEÇMEDİ (dev_valid 1× %+3,14, 2× %−6,34, Sharpe 0,19 < 0,5; alfa +0,043, t 0,24; 283 işlem)"
    ),
    "t2_meta_1h_kanal_n96_iz4.0-H240_logit_tam_taban0.0": (
        "GEÇMEDİ (dev_valid 1× %−7,14, 2× %−17,01, Sharpe 0,03 < 0,5; alfa +0,007, t 0,03; 241 işlem)"
    ),
    "t2_meta_1h_kanal_n96_iz3.0-H120_logit_tam_taban0.0": (
        "GEÇTİ, zayıf (dev_valid 1× %+25,72, 2× %+8,53, Sharpe 0,59; alfa +0,172, beta 0,011, alfa t 0,78; "
        "315 işlem; DSR 0,08; kazanç 2025'te, 2026'nın ilk 9 ayı %−7,8)"
    ),
    "t2_meta_4h_ema_e20-100_b3.0-1.5-H60_logit_tam_taban0.0_min_olay150": (
        "GEÇMEDİ (dev_valid 1× %+6,64, 2× %+2,50, Sharpe 0,35 < 0,5; alfa +0,047, t 0,47; 85 işlem)"
    ),
}
"""dev_valid tek seferlik değerlendirmesinin candidate_check sonucu (yalnız açıklama metni;
parametreleri ve sinyali etkilemez)."""


def specs() -> list[StrategySpec]:
    """Dondurulup dev_valid'de bir kez değerlendirilen yapılandırmalar."""
    out = []
    for name, interval, params, desc in FROZEN:
        durum = FROZEN_CHECK.get(name)
        if durum is not None:
            desc = f"{desc} candidate_check: {durum}."
        out.append(make_spec(name, interval, description=desc, **params))
    return out
