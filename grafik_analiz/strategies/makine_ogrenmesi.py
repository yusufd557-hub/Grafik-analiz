"""Makine öğrenmesi ailesi ("makine_ogrenmesi").

Bütün modeller ``signal_fn`` içinde **ileriye yürüyerek** eğitilir:

- Yeniden eğitim takvim ayı başlarında yapılır (her ``yeniden`` ayda bir).
  O tarihten sonraki barlar için tahmin, yalnızca **etiketi o tarihten önce
  tamamen bilinen** satırlarla eğitilmiş modelden gelir (arındırma: t satırının
  etiketi ``open[t+1+H]`` fiyatını kullanır; bu barın açılış zamanı eğitim
  tarihinden önce olmalıdır).
- İlk tahmin, verinin başından en az ``min_gun`` gün sonra ve en az
  ``min_satir`` eğitim satırı varsa yapılır.
- Eğitim penceresi genişleyen (``pencere_gun=0``) ya da son ``pencere_gun``
  gündür.
- Aynı spec'teki coinlerin satırları tek modelde birlikte eğitilir (havuz);
  özellikler ölçekten bağımsızdır.

Özellikler yalnızca t ve önceki barları kullanır (geriye dönük pencereler,
``shift(+k)``, baştan başlayan EWM). Fonlama kaydı yalnızca kayıt zamanı barın
açılış zamanından küçük ya da eşitse kullanılır (ihtiyatlı). Tam örneklem
normalleştirmesi, ``shift(-k)``, ortalanmış pencere yoktur; ölçekleyiciler
yalnız eğitim satırlarına uydurulur.

Hedef: ``H`` bar ileri getiri ``open[t+1+H] / open[t+1] - 1`` (stratejinin
t barındaki kararla yakalayacağı getiri). Sınıflandırıcılar işaretini,
regresör oynaklığa bölünmüş (σ_t·√H) ve ±4'te kırpılmış değerini öğrenir.

Kenar tahmini: regresörde ``ŷ·σ_t·√H``; sınıflandırıcıda
``(2p−1)·√(2/π)·σ_t·√H``. Kenar, ``k`` × gidiş-dönüş maliyetini aşarsa alım,
``−k`` × maliyetin altındaysa (vadeli, iki yönde) açığa satış, yoksa nakit.
``esleme="ortusen"``: pozisyon son ``H`` kararın ortalamasıdır (H tane
örtüşen alt portföy); ``esleme="esik"``: her bar yeniden karar.

Vadelide coinin ilk fonlama kaydından önce pozisyon 0'dır.

Tahminler, aynı girdi verisi ve aynı model parametreleri için süreç içinde
önbelleğe alınır (yalnız eşleme parametreleri değişen yapılandırmalar için
yeniden eğitim gerekmez). Önbellek anahtarı verinin parmak izini içerir;
kısaltılmış veri (``assert_causal``) her zaman yeniden hesaplanır.

`specs()` yalnızca dondurulup dev_valid'de bir kez değerlendirilen
yapılandırmaları döndürür (bkz. `arastirma/makine_ogrenmesi/RAPOR.md`).
"""

from __future__ import annotations

import hashlib
import math

import numpy as np
import pandas as pd

from grafik_analiz.indicators import adx, atr, bollinger, cci, ema, macd, mfi, rsi, stochastic
from grafik_analiz.patterns.candles import SPECS as CANDLE_SPECS
from grafik_analiz.patterns.candles import detect_candles
from grafik_analiz.research.evaluate import StrategySpec
from grafik_analiz.research.protocol import COSTS

FAMILY = "makine_ogrenmesi"

COINS = ("BTCUSDT", "ETHUSDT", "SOLUSDT")

RT_COST = {m: 2.0 * c.per_side for m, c in COSTS.items()}
"""Gidiş-dönüş maliyeti (1×): spot 0,0024, vadeli 0,0014."""

DEFAULTS: dict = {
    "model": "logit",
    "H": 12,
    "k": 1.0,
    "esleme": "ortusen",
    "yon": "iki",
    "pencere_gun": 0,
    "min_gun": 365,
    "min_satir": 500,
    "yeniden": 1,
    "ozellik": "temel",
    "adim": 0,
    "C": 0.05,
    "hgb_iter": 150,
    "hgb_lr": 0.05,
    "hgb_yaprak": 15,
    "hgb_min_yaprak": 200,
    "hgb_l2": 1.0,
    "egitim": "kendi",
}
"""``egitim="spot"`` (yalnız vadeli spec'lerde): model aynı coinlerin spot satırlarıyla
eğitilir (spot geçmişi 2017'ye uzanır), tahmin vadeli satırlar için yapılır. Spot
bacaklar spec'e sıfır ağırlıkla eklenir ve pozisyonları her zaman 0'dır."""


def legs_for(market: str, universe: str) -> tuple:
    if universe == "PORT3":
        return tuple((market, c) for c in COINS)
    if universe == "PORT2":
        return tuple((market, c) for c in COINS[:2])
    return ((market, universe),)


# ---------------------------------------------------------------- özellikler

RET_LAGS = (1, 2, 4, 8, 16, 32, 64, 128)


def _bar_delta(index: pd.DatetimeIndex) -> pd.Timedelta:
    if len(index) < 2:
        return pd.Timedelta(days=1)
    return pd.Series(index[1:] - index[:-1]).median()


def _sigma(close: pd.Series, n: int = 48) -> pd.Series:
    lr = np.log(close).diff()
    return lr.rolling(n, min_periods=n).std()


def base_features(df: pd.DataFrame) -> pd.DataFrame:
    """Ölçekten bağımsız, nedensel temel özellikler."""
    c = df["close"].astype(float)
    h = df["high"].astype(float)
    lo = df["low"].astype(float)
    o = df["open"].astype(float)
    v = df["volume"].astype(float)
    logc = np.log(c)
    sig = _sigma(c, 48)
    f: dict[str, pd.Series] = {}
    for k in RET_LAGS:
        f[f"z{k}"] = (logc - logc.shift(k)) / (sig * math.sqrt(k))
    sig_s = _sigma(c, 12)
    sig_l = _sigma(c, 192)
    f["vol_oran_s"] = np.log(sig_s / sig)
    f["vol_oran_l"] = np.log(sig / sig_l)
    f["vol_sira"] = sig.rolling(500, min_periods=200).rank(pct=True)
    a = atr(df, 14)
    for n in (20, 50, 200):
        f[f"ema{n}"] = (c - ema(c, n)) / a
    f["rsi"] = (rsi(c, 14) - 50.0) / 50.0
    f["stoch"] = stochastic(df)["stoch_k"] / 100.0 - 0.5
    bb = bollinger(c, 20, 2.0)
    f["bb_pos"] = bb["bb_pos"] - 0.5
    f["bb_gen_sira"] = bb["bb_width"].rolling(500, min_periods=200).rank(pct=True)
    ad = adx(df, 14)
    f["adx"] = ad["adx"] / 100.0
    f["di_fark"] = (ad["plus_di"] - ad["minus_di"]) / (ad["plus_di"] + ad["minus_di"]).replace(0.0, np.nan)
    f["macd_h"] = macd(c)["macd_hist"] / a
    f["cci"] = cci(df, 20) / 100.0
    f["mfi"] = (mfi(df, 14) - 50.0) / 50.0
    for n in (20, 100):
        hi = h.rolling(n, min_periods=n).max()
        lw = lo.rolling(n, min_periods=n).min()
        f[f"dc{n}"] = (c - lw) / (hi - lw).replace(0.0, np.nan) - 0.5
    f["tepe_dusus"] = np.log(c / c.rolling(500, min_periods=100).max())
    lv = np.log(v.replace(0.0, np.nan))
    f["hacim20"] = lv - lv.rolling(20, min_periods=20).mean()
    f["hacim200"] = lv - lv.rolling(200, min_periods=100).mean()
    tb = (df["taker_buy_base"].astype(float) / v.replace(0.0, np.nan)) - 0.5
    f["alici"] = tb
    f["alici8"] = tb.rolling(8, min_periods=8).mean()
    f["alici32"] = tb.rolling(32, min_periods=32).mean()
    lt = np.log(df["trades"].astype(float).replace(0.0, np.nan))
    f["islem20"] = lt - lt.rolling(20, min_periods=20).mean()
    rng = (h - lo).replace(0.0, np.nan)
    f["aralik"] = (h - lo) / a
    f["kapanis_yeri"] = (c - lo) / rng - 0.5
    f["govde"] = (c - o) / a
    f["ust_fitil"] = (h - np.maximum(o, c)) / rng
    f["alt_fitil"] = (np.minimum(o, c) - lo) / rng
    out = pd.DataFrame(f, index=df.index)
    return out.replace([np.inf, -np.inf], np.nan)


def candle_features(df: pd.DataFrame) -> pd.DataFrame:
    flags = detect_candles(df)
    bias = pd.Series(0.0, index=df.index)
    for spec in CANDLE_SPECS:
        bias = bias + spec.bias * flags[spec.key].astype(float)
    bull = sum(flags[s.key].astype(float) for s in CANDLE_SPECS if s.bias > 0)
    bear = sum(flags[s.key].astype(float) for s in CANDLE_SPECS if s.bias < 0)
    return pd.DataFrame(
        {
            "mum_net": bias,
            "mum_net5": bias.rolling(5, min_periods=1).sum(),
            "mum_boga5": bull.rolling(5, min_periods=1).sum(),
            "mum_ayi5": bear.rolling(5, min_periods=1).sum(),
        },
        index=df.index,
    )


def funding_features(df: pd.DataFrame, fund: pd.DataFrame | None) -> pd.DataFrame:
    """Kayıt zamanı ≤ bar açılış zamanı olan son fonlama kayıtları."""
    cols = ["fon_son", "fon_ort3", "fon_ort21", "fon_z90"]
    if fund is None or fund.empty:
        return pd.DataFrame(np.nan, index=df.index, columns=cols)
    fr = fund["funding_rate"].astype(float).sort_index()
    rec = pd.DataFrame(
        {
            "fon_son": fr,
            "fon_ort3": fr.rolling(3, min_periods=1).mean(),
            "fon_ort21": fr.rolling(21, min_periods=1).mean(),
            "fon_z90": (fr - fr.rolling(90, min_periods=10).mean()) / fr.rolling(90, min_periods=10).std(),
        }
    )
    rec = rec * np.array([1e4, 1e4, 1e4, 1.0])
    rec_ns = _ns(rec.index)
    # İhtiyatlı: yalnız barın AÇILIŞ zamanına kadar kaydedilmiş fonlama kullanılır
    # (1h/4h barlarda kapanışa kadar olanla aynıdır; 1d barda gün içi kayıtlar ertesi
    # güne kalır). `assert_causal` fonlamayı kesim barının açılışında kestiği için de
    # bu seçim gerekir.
    open_ns = _ns(df.index)
    idx = np.searchsorted(rec_ns, open_ns, side="right") - 1
    vals = rec.to_numpy(dtype=float)
    out = np.full((len(df), len(cols)), np.nan)
    ok = idx >= 0
    out[ok] = vals[idx[ok]]
    return pd.DataFrame(out, index=df.index, columns=cols)


def _ns(index) -> np.ndarray:
    """Zaman damgalarını birimden bağımsız olarak nanosaniye tamsayıya çevirir."""
    return pd.DatetimeIndex(index).as_unit("ns").asi8


def _first_funding_time(fund: pd.DataFrame | None):
    if fund is None or fund.empty:
        return None
    return fund.index.min()


def leg_features(df: pd.DataFrame, ozellik: str, fund: pd.DataFrame | None, btc: pd.DataFrame | None) -> pd.DataFrame:
    parts = [base_features(df)]
    if "mum" in ozellik:
        parts.append(candle_features(df))
    if "fon" in ozellik:
        parts.append(funding_features(df, fund))
    if "btc" in ozellik and btc is not None:
        bc = btc["close"].astype(float).reindex(df.index)
        lb = np.log(bc)
        sb = _sigma(bc, 48)
        cross = {f"btc_z{k}": (lb - lb.shift(k)) / (sb * math.sqrt(k)) for k in (4, 16, 64)}
        parts.append(pd.DataFrame(cross, index=df.index))
    return pd.concat(parts, axis=1)


# ---------------------------------------------------------------- etiket


def labels(df: pd.DataFrame, H: int) -> tuple[pd.Series, pd.Series, pd.Series]:
    """İleri getiri, etiketin bilindiği zaman (t+1+H barının açılış zamanı) ve σ_t."""
    op = df["open"].astype(float)
    fwd = op.shift(-(1 + H)) / op.shift(-1) - 1.0
    ts = pd.Series(df.index, index=df.index)
    known = ts.shift(-(1 + H))
    sig = _sigma(df["close"].astype(float), 48)
    return fwd, known, sig


# ---------------------------------------------------------------- modeller


def _make_model(p: dict):
    model = p["model"]
    if model == "logit":
        from sklearn.linear_model import LogisticRegression
        from sklearn.pipeline import make_pipeline
        from sklearn.preprocessing import FunctionTransformer, StandardScaler

        return make_pipeline(
            StandardScaler(),
            FunctionTransformer(lambda x: np.clip(x, -5.0, 5.0)),
            LogisticRegression(C=p["C"], max_iter=1000),
        )
    if model in ("hgb_clf", "hgb_reg"):
        from sklearn.ensemble import HistGradientBoostingClassifier, HistGradientBoostingRegressor

        kw = dict(
            max_iter=int(p["hgb_iter"]),
            learning_rate=float(p["hgb_lr"]),
            max_leaf_nodes=int(p["hgb_yaprak"]),
            min_samples_leaf=int(p["hgb_min_yaprak"]),
            l2_regularization=float(p["hgb_l2"]),
            early_stopping=False,
            random_state=0,
        )
        if model == "hgb_clf":
            return HistGradientBoostingClassifier(**kw)
        return HistGradientBoostingRegressor(**kw)
    raise ValueError(f"bilinmeyen model: {model}")


def _is_classifier(model: str) -> bool:
    return model in ("logit", "hgb_clf")


def _month_starts(first: pd.Timestamp, last: pd.Timestamp, step: int) -> list[pd.Timestamp]:
    start = pd.Timestamp(year=first.year, month=first.month, day=1, tz="UTC")
    if start < first:
        start = start + pd.offsets.MonthBegin(1)
    out = []
    t = start
    while t <= last:
        out.append(t)
        t = t + pd.offsets.MonthBegin(step)
    return out


def walk_forward_edges(data: dict, funding: dict, p: dict) -> dict:
    """Her bacak için kenar tahmini serisi (tahmin yoksa NaN)."""
    legs = list(data)
    H = int(p["H"])
    btc = {leg[0]: data[leg] for leg in legs if leg[1] == "BTCUSDT"}
    frames = []
    for li, leg in enumerate(legs):
        df = data[leg]
        if df.empty:
            continue
        fund = funding.get(leg[1]) if leg[0] == "futures" else None
        X = leg_features(df, p["ozellik"], fund, btc.get(leg[0]))
        fwd, known, sig = labels(df, H)
        part = X.copy()
        part["_fwd"] = fwd
        part["_known"] = known
        part["_sig"] = sig
        part["_leg"] = li
        part["_pos"] = np.arange(len(df))
        part["_ts"] = df.index
        frames.append(part)
    if not frames:
        return {leg: pd.Series(np.nan, index=data[leg].index) for leg in legs}
    allf = pd.concat(frames, ignore_index=True)
    feat_cols = [c for c in allf.columns if not c.startswith("_")]
    Xall = allf[feat_cols].to_numpy(dtype=float)
    ts_ns = _ns(allf["_ts"])
    known = allf["_known"]
    known_ns = np.where(known.isna(), np.iinfo(np.int64).max, _ns(known.fillna(pd.Timestamp("2200-01-01", tz="UTC"))))
    fwd = allf["_fwd"].to_numpy(dtype=float)
    sig = allf["_sig"].to_numpy(dtype=float)
    feat_ok = np.isfinite(Xall).all(axis=1) & np.isfinite(sig) & (sig > 0)
    adim = int(p["adim"]) if int(p["adim"]) > 0 else max(1, H // 4)
    sub = (allf["_pos"].to_numpy() % adim) == 0
    train_ok = feat_ok & np.isfinite(fwd) & sub
    if p.get("egitim", "kendi") == "spot":
        spot_rows = np.isin(allf["_leg"].to_numpy(), [i for i, leg in enumerate(legs) if leg[0] == "spot"])
        train_ok &= spot_rows
    scale = sig * math.sqrt(H)
    clf = _is_classifier(p["model"])
    if clf:
        y = (fwd > 0).astype(int)
    else:
        y = np.clip(np.where(np.isfinite(fwd), fwd, 0.0) / np.where(scale > 0, scale, np.nan), -4.0, 4.0)

    first = pd.Timestamp(ts_ns.min(), tz="UTC")
    last = pd.Timestamp(ts_ns.max(), tz="UTC")
    starts = _month_starts(first + pd.Timedelta(days=int(p["min_gun"])), last, int(p["yeniden"]))
    edge = np.full(len(allf), np.nan)
    win_ns = int(pd.Timedelta(days=int(p["pencere_gun"])).value) if int(p["pencere_gun"]) > 0 else None
    for i, a in enumerate(starts):
        a_ns = a.value
        b_ns = starts[i + 1].value if i + 1 < len(starts) else np.iinfo(np.int64).max
        pred_mask = feat_ok & (ts_ns >= a_ns) & (ts_ns < b_ns)
        if not pred_mask.any():
            continue
        tr = train_ok & (known_ns < a_ns)
        if win_ns is not None:
            tr &= ts_ns >= a_ns - win_ns
        if tr.sum() < int(p["min_satir"]):
            continue
        ytr = y[tr]
        if clf and len(np.unique(ytr)) < 2:
            continue
        model = _make_model(p)
        model.fit(Xall[tr], ytr)
        Xp = Xall[pred_mask]
        if clf:
            prob = model.predict_proba(Xp)[:, 1]
            e = (2.0 * prob - 1.0) * math.sqrt(2.0 / math.pi)
        else:
            e = model.predict(Xp)
        edge[pred_mask] = e * scale[pred_mask]
    out = {}
    leg_id = allf["_leg"].to_numpy()
    for li, leg in enumerate(legs):
        m = leg_id == li
        out[leg] = pd.Series(edge[m], index=data[leg].index) if m.any() else pd.Series(np.nan, index=data[leg].index)
    return out


# ---------------------------------------------------------------- önbellek

_CACHE: dict = {}
_CACHE_MAX = 64
_PRED_KEYS = (
    "model", "H", "pencere_gun", "min_gun", "min_satir", "yeniden", "ozellik", "adim",
    "C", "hgb_iter", "hgb_lr", "hgb_yaprak", "hgb_min_yaprak", "hgb_l2", "egitim",
)


def _fingerprint(data: dict, funding: dict) -> str:
    hsh = hashlib.sha1()
    for leg in sorted(data):
        df = data[leg]
        hsh.update(repr(leg).encode())
        hsh.update(str(len(df)).encode())
        if len(df):
            hsh.update(df.index.asi8.tobytes())
            hsh.update(np.ascontiguousarray(df[["open", "high", "low", "close", "volume"]].to_numpy(dtype=float)).tobytes())
    for sym in sorted(funding):
        f = funding[sym]
        hsh.update(sym.encode())
        hsh.update(str(len(f)).encode())
        if len(f):
            hsh.update(f.index.asi8.tobytes())
            hsh.update(f["funding_rate"].to_numpy(dtype=float).tobytes())
    return hsh.hexdigest()


def cached_edges(data: dict, funding: dict, p: dict) -> dict:
    key = (_fingerprint(data, funding), tuple((k, p[k]) for k in _PRED_KEYS))
    if key in _CACHE:
        return _CACHE[key]
    edges = walk_forward_edges(data, funding, p)
    if len(_CACHE) >= _CACHE_MAX:
        _CACHE.pop(next(iter(_CACHE)))
    _CACHE[key] = edges
    return edges


# ---------------------------------------------------------------- sinyal


def sinyal(data: dict, funding: dict, **params) -> dict:
    p = {**DEFAULTS, **params}
    edges = cached_edges(data, funding, p)
    H = int(p["H"])
    out = {}
    spot_only_training = p.get("egitim", "kendi") == "spot" and any(leg[0] == "futures" for leg in data)
    for leg, df in data.items():
        market = leg[0]
        if spot_only_training and market == "spot":
            out[leg] = pd.Series(0.0, index=df.index)
            continue
        e = edges[leg].reindex(df.index)
        thr = float(p["k"]) * RT_COST[market]
        s = pd.Series(0.0, index=df.index)
        s[e > thr] = 1.0
        if market == "futures" and p["yon"] == "iki":
            s[e < -thr] = -1.0
        if p["esleme"] == "ortusen":
            pos = s.rolling(H, min_periods=1).mean()
        elif p["esleme"] == "esik":
            pos = s
        else:
            raise ValueError(f"bilinmeyen eşleme: {p['esleme']}")
        if market == "futures":
            first = _first_funding_time(funding.get(leg[1]))
            if first is None:
                pos = pos * 0.0
            else:
                pos = pos.where(df.index >= first, 0.0)
        out[leg] = pos.fillna(0.0)
    return out


def make_spec(name: str, interval: str, market: str, universe: str = "PORT3", description: str = "", **params) -> StrategySpec:
    p = {**DEFAULTS, **params}
    legs = legs_for(market, universe)
    weights = None
    if market == "spot":
        p["yon"] = "uzun"
        p["egitim"] = "kendi"
    elif p["egitim"] == "spot":
        if "fon" in p["ozellik"]:
            raise ValueError("spot satırlarıyla eğitimde fonlama özelliği kullanılamaz")
        trade_legs = legs
        legs = trade_legs + legs_for("spot", universe)
        weights = {leg: 1.0 / len(trade_legs) for leg in trade_legs}
        weights.update({leg: 0.0 for leg in legs_for("spot", universe)})
    return StrategySpec(
        name=name,
        family=FAMILY,
        interval=interval,
        legs=legs,
        signal_fn=sinyal,
        params=p,
        weights=weights,
        description=description,
    )


# ---------------------------------------------------------------- dondurulmuş yapılandırmalar


def specs() -> list[StrategySpec]:
    """Dondurulup dev_valid'de bir kez değerlendirilen yapılandırmalar."""
    return []
