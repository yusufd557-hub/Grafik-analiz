import numpy as np
import pandas as pd
import pytest

from grafik_analiz.analysis import AnalysisConfig, analyze
from grafik_analiz.patterns.base import (
    BROKEN,
    FORMING,
    INVALID,
    NO_BREAKOUT,
    STOPPED,
    SUPERSEDED,
    TARGET,
    TIMEOUT,
    Formation,
    Line,
    resolve,
)
from grafik_analiz.patterns.candles import SPECS, detect_candles

from .synthetic import (
    ASCENDING_TRIANGLE,
    BULL_FLAG,
    CUP_HANDLE,
    DOUBLE_TOP,
    HEAD_SHOULDERS,
    mirror,
    path_frame,
    random_walk,
)

FULL = AnalysisConfig(max_bars=None)


def _only(result, key):
    found = [f for f in result.formations if f.key == key]
    assert len(found) == 1, [(f.key, f.start_index, f.end_index) for f in result.formations]
    return found[0]


@pytest.mark.parametrize(
    "anchors,key,direction,target,stop",
    [
        (DOUBLE_TOP, "double_top", -1, 69.1, 100.3),
        (mirror(DOUBLE_TOP), "double_bottom", 1, 130.9, 99.7),
        (HEAD_SHOULDERS, "head_shoulders", -1, 64.1, 95.3),
        (mirror(HEAD_SHOULDERS), "inverse_head_shoulders", 1, 135.9, 104.7),
        (ASCENDING_TRIANGLE, "ascending_triangle", 1, None, None),
        (mirror(ASCENDING_TRIANGLE), "descending_triangle", -1, None, None),
        (BULL_FLAG, "bull_flag", 1, 130.9, 91.7),
        (mirror(BULL_FLAG), "bear_flag", -1, 69.1, 108.3),
        (CUP_HANDLE, "cup_handle", 1, 130.9, 92.7),
        (mirror(CUP_HANDLE), "inverse_cup_handle", -1, 69.1, 107.3),
    ],
)
def test_synthetic_pattern_detected_and_reaches_target(anchors, key, direction, target, stop):
    result = analyze(path_frame(anchors), config=FULL)
    f = _only(result, key)
    assert f.direction == direction
    assert f.breakout_index is not None and f.breakout_index >= f.detected_index > f.end_index
    if target is not None:
        assert f.target == pytest.approx(target, abs=0.05)
        assert f.stop == pytest.approx(stop, abs=0.05)
    assert f.status_at(result.as_of) == TARGET


def test_measured_move_from_breakout_boundary():
    result = analyze(path_frame(ASCENDING_TRIANGLE), config=FULL)
    f = _only(result, "ascending_triangle")
    boundary = float(f.upper.at(f.breakout_index))
    assert f.target == pytest.approx(boundary + f.height)
    assert f.stop == pytest.approx(float(f.lower.at(f.breakout_index)))


def test_double_top_becomes_cup_and_is_superseded():
    result = analyze(path_frame(CUP_HANDLE), config=FULL)
    double = _only(result, "double_top")
    cup = _only(result, "cup_handle")
    assert double.superseded_index == cup.detected_index
    assert double.status_at(cup.detected_index - 1) == FORMING
    assert double.status_at(result.as_of) == SUPERSEDED
    assert double.breakout_index is None


def test_v_shape_is_not_a_cup():
    # Üçgenin içindeki V şekilli dip fincan sayılmamalı.
    result = analyze(path_frame(ASCENDING_TRIANGLE), config=FULL)
    assert not [f for f in result.formations if f.key == "cup_handle"]


def test_no_pattern_on_straight_trend():
    result = analyze(path_frame([(0, 50), (200, 150)]), config=FULL)
    assert result.formations == []


# ---------------------------------------------------------------- yaşam döngüsü


def _manual(allowed=(-1,), height=10.0) -> Formation:
    return Formation(
        key="double_top",
        name="İkili tepe",
        bias=-1,
        scale=2.0,
        start_index=0,
        end_index=10,
        detected_index=12,
        points=[(0, 110.0), (5, 100.0), (10, 110.0)],
        upper=Line.horizontal(0, 10, 110.0),
        lower=Line.horizontal(0, 10, 100.0),
        allowed=allowed,
        height=height,
        expiry_index=30,
        stop_levels={-1: 110.0},
    )


def _arrays(closes, highs=None, lows=None):
    c = np.array(closes, dtype=float)
    h = c + 0.5 if highs is None else np.array(highs, dtype=float)
    l = c - 0.5 if lows is None else np.array(lows, dtype=float)
    return c, h, l


def test_lifecycle_target():
    closes = [105.0] * 15 + [99.0] + [95.0] * 3 + [89.0] + [95.0] * 30
    c, h, l = _arrays(closes)
    f = _manual()
    assert resolve(f, c, h, l)
    assert f.breakout_index == 15 and f.target == 90.0 and f.stop == 110.0
    assert f.status_at(11) is None
    assert f.status_at(14) == FORMING
    assert f.status_at(15) == BROKEN
    assert f.status_at(19) == TARGET and f.outcome_index == 19


def test_same_bar_target_and_stop_counts_as_stop():
    closes = [105.0] * 15 + [99.0] + [100.0] * 30
    c, h, l = _arrays(closes)
    h[17], l[17] = 111.0, 89.0
    f = _manual()
    resolve(f, c, h, l)
    assert f.outcome == STOPPED and f.outcome_index == 17


def test_timeout_and_open_outcome():
    closes = [105.0] * 15 + [99.0] + [98.0] * 60
    c, h, l = _arrays(closes)
    f = _manual()
    resolve(f, c, h, l)
    assert f.outcome == TIMEOUT and f.outcome_index == 15 + f.outcome_bars
    # Veri pencere bitmeden kesilirse sonuç açık kalır.
    f2 = _manual()
    resolve(f2, c[:30], h[:30], l[:30])
    assert f2.outcome is None and f2.status_at(29) == BROKEN


def test_opposite_breakout_invalidates_and_expiry():
    closes = [105.0] * 15 + [111.0] + [105.0] * 30
    c, h, l = _arrays(closes)
    f = _manual()
    resolve(f, c, h, l)
    assert f.invalid_index == 15 and f.breakout_index is None
    assert f.status_at(15) == INVALID

    g = _manual()
    resolve(g, *_arrays([105.0] * 50))
    assert g.status_at(29) == FORMING and g.status_at(30) == NO_BREAKOUT


def test_stale_detection_rejected():
    # Formasyon bilindiğinde fiyat hedefe giden yolun yarısından fazlasını gitmişse kaydedilmez.
    closes = [105.0] * 12 + [93.0] + [90.0] * 20
    f = _manual()
    assert resolve(f, *_arrays(closes)) is False


# ---------------------------------------------------------------- nedensellik


def test_no_lookahead_in_formations():
    """Seri kısaltılınca geçmişte bilinen formasyonlar ve durumları değişmemeli."""
    frame = random_walk(2500)
    full = analyze(frame, config=FULL)
    assert len(full.formations) > 20
    for cut in (900, 1600, 2300):
        part = analyze(frame.iloc[: cut + 1], config=FULL)
        known_full = [
            (f.key, f.scale, f.start_index, f.end_index, f.detected_index, f.status_at(cut))
            for f in full.formations
            if f.detected_index <= cut
        ]
        known_part = [
            (f.key, f.scale, f.start_index, f.end_index, f.detected_index, f.status_at(cut))
            for f in part.formations
        ]
        assert known_part == known_full
        # Kırılımı bilinenlerin hedef ve stopları da aynı olmalı.
        for a, b in zip(
            [f for f in full.formations if f.detected_index <= cut], part.formations
        ):
            if a.breakout_index is not None and a.breakout_index <= cut:
                assert (a.target, a.stop, a.breakout_index) == (b.target, b.stop, b.breakout_index)


def test_no_lookahead_in_stats():
    frame = random_walk(2500, seed=11)
    full = analyze(frame, config=FULL)
    cut = 1800
    part = analyze(frame.iloc[: cut + 1], config=FULL)
    from grafik_analiz.stats import candle_stats, formation_stats

    pd.testing.assert_frame_equal(formation_stats(full.formations, cut), part.formation_stats)
    pd.testing.assert_frame_equal(
        candle_stats(full.candles, full.frame["close"], 6, cut), part.candle_stats
    )


# ---------------------------------------------------------------- mum formasyonları


def _candles(rows, prior_trend=-1.0, atr=1.0):
    """Önce `prior_trend` eğimli 30 bar, ardından verilen (o, h, l, c) satırları."""
    base = []
    price = 100.0
    for _ in range(30):
        o = price
        price += prior_trend
        base.append((o, max(o, price) + 0.2, min(o, price) - 0.2, price))
    frame = pd.DataFrame(base + rows, columns=["open", "high", "low", "close"])
    frame.index = pd.date_range("2024-01-01", periods=len(frame), freq="1h", tz="UTC")
    return detect_candles(frame, pd.Series(atr, index=frame.index))


def test_hammer_only_after_decline():
    hammer = [(70.0, 70.3, 66.5, 70.2)]
    assert _candles(hammer, prior_trend=-1.0)["hammer"].iloc[-1]
    flags = _candles([(130.0, 130.3, 126.5, 130.2)], prior_trend=1.0)
    assert not flags["hammer"].iloc[-1] and flags["hanging_man"].iloc[-1]


def test_engulfing_and_morning_star():
    eng = _candles([(70.0, 70.2, 69.0, 69.2), (69.2, 70.6, 69.0, 70.5)])
    assert eng["bullish_engulfing"].iloc[-1]
    star = _candles([(70.0, 70.1, 68.9, 69.0), (69.0, 69.2, 68.7, 68.9), (68.9, 69.9, 68.8, 69.8)])
    assert star["morning_star"].iloc[-1]


def test_candle_columns_complete():
    flags = detect_candles(random_walk(500))
    assert list(flags.columns) == [s.key for s in SPECS]
    assert flags.dtypes.eq(bool).all()
