"""Grafik ve mum formasyonları ailesi ("formasyon").

1. aşamadaki formasyon tanıyıcıları işlem tetikleyicisi olarak kullanılır:

- ``yontem="grafik"``: ATR eşikli zigzag pivotlarından klasik grafik
  formasyonları (`detect_chart_patterns`, ölçekler `merge_scales` ile
  birleştirilir; `analysis.py` ile aynı yol). Formasyonun kırılımı
  ``breakout_index`` barının kapanışında bilinir; hedef pozisyon o bardan
  itibaren verilir, işlem harness tarafından bir sonraki açılışta yapılır.
- ``yontem="mum"``: `detect_candles` ile mum formasyonları; sinyal formasyon
  barının kapanışında.

Bütün kararlar t barının kapanışında yalnız t ve önceki verilerle verilir.
Formasyon nesnelerinde kırılımdan sonra hesaplanan sonuç alanları (`outcome`)
kullanılmaz; çıkışlar burada kapanışlarla yeniden ve ileri yönde izlenir.

Çıkışlar (``cikis``):

- ``hedef``: kapanış hedefin ötesine (ölçülen hareket × ``hedef_k``) ya da
  stopun ötesine geçince çıkış; en fazla ``max_bar`` bar (0 ise formasyonun
  kendi süresi ``max(2 × genişlik, 10)``; mumda ``tutma``).
- ``stop_sure``: yalnız stop + süre (hedef yok).
- ``sure``: sabit ``tutma`` bar (grafikte ``max_bar``) tutma.
- ``atr`` (mum): giriş kapanışından ``stop_k`` × ATR stop, ``hedef_atr`` × ATR
  hedef, en fazla ``tutma`` bar.

Filtreler: trend (``trend_n`` barlık EMA'nın doğru tarafı; 0 kapalı), hacim
(sinyal barı hacmi > ``hacim_k`` × önceki 20 barın ortalaması; 0 kapalı).
Yön (``yon``): ``uzun`` (yalnız alım; düşüş sinyali açık alımı kapatır),
``iki`` (alım + açığa satış), ``kisa`` (yalnız açığa satış; vadeli).

Vadeli bacaklarda coinin ilk fonlama kaydından önce pozisyon 0 tutulur.

`specs()` yalnızca dondurulup dev_valid'de bir kez değerlendirilen
yapılandırmaları döndürür (bkz. `arastirma/formasyon/RAPOR.md`).
"""

from __future__ import annotations

from collections import OrderedDict

import numpy as np
import pandas as pd

from grafik_analiz.indicators import atr as atr_fn
from grafik_analiz.indicators import ema
from grafik_analiz.patterns.candles import SPEC_BY_KEY, detect_candles
from grafik_analiz.patterns.chart import detect_chart_patterns, merge_scales
from grafik_analiz.pivots import zigzag
from grafik_analiz.research.evaluate import StrategySpec

FAMILY = "formasyon"

COINS = ("BTCUSDT", "ETHUSDT", "SOLUSDT")

GRAFIK_GRUPLARI: dict[str, tuple[str, ...]] = {
    "ikili": ("double_top", "double_bottom"),
    "uclu": ("triple_top", "triple_bottom"),
    "obo": ("head_shoulders", "inverse_head_shoulders"),
    "ucgen": ("ascending_triangle", "descending_triangle", "symmetric_triangle"),
    "kama": ("rising_wedge", "falling_wedge"),
    "dikdortgen": ("rectangle",),
    "bayrak": ("bull_flag", "bear_flag"),
    "fincan": ("cup_handle", "inverse_cup_handle"),
}

MUM_GRUPLARI: dict[str, tuple[str, ...]] = {
    "doji_uc": ("dragonfly_doji", "gravestone_doji"),
    "cekic": ("hammer", "hanging_man"),
    "ters_cekic": ("inverted_hammer", "shooting_star"),
    "yutan": ("bullish_engulfing", "bearish_engulfing"),
    "harami": ("bullish_harami", "bearish_harami"),
    "delen": ("piercing_line", "dark_cloud_cover"),
    "yildiz": ("morning_star", "evening_star"),
    "asker": ("three_white_soldiers", "three_black_crows"),
    "marubozu": ("bullish_marubozu", "bearish_marubozu"),
    "cimbiz": ("tweezer_bottom", "tweezer_top"),
}


def legs_for(market: str, universe: str) -> tuple:
    """`universe`: tek coin sembolü ya da üç coinlik eşit ağırlıklı portföy için 'PORT3'."""
    if universe == "PORT3":
        return tuple((market, c) for c in COINS)
    return ((market, universe),)


def _expand(tipler, groups: dict[str, tuple[str, ...]]) -> set[str] | None:
    """Tip listesini formasyon anahtarlarına açar. 'hepsi' → None (hepsi)."""
    if tipler is None or tipler == "hepsi":
        return None
    if isinstance(tipler, str):
        tipler = [tipler]
    out: set[str] = set()
    for t in tipler:
        if t == "hepsi":
            return None
        out.update(groups.get(t, (t,)))
    return out


# ---------------------------------------------------------------- önbellek

_CACHE: OrderedDict = OrderedDict()
_CACHE_MAX = 96


def _frame_key(df: pd.DataFrame) -> tuple:
    if df.empty:
        return (0,)
    return (
        len(df),
        int(df.index[0].value),
        int(df.index[-1].value),
        float(df["close"].iloc[-1]),
        float(df["close"].sum()),
        float(df["volume"].sum()),
    )


def _cached(kind: str, df: pd.DataFrame, extra: tuple, fn):
    key = (kind, _frame_key(df), extra)
    if key in _CACHE:
        _CACHE.move_to_end(key)
        return _CACHE[key]
    value = fn()
    _CACHE[key] = value
    if len(_CACHE) > _CACHE_MAX:
        _CACHE.popitem(last=False)
    return value


def _atr(df: pd.DataFrame) -> np.ndarray:
    return _cached("atr", df, (), lambda: atr_fn(df, 14).to_numpy(dtype=float))


def _breakouts(df: pd.DataFrame, scales: tuple[float, ...]) -> pd.DataFrame:
    """Kırılımı gerçekleşmiş grafik formasyonları (kırılım barında bilinen alanlarla)."""

    def build() -> pd.DataFrame:
        high = df["high"].to_numpy(dtype=float)
        low = df["low"].to_numpy(dtype=float)
        close = df["close"].to_numpy(dtype=float)
        a = _atr(df)
        groups = []
        for s in scales:
            zz = zigzag(high, low, a, float(s))
            groups.append(detect_chart_patterns(close, high, low, a, zz))
        forms = merge_scales(groups) if len(groups) > 1 else (groups[0] if groups else [])
        rows = []
        for f in forms:
            if f.breakout_index is None or f.direction == 0:
                continue
            j = int(f.breakout_index)
            d = int(f.direction)
            boundary = f._boundary(d, j)
            rows.append(
                {
                    "bar": j,
                    "key": f.key,
                    "bias": int(f.bias),
                    "dir": d,
                    "scale": float(f.scale),
                    "boundary": float(boundary),
                    "target": float(f.target),
                    "stop": float(f.stop),
                    "width": int(f.width),
                    "outcome_bars": int(max(2 * f.width, 10)),
                }
            )
        cols = ["bar", "key", "bias", "dir", "scale", "boundary", "target", "stop", "width", "outcome_bars"]
        out = pd.DataFrame(rows, columns=cols)
        return out.sort_values(["bar", "scale"], ascending=[True, False], kind="mergesort").reset_index(drop=True)

    return _cached("grafik", df, tuple(float(s) for s in scales), build)


def _candles(df: pd.DataFrame) -> pd.DataFrame:
    return _cached("mum", df, (), lambda: detect_candles(df, pd.Series(_atr(df), index=df.index)))


# ---------------------------------------------------------------- filtreler


def _filters(df: pd.DataFrame, p: dict) -> tuple[np.ndarray, np.ndarray]:
    """Alım ve açığa satış için izin dizileri (t barında bilinen)."""
    n = len(df)
    long_ok = np.ones(n, dtype=bool)
    short_ok = np.ones(n, dtype=bool)
    close = df["close"]
    tn = int(p.get("trend_n") or 0)
    if tn > 0:
        e = _cached("ema", df, (tn,), lambda: ema(close, tn).to_numpy(dtype=float))
        c = close.to_numpy(dtype=float)
        valid = np.isfinite(e)
        long_ok &= valid & (c > e)
        short_ok &= valid & (c < e)
    hk = float(p.get("hacim_k") or 0.0)
    if hk > 0:
        vol = df["volume"]
        base = vol.shift(1).rolling(20, min_periods=20).mean().to_numpy(dtype=float)
        ok = np.isfinite(base) & (vol.to_numpy(dtype=float) > hk * base)
        long_ok &= ok
        short_ok &= ok
    return long_ok, short_ok


def _funding_allowed(df: pd.DataFrame, fund: pd.DataFrame | None) -> np.ndarray:
    """Vadelide ilk fonlama kaydı bar kapanışından önce/eşit değilse pozisyon yok."""
    if fund is None or fund.empty:
        return np.zeros(len(df), dtype=bool)
    first = fund.index[0]
    return (df["close_time"] >= first).to_numpy()


# ---------------------------------------------------------------- durum makinesi


def _run_events(
    close: np.ndarray,
    ev_bar: np.ndarray,
    ev_dir: np.ndarray,
    ev_tgt: np.ndarray,
    ev_stp: np.ndarray,
    ev_hold: np.ndarray,
    allow_long: bool,
    allow_short: bool,
    allowed: np.ndarray,
) -> np.ndarray:
    """Olaylardan pozisyon serisi. t barındaki karar yalnız t ve önceki kapanışlarla.

    Olay: (bar, yön, hedef, stop, en fazla tutma). Önce açık işlemin çıkışı
    kontrol edilir (kapanış hedef/stop ötesinde ya da süre doldu), sonra o barın
    olayı işlenir: izinli yönse yeni işlem eskisinin yerini alır, izinsiz yönse
    (yalnız alım modunda düşüş sinyali) açık pozisyon kapanır.
    """
    n = len(close)
    out = np.zeros(n)
    events = {int(b): k for k, b in enumerate(ev_bar)}
    state = 0
    tgt = stp = 0.0
    exit_at = -1
    for t in range(n):
        c = close[t]
        if state != 0:
            if t >= exit_at:
                state = 0
            elif state > 0 and (c >= tgt or c <= stp):
                state = 0
            elif state < 0 and (c <= tgt or c >= stp):
                state = 0
        k = events.get(t)
        if k is not None and allowed[t]:
            d = ev_dir[k]
            if (d > 0 and allow_long) or (d < 0 and allow_short):
                state = d
                tgt = ev_tgt[k]
                stp = ev_stp[k]
                exit_at = t + int(ev_hold[k])
            else:
                state = 0
        if not allowed[t]:
            state = 0
        out[t] = state
    return out


def _dedupe(bars: np.ndarray, dirs: np.ndarray) -> np.ndarray:
    """Her bar için ilk olayı seçer; aynı barda çelişen yönler varsa o bar atlanır. Seçilen satır indeksleri."""
    keep = []
    i = 0
    n = len(bars)
    while i < n:
        j = i
        while j + 1 < n and bars[j + 1] == bars[i]:
            j += 1
        ds = set(int(x) for x in dirs[i : j + 1])
        if len(ds) == 1:
            keep.append(i)
        i = j + 1
    return np.array(keep, dtype=int)


def _grafik_leg(df: pd.DataFrame, allowed: np.ndarray, p: dict) -> np.ndarray:
    scales = tuple(float(s) for s in (p.get("olcekler") or (2.0, 4.0)))
    br = _breakouts(df, scales)
    n = len(df)
    if br.empty:
        return np.zeros(n)
    keys = _expand(p.get("tipler", "hepsi"), GRAFIK_GRUPLARI)
    if keys is not None:
        br = br[br["key"].isin(keys)]
    if p.get("egilim_uyumu"):
        # Klasik eğilimi olan formasyonda yalnız eğilim yönündeki kırılım.
        br = br[(br["bias"] == 0) | (br["bias"] == br["dir"])]
    long_ok, short_ok = _filters(df, p)
    if len(br):
        bars = br["bar"].to_numpy()
        dirs = br["dir"].to_numpy()
        ok = np.where(dirs > 0, long_ok[bars], short_ok[bars])
        br = br[ok]
    if br.empty:
        return np.zeros(n)
    br = br.iloc[_dedupe(br["bar"].to_numpy(), br["dir"].to_numpy())]

    close = df["close"].to_numpy(dtype=float)
    d = br["dir"].to_numpy().astype(float)
    cikis = p.get("cikis", "hedef")
    hedef_k = float(p.get("hedef_k") or 1.0)
    max_bar = int(p.get("max_bar") or 0)
    hold = br["outcome_bars"].to_numpy() if max_bar <= 0 else np.full(len(br), max_bar)
    boundary = br["boundary"].to_numpy()
    tgt = boundary + hedef_k * (br["target"].to_numpy() - boundary)
    stp = br["stop"].to_numpy().astype(float)
    if cikis == "stop_sure":
        tgt = np.where(d > 0, np.inf, -np.inf)
    elif cikis == "sure":
        tgt = np.where(d > 0, np.inf, -np.inf)
        stp = np.where(d > 0, -np.inf, np.inf)
    elif cikis != "hedef":
        raise ValueError(f"bilinmeyen çıkış: {cikis}")
    yon = p.get("yon", "iki")
    return _run_events(
        close,
        br["bar"].to_numpy(),
        d,
        tgt,
        stp,
        hold,
        yon in ("uzun", "iki"),
        yon in ("kisa", "iki"),
        allowed,
    )


def _mum_leg(df: pd.DataFrame, allowed: np.ndarray, p: dict) -> np.ndarray:
    flags = _candles(df)
    keys = _expand(p.get("tipler", "hepsi"), MUM_GRUPLARI)
    cols = [c for c in flags.columns if SPEC_BY_KEY[c].bias != 0 and (keys is None or c in keys)]
    n = len(df)
    if not cols:
        return np.zeros(n)
    bull = np.zeros(n, dtype=bool)
    bear = np.zeros(n, dtype=bool)
    for c in cols:
        v = flags[c].to_numpy()
        if SPEC_BY_KEY[c].bias > 0:
            bull |= v
        else:
            bear |= v
    sig = np.where(bull & ~bear, 1, np.where(bear & ~bull, -1, 0))
    long_ok, short_ok = _filters(df, p)
    sig = np.where((sig > 0) & ~long_ok, 0, sig)
    sig = np.where((sig < 0) & ~short_ok, 0, sig)
    bars = np.flatnonzero(sig)
    if len(bars) == 0:
        return np.zeros(n)
    d = sig[bars].astype(float)
    close = df["close"].to_numpy(dtype=float)
    tutma = int(p.get("tutma") or 10)
    hold = np.full(len(bars), tutma)
    cikis = p.get("cikis", "sure")
    if cikis == "sure":
        tgt = np.where(d > 0, np.inf, -np.inf)
        stp = np.where(d > 0, -np.inf, np.inf)
    elif cikis == "atr":
        a = _atr(df)[bars]
        c0 = close[bars]
        sk = float(p.get("stop_k") or 0.0)
        hk = float(p.get("hedef_atr") or 0.0)
        stp = c0 - d * sk * a if sk > 0 else np.where(d > 0, -np.inf, np.inf)
        tgt = c0 + d * hk * a if hk > 0 else np.where(d > 0, np.inf, -np.inf)
        bad = ~np.isfinite(a)
        stp = np.where(bad, np.where(d > 0, -np.inf, np.inf), stp)
        tgt = np.where(bad, np.where(d > 0, np.inf, -np.inf), tgt)
    else:
        raise ValueError(f"bilinmeyen çıkış: {cikis}")
    yon = p.get("yon", "iki")
    return _run_events(close, bars, d, tgt, stp, hold, yon in ("uzun", "iki"), yon in ("kisa", "iki"), allowed)


def sinyal(data: dict, funding: dict, yontem: str = "grafik", **params) -> dict:
    out = {}
    p = dict(params)
    for leg, df in data.items():
        market, symbol = leg
        if len(df) == 0:
            out[leg] = pd.Series(0.0, index=df.index)
            continue
        if market == "futures":
            allowed = _funding_allowed(df, funding.get(symbol))
        else:
            allowed = np.ones(len(df), dtype=bool)
        if yontem == "grafik":
            pos = _grafik_leg(df, allowed, p)
        elif yontem == "mum":
            pos = _mum_leg(df, allowed, p)
        else:
            raise ValueError(f"bilinmeyen yöntem: {yontem}")
        if market == "spot":
            pos = np.clip(pos, 0.0, 1.0)
        out[leg] = pd.Series(pos, index=df.index, dtype=float)
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


# ---------------------------------------------------------------- dondurulanlar

FROZEN: list[dict] = [
    {
        "name": "formasyon_ucgen_kama_4h_trend_uzun",
        "interval": "4h",
        "market": "futures",
        "universe": "PORT3",
        "params": {"yontem": "grafik", "tipler": ["ucgen", "kama"], "yon": "uzun", "cikis": "hedef", "trend_n": 200},
        "description": (
            "4h üçgen/kama kırılımı, yalnız alım, kapanış EMA200 üstündeyken; çıkış kapanışla "
            "formasyon hedefi/stopu ya da formasyon süresi. Vadeli BTC/ETH/SOL eşit ağırlık. "
            "candidate_check: GEÇTİ (dev_valid Sharpe 1,00)."
        ),
    },
    {
        "name": "formasyon_ucgen_kama_4h_hacim_iki",
        "interval": "4h",
        "market": "futures",
        "universe": "PORT3",
        "params": {"yontem": "grafik", "tipler": ["ucgen", "kama"], "yon": "iki", "cikis": "hedef", "hacim_k": 1.5},
        "description": (
            "4h üçgen/kama kırılımı iki yönde (alım + açığa satış), kırılım barı hacmi > 1,5 × "
            "önceki 20 bar ortalaması; çıkış formasyon hedefi/stopu/süresi. Vadeli BTC/ETH/SOL eşit ağırlık. "
            "candidate_check: GEÇTİ (dev_valid Sharpe 1,13)."
        ),
    },
    {
        "name": "formasyon_hepsi_4h_trend_10bar_uzun",
        "interval": "4h",
        "market": "futures",
        "universe": "PORT3",
        "params": {"yontem": "grafik", "tipler": "hepsi", "yon": "uzun", "cikis": "sure", "max_bar": 10, "trend_n": 200},
        "description": (
            "4h bütün grafik formasyonlarının yukarı kırılımı, kapanış EMA200 üstündeyken alım, "
            "10 bar (40 saat) sabit tutma. Vadeli BTC/ETH/SOL eşit ağırlık. "
            "candidate_check: GEÇTİ (dev_valid Sharpe 1,12)."
        ),
    },
    {
        "name": "formasyon_hepsi_1d_olcek234_iki",
        "interval": "1d",
        "market": "futures",
        "universe": "PORT3",
        "params": {"yontem": "grafik", "tipler": "hepsi", "yon": "iki", "cikis": "hedef", "olcekler": [2.0, 3.0, 4.0]},
        "description": (
            "Günlük bütün grafik formasyonlarının kırılımı iki yönde, zigzag ölçekleri 2/3/4 ATR; "
            "çıkış kapanışla formasyon hedefi/stopu ya da formasyon süresi. Vadeli BTC/ETH/SOL eşit ağırlık. "
            "candidate_check: GEÇMEDİ (dev_valid Sharpe 0,31 < 0,5)."
        ),
    },
]
"""Dondurulup dev_valid'de bir kez değerlendirilen yapılandırmalar (RAPOR.md)."""


def specs() -> list[StrategySpec]:
    return [
        make_spec(f["name"], f["interval"], f["market"], f["universe"], f["params"], f.get("description", ""))
        for f in FROZEN
    ]
