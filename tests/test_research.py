import json

import numpy as np
import pandas as pd
import pytest

from grafik_analiz.data import FUTURES, SPOT, CandleStore
from grafik_analiz.research import data as rdata
from grafik_analiz.research.backtest import backtest_leg
from grafik_analiz.research.evaluate import StrategySpec, assert_causal, candidate_check, evaluate, holdout_check
from grafik_analiz.research.metrics import block_bootstrap_means, deflated_sharpe, summarize
from grafik_analiz.research.protocol import DEV_END, FUTURES_COSTS, HOLDOUT_END, SPOT_COSTS, Costs

ZERO = Costs(0.0, 0.0)


def _frame(closes, start="2024-01-01", freq="1h"):
    closes = np.asarray(closes, dtype=float)
    opens = np.concatenate([[closes[0]], closes[:-1]])
    index = pd.date_range(start, periods=len(closes), freq=freq, tz="UTC")
    step = index[1] - index[0]
    return pd.DataFrame(
        {
            "open": opens,
            "high": np.maximum(opens, closes) * 1.001,
            "low": np.minimum(opens, closes) * 0.999,
            "close": closes,
            "volume": 1.0,
            "close_time": index + step - pd.Timedelta(milliseconds=1),
        },
        index=index,
    )


# ---------------------------------------------------------------- backtest


def test_signal_executes_next_bar_open():
    frame = _frame([100, 101, 102, 103, 104, 105, 106, 107])
    target = pd.Series(0.0, index=frame.index)
    target.iloc[3] = 1.0  # 3. bar kapanışında karar
    res = backtest_leg(frame, target, SPOT, costs=ZERO)
    assert list(res.position.to_numpy()) == [0, 0, 0, 0, 1, 0, 0, 0]
    # 4. bar: açılış 103 → sonraki açılış 104.
    assert res.net.iloc[4] == pytest.approx(104 / 103 - 1)
    assert res.net.drop(res.net.index[4]).abs().sum() == 0


def test_always_long_matches_buy_and_hold_minus_entry_cost():
    rng = np.random.default_rng(1)
    closes = 100 * np.exp(np.cumsum(rng.normal(0, 0.01, 500)))
    frame = _frame(closes)
    res = backtest_leg(frame, pd.Series(1.0, index=frame.index), SPOT)
    total = float((1 + res.net).prod() - 1)
    passive = closes[-1] / frame["open"].iloc[1] - 1
    assert total == pytest.approx((1 + passive) * (1 - SPOT_COSTS.per_side) - 1, rel=1e-3)
    assert len(res.trades) == 1 and res.cost.sum() == pytest.approx(SPOT_COSTS.per_side)


def test_spot_cannot_short_and_futures_short_mirrors():
    frame = _frame([100, 99, 98, 97, 96, 95])
    short = pd.Series(-1.0, index=frame.index)
    spot = backtest_leg(frame, short, SPOT, costs=ZERO)
    assert spot.position.abs().sum() == 0
    fut = backtest_leg(frame, short, FUTURES, costs=ZERO)
    assert (fut.net.iloc[1:-1] > 0).all()


def test_flip_costs_twice():
    frame = _frame([100] * 6)
    target = pd.Series([1, 1, -1, -1, 0, 0], index=frame.index, dtype=float)
    res = backtest_leg(frame, target, FUTURES)
    c = FUTURES_COSTS.per_side
    assert list(res.cost.round(10)) == [0, c, 0, 2 * c, 0, c]
    assert len(res.trades) == 2


def test_funding_sign_and_timing():
    frame = _frame([100] * 24, start="2024-01-01 00:00")
    target = pd.Series(1.0, index=frame.index)
    target.iloc[7] = 0.0  # 08:00 açılışında pozisyon kapanır
    funding = pd.DataFrame(
        {"funding_rate": [0.001, 0.001, 0.001]},
        index=pd.DatetimeIndex(pd.to_datetime(["2024-01-01 00:00", "2024-01-01 08:00", "2024-01-01 16:00"], utc=True)),
    )
    res = backtest_leg(frame, target, FUTURES, funding=funding, costs=ZERO)
    # 00:00: önceki pozisyon yok → 0. 08:00: o açılıştan önceki pozisyon uzun → öder.
    # 16:00: pozisyon 09:00'da yeniden açıldı → öder.
    assert res.funding.iloc[0] == 0
    assert res.funding.iloc[8] == pytest.approx(0.001)
    assert res.funding.iloc[16] == pytest.approx(0.001)
    short = backtest_leg(frame, -target, FUTURES, funding=funding, costs=ZERO)
    assert short.funding.iloc[16] == pytest.approx(-0.001)  # kısa pozisyon fonlama alır


# ---------------------------------------------------------------- metrikler


def test_summarize_and_bootstrap():
    idx = pd.date_range("2024-01-01", periods=24 * 100, freq="1h", tz="UTC")
    r = pd.Series(0.0001, index=idx)
    m = summarize(r)
    assert m["total_return"] == pytest.approx((1.0001) ** len(idx) - 1)
    assert m["p_value"] == 0.0 and m["max_drawdown"] == 0.0
    noise = np.random.default_rng(0).normal(0, 0.01, 400)
    means = block_bootstrap_means(noise)
    assert abs(means.mean() - noise.mean()) < 0.001


def test_deflated_sharpe_penalizes_many_trials():
    one = deflated_sharpe(1.5, 500, 1, 0.5, 0.0, 3.0)
    many = deflated_sharpe(1.5, 500, 1000, 0.5, 0.0, 3.0)
    assert one > many


# ---------------------------------------------------------------- dönem kilidi ve ileri bakış


@pytest.fixture
def research_store(tmp_path, monkeypatch):
    monkeypatch.setenv("GRAFIK_ANALIZ_ARASTIRMA", str(tmp_path / "veri"))
    monkeypatch.setattr(rdata, "research_dir", lambda: tmp_path / "arastirma")
    monkeypatch.setattr("grafik_analiz.research.ledger.research_dir", lambda: tmp_path / "arastirma")
    rdata.clear_cache()
    rdata.lock_holdout()
    rng = np.random.default_rng(3)
    n = (HOLDOUT_END - pd.Timestamp("2023-01-01", tz="UTC")).days + 30
    closes = 100 * np.exp(np.cumsum(rng.normal(0.0003, 0.02, n)))
    frame = _frame(closes, start="2023-01-01", freq="1D")
    CandleStore(tmp_path / "veri", market=SPOT).save("BTCUSDT", "1d", frame)
    yield tmp_path
    rdata.clear_cache()
    rdata.lock_holdout()


def test_holdout_locked_until_unlocked(research_store):
    dev = rdata.load("BTCUSDT", "1d")
    assert dev["close_time"].max() < DEV_END
    with pytest.raises(rdata.HoldoutLocked):
        rdata.load("BTCUSDT", "1d", scope="holdout")
    with pytest.raises(ValueError):
        rdata.unlock_holdout("kısa")
    rdata.unlock_holdout("test: holdout erişim kaydı denetimi")
    full = rdata.load("BTCUSDT", "1d", scope="holdout")
    assert full["close_time"].max() < HOLDOUT_END and len(full) > len(dev)
    log = (research_store / "arastirma" / "holdout_kayit.jsonl").read_text(encoding="utf-8").splitlines()
    assert json.loads(log[-1])["gerekce"].startswith("test:")


def _ma(data, funding, n=20):
    return {leg: (df["close"] > df["close"].rolling(n).mean()).astype(float) for leg, df in data.items()}


def _peek(data, funding):
    return {leg: (df["close"].shift(-1) > df["close"]).astype(float) for leg, df in data.items()}


def test_assert_causal_catches_lookahead(research_store):
    good = StrategySpec("ma", "test", "1d", (("spot", "BTCUSDT"),), _ma, {"n": 10})
    assert_causal(good)
    bad = StrategySpec("peek", "test", "1d", (("spot", "BTCUSDT"),), _peek)
    with pytest.raises(AssertionError, match="ileri bakış"):
        assert_causal(bad)


def test_evaluate_records_and_checks(research_store):
    spec = StrategySpec("ma", "test", "1d", (("spot", "BTCUSDT"),), _ma, {"n": 10})
    res = evaluate(spec)
    assert set(res) == {"dev_train", "dev_valid"} and set(res["dev_valid"]) == {1.0, 2.0}
    assert res["dev_valid"][2.0]["total_return"] < res["dev_valid"][1.0]["total_return"]
    checks = candidate_check(res)
    assert "aday" in checks
    lines = (research_store / "arastirma" / "deneyler" / "test.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(lines) == 4
    with pytest.raises(rdata.HoldoutLocked):
        evaluate(spec, windows=("holdout",), record=False)
    rdata.unlock_holdout("test: holdout değerlendirme yolu")
    hold = evaluate(spec, windows=("holdout",), record=False)
    result = holdout_check(hold, n_finalists=1)
    assert set(result) == {"seviye1", "seviye1_gecti", "seviye2", "seviye2_gecti"}
    assert hold["holdout"][1.0]["start"].startswith("2025-07-01")
