"""Kırılım ve oynaklık ailesi ("kirilim").

Bütün sinyaller nedenseldir: t barındaki hedef pozisyon yalnızca t ve önceki
barların kapanmış verisiyle hesaplanır. Kullanılan araçlar: geriye dönük
pencereler (`rolling`), `shift(+k)`, gün içi kümülatif değerler, önceki günün
tamamlanmış değerleri ve baştan ileri yürüyen durum makinesi. Tam örneklem
istatistiği, ortalanmış pencere, `shift(-k)` kullanılmaz.

Yöntemler (``yontem`` parametresi):

- ``kanal``: Donchian kanal kırılımı. Kapanış önceki ``n`` barın en
  yükseğini geçince alım (vadelide en düşüğünün altına inince açığa satış).
  İsteğe bağlı hacim teyidi (hacim > ``hacim_k`` × önceki ``n`` barın
  ortalama hacmi), çıkış kanalı (``n_cikis``), ATR iz süren stop.
- ``sikisma``: Oynaklık sıkışması (Bollinger bantları Keltner kanalının
  içinde). Sıkışma en az ``min_sik`` bar sürüp son ``pencere`` bar içinde
  bittiyse, kapanış üst Bollinger bandını geçince alım / alt bandın altına
  inince satış.
- ``nr``: NR-k kırılımı. Önceki bar son ``nr_n`` barın en dar aralıklı barı
  ise ve kapanış onun en yükseğini geçerse alım, en düşüğünün altına inerse
  satış.
- ``acilis``: Günlük açılış aralığı kırılımı (00:00 UTC). Günün ilk
  ``or_saat`` saatinin en yükseği/en düşüğü aralığı belirler; aralık bitince
  kapanış aralığın üstüne çıkarsa alım, altına inerse satış. Gün sonunda
  (son barın kapanışında) pozisyon kapatılır.
- ``williams``: Oynaklık kırılımı (L. Williams). Eşik = gün açılışı ±
  ``k`` × önceki günün aralığı. Kapanış eşiği geçince o yönde pozisyon,
  gün sonunda kapanış.

Ortak çıkışlar: ATR iz süren stop (``atr_k`` × ATR, pozisyon içindeki en
uç fiyattan), çıkış kanalı, en fazla ``max_bar`` bar tutma, gün sonu.
Ortak filtreler: trend (``trend_n`` barlık EMA'nın doğru tarafında olma),
oynaklık rejimi (ATR/fiyat oranının son ``rejim_n`` bar içindeki yüzdelik
sırası ``vol_alt`` … ``vol_ust`` arasında).

`specs()` yalnızca dondurulup dev_valid'de bir kez değerlendirilen
yapılandırmaları döndürür (bkz. `arastirma/kirilim/RAPOR.md`).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from grafik_analiz.indicators import atr, bollinger, ema
from grafik_analiz.research.evaluate import StrategySpec

FAMILY = "kirilim"

COINS = ("BTCUSDT", "ETHUSDT", "SOLUSDT")

BAR_MINUTES = {"5m": 5, "15m": 15, "1h": 60, "4h": 240, "1d": 1440}


def legs_for(market: str, universe: str) -> tuple:
    """`universe`: tek coin sembolü ya da üç coinlik eşit ağırlıklı portföy için 'PORT3'."""
    if universe == "PORT3":
        return tuple((market, c) for c in COINS)
    if universe == "PORT2":
        return tuple((market, c) for c in COINS[:2])
    return ((market, universe),)


# ---------------------------------------------------------------- yardımcılar


def _bar_minutes(index: pd.DatetimeIndex) -> int:
    if len(index) < 2:
        return 1440
    step = pd.Series(index[1:] - index[:-1]).median()
    return max(1, int(round(step.total_seconds() / 60.0)))


def _vol_rank(df: pd.DataFrame, atr_n: int, rejim_n: int) -> pd.Series:
    """ATR/fiyat oranının son `rejim_n` bar içindeki yüzdelik sırası (0–1, nedensel)."""
    rv = atr(df, atr_n) / df["close"]
    return rv.rolling(rejim_n, min_periods=rejim_n).rank(pct=True)


def _day_parts(index: pd.DatetimeIndex, bar_min: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Gün kimliği, gün içindeki bar sırası ve günün son barı mı bayrağı."""
    day = index.floor("1D")
    pos = ((index - day).total_seconds() // (bar_min * 60)).astype(int).to_numpy()
    bars_per_day = 1440 // bar_min
    last = pos == bars_per_day - 1
    day_code = pd.factorize(day)[0]
    return day_code, pos, last


# ---------------------------------------------------------------- durum makinesi


def _state_machine(
    close: np.ndarray,
    high: np.ndarray,
    low: np.ndarray,
    long_entry: np.ndarray,
    short_entry: np.ndarray,
    long_exit: np.ndarray,
    short_exit: np.ndarray,
    atr_arr: np.ndarray | None,
    atr_k: float,
    max_bar: int,
    flat: np.ndarray | None = None,
    day_code: np.ndarray | None = None,
    once_per_day: bool = False,
) -> np.ndarray:
    """Baştan ileri yürüyen pozisyon makinesi (1 alım, −1 satım, 0 nakit).

    Bütün kararlar t barının kapanışında, yalnızca t ve önceki değerlerle verilir.
    """
    n = len(close)
    out = np.zeros(n)
    state = 0
    held = 0
    extreme = np.nan
    last_long_day = -1
    last_short_day = -1
    use_atr = atr_arr is not None and atr_k > 0
    for i in range(n):
        c = close[i]
        exited = 0
        if state == 1:
            held += 1
            h = high[i]
            if h > extreme:
                extreme = h
            stop = use_atr and atr_arr[i] == atr_arr[i] and c < extreme - atr_k * atr_arr[i]
            if stop or long_exit[i] or (max_bar > 0 and held >= max_bar) or (flat is not None and flat[i]):
                state = 0
                exited = 1
        elif state == -1:
            held += 1
            lo = low[i]
            if lo < extreme:
                extreme = lo
            stop = use_atr and atr_arr[i] == atr_arr[i] and c > extreme + atr_k * atr_arr[i]
            if stop or short_exit[i] or (max_bar > 0 and held >= max_bar) or (flat is not None and flat[i]):
                state = 0
                exited = -1
        if state == 0 and not (flat is not None and flat[i]):
            d = day_code[i] if day_code is not None else -2
            if long_entry[i] and exited != 1 and not (once_per_day and d == last_long_day):
                state, held, extreme = 1, 0, high[i]
                last_long_day = d
            elif short_entry[i] and exited != -1 and not (once_per_day and d == last_short_day):
                state, held, extreme = -1, 0, low[i]
                last_short_day = d
        out[i] = state
    return out


# ---------------------------------------------------------------- giriş kuralları


def _entries_kanal(df: pd.DataFrame, p: dict) -> tuple[pd.Series, pd.Series, pd.Series, pd.Series]:
    n = int(p["n"])
    up = df["high"].shift(1).rolling(n, min_periods=n).max()
    dn = df["low"].shift(1).rolling(n, min_periods=n).min()
    close = df["close"]
    le = close > up
    se = close < dn
    hk = p.get("hacim_k") or 0.0
    if hk > 0:
        hn = int(p.get("hacim_n") or n)
        vol = df["volume"]
        base = vol.shift(1).rolling(hn, min_periods=hn).mean()
        ok = vol > hk * base
        le &= ok
        se &= ok
    nx = int(p.get("n_cikis") or 0)
    if nx > 0:
        xup = df["high"].shift(1).rolling(nx, min_periods=nx).max()
        xdn = df["low"].shift(1).rolling(nx, min_periods=nx).min()
        lx = close < xdn
        sx = close > xup
    else:
        lx = pd.Series(False, index=df.index)
        sx = pd.Series(False, index=df.index)
    return le, se, lx, sx


def _entries_sikisma(df: pd.DataFrame, p: dict) -> tuple[pd.Series, pd.Series, pd.Series, pd.Series]:
    n = int(p.get("bb_n", 20))
    bb = bollinger(df["close"], n, float(p.get("bb_k", 2.0)))
    mid = ema(df["close"], n)
    a = atr(df, n)
    kc_k = float(p.get("kc_k", 1.5))
    kc_up = mid + kc_k * a
    kc_dn = mid - kc_k * a
    squeeze = ((bb["bb_upper"] < kc_up) & (bb["bb_lower"] > kc_dn)).to_numpy()
    # Kesintisiz sıkışma süresi ve en son yeterli sıkışmanın bittiği bardan bu yana geçen süre.
    m = int(p.get("min_sik", 6))
    w = int(p.get("pencere", 3))
    run = np.zeros(len(squeeze), dtype=int)
    since = np.full(len(squeeze), 10**9)
    r = 0
    last_ok = -(10**9)
    for i, s in enumerate(squeeze):
        r = r + 1 if s else 0
        run[i] = r
        if r >= m:
            last_ok = i
        since[i] = i - last_ok
    recent = pd.Series(since <= w, index=df.index)
    close = df["close"]
    le = recent & (close > bb["bb_upper"])
    se = recent & (close < bb["bb_lower"])
    if p.get("cikis_orta"):
        lx = close < bb["bb_mid"]
        sx = close > bb["bb_mid"]
    else:
        lx = pd.Series(False, index=df.index)
        sx = pd.Series(False, index=df.index)
    return le, se, lx, sx


def _entries_nr(df: pd.DataFrame, p: dict) -> tuple[pd.Series, pd.Series, pd.Series, pd.Series]:
    k = int(p.get("nr_n", 7))
    rng = df["high"] - df["low"]
    nr = rng <= rng.rolling(k, min_periods=k).min()
    prev_nr = nr.shift(1, fill_value=False).astype(bool)
    close = df["close"]
    le = prev_nr & (close > df["high"].shift(1))
    se = prev_nr & (close < df["low"].shift(1))
    f = pd.Series(False, index=df.index)
    return le, se, f, f


def _daily_prev(df: pd.DataFrame, day: pd.DatetimeIndex) -> pd.DataFrame:
    """Önceki tamamlanmış UTC gününün değerleri, gün içi barlara eşlenmiş."""
    g = df.groupby(day)
    daily = pd.DataFrame({"open": g["open"].first(), "high": g["high"].max(), "low": g["low"].min(), "close": g["close"].last()})
    prev_close = daily["close"].shift(1)
    tr = pd.concat([daily["high"] - daily["low"], (daily["high"] - prev_close).abs(), (daily["low"] - prev_close).abs()], axis=1).max(axis=1)
    daily["atr14"] = tr.ewm(alpha=1.0 / 14, adjust=False, min_periods=14).mean()
    prev = daily.shift(1)  # yalnızca önceki günlerin bilgisi
    prev["range"] = prev["high"] - prev["low"]
    return prev.reindex(day).set_axis(df.index)


def _entries_acilis(df: pd.DataFrame, p: dict, bar_min: int):
    day = df.index.floor("1D")
    day_code, pos, last = _day_parts(df.index, bar_min)
    or_bars = max(1, int(round(float(p["or_saat"]) * 60 / bar_min)))
    in_or = pos < or_bars
    hi = df["high"].where(in_or).groupby(day).cummax()
    lo = df["low"].where(in_or).groupby(day).cummin()
    # Aralık, açılış aralığındaki son barın kapanışında belli olur; sonra gün boyu sabit.
    hi = hi.groupby(day).ffill()
    lo = lo.groupby(day).ffill()
    # Gün eksik başladıysa (ilk bar gecikmeliyse) o gün işlem yok.
    first_pos = pd.Series(pos, index=df.index).groupby(day).transform("min").to_numpy()
    valid = (pos >= or_bars) & (first_pos == 0)
    close = df["close"]
    le = (close > hi) & valid
    se = (close < lo) & valid
    w = p.get("genislik_ust")
    if w:
        prev = _daily_prev(df, day)
        narrow = (hi - lo) <= float(w) * prev["atr14"]
        le &= narrow
        se &= narrow
    stop = p.get("stop", "yok")
    if stop == "karsi":
        lx, sx = close < lo, close > hi
    elif stop == "orta":
        midp = (hi + lo) / 2.0
        lx, sx = close < midp, close > midp
    else:
        lx = pd.Series(False, index=df.index)
        sx = pd.Series(False, index=df.index)
    return le, se, lx, sx, last, day_code


def _entries_williams(df: pd.DataFrame, p: dict, bar_min: int):
    day = df.index.floor("1D")
    day_code, pos, last = _day_parts(df.index, bar_min)
    prev = _daily_prev(df, day)
    first_pos = pd.Series(pos, index=df.index).groupby(day).transform("min").to_numpy()
    day_open = df["open"].groupby(day).transform("first")
    k = float(p["k"])
    up = day_open + k * prev["range"]
    dn = day_open - k * prev["range"]
    close = df["close"]
    valid = first_pos == 0
    le = (close > up) & valid
    se = (close < dn) & valid
    stop = p.get("stop", "yok")
    if stop == "acilis":
        lx, sx = close < day_open, close > day_open
    else:
        lx = pd.Series(False, index=df.index)
        sx = pd.Series(False, index=df.index)
    return le, se, lx, sx, last, day_code


# ---------------------------------------------------------------- sinyal


def leg_signal(df: pd.DataFrame, allow_short: bool, p: dict) -> pd.Series:
    yontem = p["yontem"]
    bar_min = _bar_minutes(df.index)
    flat = None
    day_code = None
    once = False
    if yontem == "kanal":
        le, se, lx, sx = _entries_kanal(df, p)
    elif yontem == "sikisma":
        le, se, lx, sx = _entries_sikisma(df, p)
    elif yontem == "nr":
        le, se, lx, sx = _entries_nr(df, p)
    elif yontem == "acilis":
        le, se, lx, sx, flat, day_code = _entries_acilis(df, p, bar_min)
        once = True
    elif yontem == "williams":
        le, se, lx, sx, flat, day_code = _entries_williams(df, p, bar_min)
        once = True
    else:
        raise ValueError(f"bilinmeyen yöntem: {yontem}")

    close = df["close"]
    trend_n = int(p.get("trend_n") or 0)
    if trend_n > 0:
        e = ema(close, trend_n)
        le = le & (close > e)
        se = se & (close < e)
    vol_alt = p.get("vol_alt")
    vol_ust = p.get("vol_ust")
    if vol_alt is not None or vol_ust is not None:
        rk = _vol_rank(df, int(p.get("atr_n", 14)), int(p.get("rejim_n", 500)))
        ok = rk.notna()
        if vol_alt is not None:
            ok &= rk >= float(vol_alt)
        if vol_ust is not None:
            ok &= rk <= float(vol_ust)
        le = le & ok
        se = se & ok
    if not allow_short:
        se = pd.Series(False, index=df.index)

    atr_k = float(p.get("atr_k") or 0.0)
    a = atr(df, int(p.get("atr_n", 14))).to_numpy(dtype=float) if atr_k > 0 else None
    pos = _state_machine(
        close.to_numpy(dtype=float),
        df["high"].to_numpy(dtype=float),
        df["low"].to_numpy(dtype=float),
        le.fillna(False).to_numpy(dtype=bool),
        se.fillna(False).to_numpy(dtype=bool),
        lx.fillna(False).to_numpy(dtype=bool),
        sx.fillna(False).to_numpy(dtype=bool),
        a,
        atr_k,
        int(p.get("max_bar") or 0),
        flat=None if flat is None else np.asarray(flat, dtype=bool),
        day_code=day_code,
        once_per_day=once,
    )
    return pd.Series(pos, index=df.index)


def sinyal(data: dict, funding: dict, **p) -> dict:
    """Her bacak için hedef pozisyon. Spotta yalnız alım; vadelide `yon='iki'` ise açığa satış da."""
    out = {}
    for leg, df in data.items():
        market = leg[0]
        allow_short = market == "futures" and p.get("yon", "iki") == "iki"
        out[leg] = leg_signal(df, allow_short, p)
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


FROZEN_BASE = {"yontem": "kanal", "n": 90, "atr_n": 14, "atr_k": 4.0, "hacim_k": 1.25}
"""4h Donchian(90) kırılımı + hacim teyidi (1,25 × önceki 90 bar ortalaması) + ATR(14)×4 iz süren stop."""


def specs() -> list[StrategySpec]:
    """dev_train'de seçilip dondurulan ve dev_valid'de bir kez değerlendirilen yapılandırmalar."""
    return [
        make_spec(
            "kirilim_kanal4h_spot",
            "4h",
            "spot",
            "PORT3",
            dict(FROZEN_BASE),
            "Spot BTC/ETH/SOL eşit ağırlık, yalnız alım. 4h kapanış önceki 90 barın en yükseğini "
            "hacim > 1,25 × ortalama ile geçince alım; en yüksekten 4 × ATR(14) geri çekilince çıkış. "
            "candidate_check: GEÇTİ (dev_valid 1× +%47,6, 2× +%42,1, Sharpe 1,13, 47 işlem; DSR ≈ 0,01).",
        ),
        make_spec(
            "kirilim_kanal4h_vadeli_iki",
            "4h",
            "futures",
            "PORT3",
            dict(FROZEN_BASE),
            "Vadeli BTC/ETH/SOL eşit ağırlık, alım ve açığa satış (simetrik kurallar), fonlama dahil. "
            "candidate_check: GEÇMEDİ (dev_valid Sharpe 0,29 < 0,5; 1× +%6,0, 2× +%1,7).",
        ),
        make_spec(
            "kirilim_kanal4h_vadeli_uzun",
            "4h",
            "futures",
            "PORT3",
            dict(FROZEN_BASE, yon="uzun"),
            "Vadeli BTC/ETH/SOL eşit ağırlık, yalnız alım, fonlama dahil. "
            "candidate_check: GEÇTİ (dev_valid 1× +%47,4, 2× +%44,3, Sharpe 1,13, 45 işlem; DSR ≈ 0,01).",
        ),
    ]
