"""Mum formasyonları.

Her formasyon kapanmış barlarla tanınır; t barındaki sinyal yalnızca t ve
önceki barlara bakar. Dönüş formasyonları bağlam ister: çekiç yalnızca
düşüşten sonra, asılı adam yalnızca yükselişten sonra anlamlıdır. Bağlam,
önceki beş barın ATR'ye göre net hareketiyle belirlenir.

Tanımlar Nison (*Japanese Candlestick Charting Techniques*) ve Bulkowski'nin
mum formasyonu ölçütlerine dayanır. Kriptoda bir barın açılışı genellikle
önceki barın kapanışına eşit olduğundan, "boşlukla açılış" isteyen klasik
koşullar eşitliğe izin verecek biçimde gevşetilmiştir.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class CandleSpec:
    key: str
    name: str
    bias: int


SPECS: tuple[CandleSpec, ...] = (
    CandleSpec("doji", "Doji", 0),
    CandleSpec("dragonfly_doji", "Yusufçuk doji", 1),
    CandleSpec("gravestone_doji", "Mezar taşı doji", -1),
    CandleSpec("spinning_top", "Topaç", 0),
    CandleSpec("hammer", "Çekiç", 1),
    CandleSpec("hanging_man", "Asılı adam", -1),
    CandleSpec("inverted_hammer", "Ters çekiç", 1),
    CandleSpec("shooting_star", "Kayan yıldız", -1),
    CandleSpec("bullish_engulfing", "Yutan boğa", 1),
    CandleSpec("bearish_engulfing", "Yutan ayı", -1),
    CandleSpec("bullish_harami", "Boğa harami", 1),
    CandleSpec("bearish_harami", "Ayı harami", -1),
    CandleSpec("piercing_line", "Delen mum", 1),
    CandleSpec("dark_cloud_cover", "Kara bulut örtüsü", -1),
    CandleSpec("morning_star", "Sabah yıldızı", 1),
    CandleSpec("evening_star", "Akşam yıldızı", -1),
    CandleSpec("three_white_soldiers", "Üç beyaz asker", 1),
    CandleSpec("three_black_crows", "Üç kara karga", -1),
    CandleSpec("bullish_marubozu", "Boğa marubozu", 1),
    CandleSpec("bearish_marubozu", "Ayı marubozu", -1),
    CandleSpec("tweezer_bottom", "Cımbız dip", 1),
    CandleSpec("tweezer_top", "Cımbız tepe", -1),
)

SPEC_BY_KEY = {s.key: s for s in SPECS}


def detect_candles(df: pd.DataFrame, atr: pd.Series | None = None, trend_bars: int = 5) -> pd.DataFrame:
    """Her formasyon için bir sütun (True/False) içeren tablo döndürür."""
    o, h, l, c = (df[col].astype(float) for col in ("open", "high", "low", "close"))
    if atr is None:
        from ..indicators import atr as atr_fn

        atr = atr_fn(df)
    a = atr.astype(float)

    body = (c - o).abs()
    rng = (h - l).replace(0.0, np.nan)
    upper = h - pd.concat([o, c], axis=1).max(axis=1)
    lower = pd.concat([o, c], axis=1).min(axis=1) - l
    bull = c > o
    bear = c < o
    body_top = pd.concat([o, c], axis=1).max(axis=1)
    body_bot = pd.concat([o, c], axis=1).min(axis=1)

    # Bağlam: formasyondan önceki barların net hareketi (formasyon barı hariç).
    move = c.shift(1) - c.shift(1 + trend_bars)
    down = move < -0.5 * a
    up = move > 0.5 * a

    def p(s: pd.Series, k: int = 1) -> pd.Series:
        return s.shift(k, fill_value=False) if s.dtype == bool else s.shift(k)

    long_body = body >= 0.6 * a
    small_body = body <= 0.3 * rng
    eps = 0.05 * a  # açılış eşitliği toleransı

    out: dict[str, pd.Series] = {}
    doji = body <= 0.1 * rng
    out["dragonfly_doji"] = doji & (upper <= 0.1 * rng) & (lower >= 0.6 * rng) & down
    out["gravestone_doji"] = doji & (lower <= 0.1 * rng) & (upper >= 0.6 * rng) & up
    out["doji"] = doji & ~out["dragonfly_doji"] & ~out["gravestone_doji"] & (rng >= 0.3 * a)
    out["spinning_top"] = (body > 0.1 * rng) & small_body & (upper > body) & (lower > body) & (rng >= 0.5 * a)

    hammer_shape = (lower >= 2 * body) & (upper <= 0.25 * rng) & (body > 0.05 * rng) & (rng >= 0.5 * a)
    star_shape = (upper >= 2 * body) & (lower <= 0.25 * rng) & (body > 0.05 * rng) & (rng >= 0.5 * a)
    out["hammer"] = hammer_shape & down
    out["hanging_man"] = hammer_shape & up
    out["inverted_hammer"] = star_shape & down
    out["shooting_star"] = star_shape & up

    out["bullish_engulfing"] = (
        p(bear) & bull & (c >= p(o)) & (o <= p(c) + eps) & (body > p(body)) & down
    )
    out["bearish_engulfing"] = (
        p(bull) & bear & (c <= p(o)) & (o >= p(c) - eps) & (body > p(body)) & up
    )
    inside_prev = (body_top <= p(body_top)) & (body_bot >= p(body_bot)) & (body <= 0.5 * p(body))
    out["bullish_harami"] = p(bear) & p(long_body) & bull & inside_prev & down
    out["bearish_harami"] = p(bull) & p(long_body) & bear & inside_prev & up

    prev_mid = (p(o) + p(c)) / 2
    out["piercing_line"] = (
        p(bear) & p(long_body) & bull & (o <= p(c) + eps) & (c > prev_mid) & (c < p(o)) & down
    )
    out["dark_cloud_cover"] = (
        p(bull) & p(long_body) & bear & (o >= p(c) - eps) & (c < prev_mid) & (c > p(o)) & up
    )

    first_mid = (p(o, 2) + p(c, 2)) / 2
    move2 = c.shift(2) - c.shift(2 + trend_bars)
    down2, up2 = move2 < -0.5 * a, move2 > 0.5 * a
    out["morning_star"] = (
        p(bear, 2) & p(long_body, 2) & (p(body) <= 0.3 * p(body, 2)) & bull & (c > first_mid) & down2
    )
    out["evening_star"] = (
        p(bull, 2) & p(long_body, 2) & (p(body) <= 0.3 * p(body, 2)) & bear & (c < first_mid) & up2
    )

    soldier = bull & (body >= 0.5 * a) & (upper <= 0.3 * body)
    crow = bear & (body >= 0.5 * a) & (lower <= 0.3 * body)
    opens_in_prev_body = (o >= p(body_bot) - eps) & (o <= p(body_top) + eps)
    out["three_white_soldiers"] = (
        soldier & p(soldier) & p(soldier, 2) & (c > p(c)) & (p(c) > p(c, 2)) & opens_in_prev_body & p(opens_in_prev_body)
    )
    out["three_black_crows"] = (
        crow & p(crow) & p(crow, 2) & (c < p(c)) & (p(c) < p(c, 2)) & opens_in_prev_body & p(opens_in_prev_body)
    )

    marubozu = (body >= 0.9 * rng) & (body >= a)
    out["bullish_marubozu"] = marubozu & bull
    out["bearish_marubozu"] = marubozu & bear

    out["tweezer_bottom"] = p(bear) & bull & ((l - p(l)).abs() <= 0.1 * a) & p(long_body) & down
    out["tweezer_top"] = p(bull) & bear & ((h - p(h)).abs() <= 0.1 * a) & p(long_body) & up

    frame = pd.DataFrame({spec.key: out[spec.key] for spec in SPECS}, index=df.index)
    return frame.fillna(False).astype(bool)
