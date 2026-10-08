import hashlib
import io
import zipfile

import numpy as np
import pandas as pd
import pytest

from grafik_analiz.data import CandleStore, RestClient, parse_klines
from grafik_analiz.data.binance import DataError, fetch_month_archive, to_milliseconds
from grafik_analiz.indicators import add_indicators, atr, ema, rsi
from grafik_analiz.levels import fibonacci, support_resistance, trendlines
from grafik_analiz.pivots import HIGH, LOW, Pivot, zigzag
from grafik_analiz.stats import wilson_interval

from .synthetic import random_walk


# ---------------------------------------------------------------- veri


def _row(open_ms, price=100.0, step_ms=3_600_000, micro=False):
    k = 1000 if micro else 1
    return [open_ms * k, price, price + 1, price - 1, price + 0.5, 10.0, (open_ms + step_ms - 1) * k, 1000.0, 5, 4.0, 400.0, 0]


def test_microsecond_timestamps_normalized():
    ms = 1735689600000  # 2025-01-01
    assert to_milliseconds(np.array([ms, ms * 1000]))[1] == ms
    frame = parse_klines([_row(ms, micro=True), _row(ms + 3_600_000)])
    assert list(frame.index) == [pd.Timestamp("2025-01-01 00:00", tz="UTC"), pd.Timestamp("2025-01-01 01:00", tz="UTC")]
    assert frame["close"].iloc[0] == 100.5


def test_parse_skips_header_row():
    raw = pd.DataFrame([["open_time"] + ["x"] * 11, [str(v) for v in _row(1735689600000)]])
    assert len(parse_klines(raw)) == 1


class FakeResponse:
    def __init__(self, status, content=b"", payload=None, text=""):
        self.status_code = status
        self.content = content
        self._payload = payload
        self.text = text
        self.headers = {}

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(self.status_code)


def _zip(rows):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("x.csv", "\n".join(",".join(str(v) for v in r) for r in rows))
    return buf.getvalue()


class FakeSession:
    def __init__(self, routes):
        self.routes = routes
        self.calls = []

    def get(self, url, params=None, timeout=None):
        self.calls.append((url, params))
        for prefix, handler in self.routes:
            if url.startswith(prefix):
                return handler(url, params)
        return FakeResponse(404)


def test_archive_checksum_verified():
    payload = _zip([_row(1735689600000)])
    good = hashlib.sha256(payload).hexdigest()
    session = FakeSession([
        ("https://data.binance.vision", lambda u, p: FakeResponse(200, text=f"{good}  f.zip") if u.endswith("CHECKSUM") else FakeResponse(200, payload)),
    ])
    assert len(fetch_month_archive(session, "BTCUSDT", "1h", 2025, 1)) == 1
    bad = FakeSession([
        ("https://data.binance.vision", lambda u, p: FakeResponse(200, text="00  f.zip") if u.endswith("CHECKSUM") else FakeResponse(200, payload)),
    ])
    with pytest.raises(DataError):
        fetch_month_archive(bad, "BTCUSDT", "1h", 2025, 1)


def test_rest_falls_back_to_next_host_and_paginates():
    start = 1735689600000
    rows = [_row(start + i * 3_600_000) for i in range(1500)]

    def second(url, params):
        cursor = params["startTime"]
        batch = [r for r in rows if r[0] >= cursor][: params["limit"]]
        return FakeResponse(200, payload=batch)

    session = FakeSession([("https://blocked", lambda u, p: FakeResponse(451)), ("https://ok", second)])
    client = RestClient(session=session, hosts=("https://blocked", "https://ok"), pause=0)
    frame = client.klines("BTCUSDT", "1h", start)
    assert len(frame) == 1500
    assert frame.index.is_monotonic_increasing
    # Çalışan adres hatırlanır: ikinci sayfa doğrudan oraya gider.
    assert session.calls[-1][0].startswith("https://ok")


def test_store_update_drops_unclosed_bar(tmp_path):
    start = pd.Timestamp("2026-10-01", tz="UTC")
    now = start + pd.Timedelta(hours=5, minutes=30)
    rows = [_row(int((start + pd.Timedelta(hours=i)).value // 1_000_000)) for i in range(6)]

    def rest(url, params):
        return FakeResponse(200, payload=[r for r in rows if r[0] >= params["startTime"]])

    session = FakeSession([("https://ok", rest)])
    store = CandleStore(tmp_path, session=session, rest=RestClient(session=session, hosts=("https://ok",), pause=0))
    frame = store.update("BTC", "1h", start="2026-10", now=now)
    assert len(frame) == 5  # 05:00 mumu 06:00'da kapanır
    assert store.path("BTCUSDT", "1h").exists()
    again = store.update("BTCUSDT", "1h", now=now)
    assert len(again) == 5


# ---------------------------------------------------------------- göstergeler


def test_indicators_basic_properties():
    frame = add_indicators(random_walk(800))
    valid = frame.dropna()
    assert ((valid["rsi"] >= 0) & (valid["rsi"] <= 100)).all()
    assert (valid["atr"] > 0).all()
    assert ((valid["mfi"] >= 0) & (valid["mfi"] <= 100)).all()
    pd.testing.assert_series_equal(
        ema(frame["close"], 10), frame["close"].ewm(span=10, adjust=False, min_periods=10).mean()
    )


def test_indicators_are_causal():
    frame = random_walk(600)
    full = add_indicators(frame)
    part = add_indicators(frame.iloc[:400])
    pd.testing.assert_frame_equal(full.iloc[:400], part)


def test_rsi_extremes():
    up = pd.Series(np.arange(100, dtype=float))
    assert rsi(up).iloc[-1] == 100.0
    assert rsi(-up).iloc[-1] == pytest.approx(0.0)


# ---------------------------------------------------------------- pivotlar ve seviyeler


def test_zigzag_alternates_and_is_causal():
    frame = add_indicators(random_walk(3000))
    h, l, a = frame["high"].values, frame["low"].values, frame["atr"].values
    full = zigzag(h, l, a, 2.0)
    kinds = [p.kind for p in full.pivots]
    assert len(kinds) > 30 and all(x != y for x, y in zip(kinds, kinds[1:]))
    assert all(p.confirmed > p.index for p in full.pivots)
    for cut in (700, 1500, 2900):
        part = zigzag(h[: cut + 1], l[: cut + 1], a[: cut + 1], 2.0)
        assert part.pivots == full.known_at(cut)


def test_zigzag_finds_known_extremes():
    from .synthetic import DOUBLE_TOP, path_frame

    frame = add_indicators(path_frame(DOUBLE_TOP))
    zz = zigzag(frame["high"].values, frame["low"].values, frame["atr"].values, 2.0)
    assert [(p.index, p.kind) for p in zz.pivots][-3:] == [(31, HIGH), (46, LOW), (61, HIGH)]


def test_support_resistance_clusters():
    pivots = [Pivot(10, 100.0, HIGH, 12), Pivot(30, 100.4, HIGH, 32), Pivot(50, 90.0, LOW, 52), Pivot(70, 89.8, LOW, 72), Pivot(80, 95, HIGH, 82)]
    levels = support_resistance(pivots, close=95.0, atr=1.0, as_of=100)
    kinds = {(round(lv.price), lv.kind, lv.touches) for lv in levels}
    assert kinds == {(100, "direnç", 2), (90, "destek", 2)}
    # Henüz kesinleşmemiş pivot kullanılmaz: 50. barda dipler bilinmiyor.
    early = support_resistance(pivots, 95.0, 1.0, as_of=50)
    assert [(round(lv.price), lv.kind) for lv in early] == [(100, "direnç")]


def test_trendline_and_fibonacci():
    close = np.linspace(90, 110, 101)
    pivots = [Pivot(20, 92.0, LOW, 22), Pivot(40, 100.0, HIGH, 42), Pivot(60, 96.0, LOW, 62), Pivot(80, 106, HIGH, 82)]
    lines = trendlines(pivots, close, atr=1.0, as_of=100)
    support = [tl for tl in lines if tl.kind == "destek"][0]
    assert support.value_at(60) == pytest.approx(96.0)
    fib = fibonacci(pivots, as_of=100)
    assert fib.levels[0.5] == pytest.approx(101.0)


def test_wilson_interval():
    lo, hi = wilson_interval(50, 100)
    assert lo < 0.5 < hi and hi - lo == pytest.approx(0.19, abs=0.01)
    assert np.isnan(wilson_interval(0, 0)[0])


def test_store_keeps_archive_when_rest_fails(tmp_path):
    rows = [_row(int((pd.Timestamp("2026-08-01", tz="UTC") + pd.Timedelta(hours=i)).value // 1_000_000)) for i in range(24 * 31)]
    payload = _zip(rows)

    def archive(url, params):
        if url.endswith("CHECKSUM"):
            return FakeResponse(404)
        return FakeResponse(200, payload) if "2026-08" in url else FakeResponse(404)

    session = FakeSession([("https://data.binance.vision", archive), ("https://blocked", lambda u, p: FakeResponse(451))])
    store = CandleStore(tmp_path, session=session, rest=RestClient(session=session, hosts=("https://blocked",), pause=0))
    messages = []
    frame = store.update("BTCUSDT", "1h", start="2025-01", now=pd.Timestamp("2026-10-08", tz="UTC"), progress=messages.append)
    assert len(frame) == 24 * 31
    assert store.load("BTCUSDT", "1h").index[-1] == pd.Timestamp("2026-08-31 23:00", tz="UTC")
    assert any("alınamadı" in m for m in messages)
