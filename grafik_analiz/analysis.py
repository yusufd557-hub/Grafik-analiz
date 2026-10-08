"""Tek bir coin/zaman dilimi için bütün grafik analizini çalıştırır."""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from .indicators import add_indicators
from .levels import FibRetracement, Level, Trendline, fibonacci, support_resistance, trendlines
from .patterns.base import BROKEN, FORMING, Formation
from .patterns.candles import SPEC_BY_KEY, CandleSpec, detect_candles
from .patterns.chart import detect_chart_patterns, merge_scales
from .pivots import ZigZag, zigzag
from .stats import candle_stats, formation_stats


def _num(value: float, digits: int = 1) -> str:
    return f"{value:.{digits}f}".replace(".", ",")


@dataclass(frozen=True)
class AnalysisConfig:
    scales: tuple[float, ...] = (2.0, 4.0)
    """Formasyon aramasında kullanılan zigzag eşikleri (ATR katı)."""
    level_scale: float = 2.0
    """Destek/direnç ve Fibonacci için pivot ölçeği."""
    trend_scale: float = 4.0
    """Trend çizgileri için pivot ölçeği."""
    candle_horizon: int = 6
    """Mum formasyonu istatistiğinde bakılan ileri bar sayısı."""
    max_bars: int | None = 150_000
    """Analize alınan en fazla son bar (5 dakikalıkta hız için)."""


@dataclass
class CandleEvent:
    index: int
    spec: CandleSpec


@dataclass
class AnalysisResult:
    symbol: str
    interval: str
    frame: pd.DataFrame
    zigzags: dict[float, ZigZag]
    formations: list[Formation]
    candles: pd.DataFrame
    levels: list[Level]
    trendlines: list[Trendline]
    fib: FibRetracement | None
    formation_stats: pd.DataFrame
    candle_stats: pd.DataFrame
    config: AnalysisConfig = field(default_factory=AnalysisConfig)

    @property
    def as_of(self) -> int:
        return len(self.frame) - 1

    @property
    def last_time(self) -> pd.Timestamp:
        return self.frame.index[-1]

    def active_formations(self) -> list[Formation]:
        """Son barda kırılım bekleyen veya kırılıp sonucu henüz belli olmayanlar."""
        t = self.as_of
        return [f for f in self.formations if f.status_at(t) in (FORMING, BROKEN)]

    def formations_in(self, start: int, end: int | None = None) -> list[Formation]:
        end = self.as_of if end is None else end
        return [f for f in self.formations if f.end_index >= start and f.start_index <= end]

    def candle_events(self, start: int = 0, end: int | None = None) -> list[CandleEvent]:
        end = self.as_of if end is None else end
        sub = self.candles.iloc[start : end + 1]
        events = []
        for key in sub.columns:
            for pos in np.flatnonzero(sub[key].to_numpy()):
                events.append(CandleEvent(start + int(pos), SPEC_BY_KEY[key]))
        return sorted(events, key=lambda e: e.index)

    def indicator_snapshot(self) -> list[tuple[str, str]]:
        """Son bardaki gösterge durumunun okunur özeti."""
        row = self.frame.iloc[-1]
        out: list[tuple[str, str]] = []
        c, e20, e50, e200 = row["close"], row["ema20"], row["ema50"], row["ema200"]
        if np.isfinite(e200):
            if c > e20 > e50 > e200:
                trend = "Yükseliş (fiyat > EMA20 > EMA50 > EMA200)"
            elif c < e20 < e50 < e200:
                trend = "Düşüş (fiyat < EMA20 < EMA50 < EMA200)"
            else:
                side = "üstünde" if c > e200 else "altında"
                trend = f"Karışık (fiyat EMA200'ün {side})"
            out.append(("EMA dizilimi", trend))
        if np.isfinite(row["rsi"]):
            r = row["rsi"]
            zone = "aşırı alım" if r >= 70 else "aşırı satım" if r <= 30 else "nötr bölge"
            out.append(("RSI(14)", f"{_num(r)} — {zone}"))
        if np.isfinite(row["macd_hist"]):
            prev = self.frame["macd_hist"].iloc[-2] if len(self.frame) > 1 else np.nan
            side = "pozitif" if row["macd_hist"] > 0 else "negatif"
            change = "artıyor" if row["macd_hist"] > prev else "azalıyor"
            out.append(("MACD histogramı", f"{side}, {change}"))
        if np.isfinite(row["adx"]):
            strength = "güçlü trend" if row["adx"] >= 25 else "zayıf trend / yatay" if row["adx"] < 20 else "orta"
            lead = "+DI önde" if row["plus_di"] > row["minus_di"] else "−DI önde"
            out.append(("ADX(14)", f"{_num(row['adx'])} — {strength}, {lead}"))
        if np.isfinite(row["bb_pos"]):
            out.append(("Bollinger konumu", f"%{100 * row['bb_pos']:.0f} (0 alt bant, 100 üst bant)"))
        if np.isfinite(row["stoch_k"]):
            out.append(("Stokastik %K", _num(row["stoch_k"])))
        if np.isfinite(row["mfi"]):
            out.append(("MFI(14)", _num(row["mfi"])))
        if np.isfinite(row["volume_ratio"]):
            out.append(("Hacim / 20 bar ort.", f"{_num(row['volume_ratio'], 2)}×"))
        if np.isfinite(row["atr"]):
            out.append(("ATR(14)", f"{_num(row['atr'], 2 if row['atr'] >= 1 else 4)} (%{_num(100 * row['atr'] / c, 2)})"))
        return out


def analyze(
    candles: pd.DataFrame,
    symbol: str = "",
    interval: str = "",
    config: AnalysisConfig | None = None,
) -> AnalysisResult:
    """Kapanmış mumlardan grafik analizini üretir. Son bar 'şimdi' kabul edilir."""
    config = config or AnalysisConfig()
    if config.max_bars is not None and len(candles) > config.max_bars:
        candles = candles.iloc[-config.max_bars :]
    if len(candles) < 50:
        raise ValueError("analiz için en az 50 mum gerekir")

    frame = add_indicators(candles)
    high = frame["high"].to_numpy(dtype=float)
    low = frame["low"].to_numpy(dtype=float)
    close = frame["close"].to_numpy(dtype=float)
    atr = frame["atr"].to_numpy(dtype=float)
    as_of = len(frame) - 1

    scales = sorted(set(config.scales) | {config.level_scale, config.trend_scale})
    zigzags = {s: zigzag(high, low, atr, s) for s in scales}
    groups = [detect_chart_patterns(close, high, low, atr, zigzags[s]) for s in config.scales]
    formations = merge_scales(groups)

    candle_flags = detect_candles(frame, frame["atr"])
    atr_now = float(atr[-1])
    level_pivots = zigzags[config.level_scale].pivots
    levels = support_resistance(level_pivots, float(close[-1]), atr_now, as_of)
    lines = trendlines(zigzags[config.trend_scale].pivots, close, atr_now, as_of)
    fib = fibonacci(zigzags[config.trend_scale].pivots, as_of)

    return AnalysisResult(
        symbol=symbol,
        interval=interval,
        frame=frame,
        zigzags=zigzags,
        formations=formations,
        candles=candle_flags,
        levels=levels,
        trendlines=lines,
        fib=fib,
        formation_stats=formation_stats(formations, as_of),
        candle_stats=candle_stats(candle_flags, frame["close"], config.candle_horizon, as_of),
        config=config,
    )
