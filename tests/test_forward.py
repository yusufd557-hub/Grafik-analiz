import json

import numpy as np
import pandas as pd

from grafik_analiz.data import CandleStore
from grafik_analiz.forward.tracker import record, score
from grafik_analiz.research.evaluate import StrategySpec


def _store(root, n=600):
    rng = np.random.default_rng(5)
    closes = 100 * np.exp(np.cumsum(rng.normal(0, 0.01, n)))
    opens = np.concatenate([[closes[0]], closes[:-1]])
    index = pd.date_range("2026-07-01", periods=n, freq="4h", tz="UTC")
    frame = pd.DataFrame(
        {
            "open": opens,
            "high": np.maximum(opens, closes),
            "low": np.minimum(opens, closes),
            "close": closes,
            "volume": 1.0,
            "close_time": index + pd.Timedelta(hours=4) - pd.Timedelta(milliseconds=1),
        },
        index=index,
    )
    CandleStore(root, market="spot").save("BTCUSDT", "4h", frame)
    return frame


def _sig(data, funding, n=10):
    return {leg: (df["close"] > df["close"].rolling(n).mean()).astype(float) for leg, df in data.items()}


SPEC = StrategySpec("test_ma", "test", "4h", (("spot", "BTCUSDT"),), _sig, {"n": 10})


def test_record_only_new_bars_and_timeliness(tmp_path):
    frame = _store(tmp_path / "veri", n=600)
    out = tmp_path / "kayit"
    t0 = frame.index[400] + pd.Timedelta(hours=4, minutes=7)
    # İlk çalıştırma yalnız son kapanmış barı kaydeder (veri t0'a kadar kesilmiş gibi davranılır).
    CandleStore(tmp_path / "veri", market="spot").save("BTCUSDT", "4h", frame.iloc[:401])
    first = record(SPEC, tmp_path / "veri", now=t0, out_dir=out, update=False)
    assert len(first) == 1 and first[0]["bar"] == frame.index[400].isoformat() and first[0]["zamaninda"]
    # Üç bar sonra: aradaki barlar eklenir; geç kalanlar işaretlenir.
    CandleStore(tmp_path / "veri", market="spot").save("BTCUSDT", "4h", frame.iloc[:404])
    t1 = frame.index[403] + pd.Timedelta(hours=4, minutes=7)
    second = record(SPEC, tmp_path / "veri", now=t1, out_dir=out, update=False)
    assert [r["bar"] for r in second] == [frame.index[i].isoformat() for i in (401, 402, 403)]
    assert [r["zamaninda"] for r in second] == [False, False, True]
    lines = (out / "test_ma.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(lines) == 4 and all(json.loads(l)["kod"] == first[0]["kod"] for l in lines)


def test_score_uses_only_timely_records(tmp_path):
    frame = _store(tmp_path / "veri", n=600)
    out = tmp_path / "kayit"
    out.mkdir()
    rows = []
    for i, target in [(500, 1.0), (501, 0.0), (502, 1.0)]:
        bar = frame.index[i]
        rows.append({
            "strateji": "test_ma", "bar": bar.isoformat(), "kapanis": (bar + pd.Timedelta(hours=4)).isoformat(),
            "kayit": (bar + pd.Timedelta(hours=4, minutes=5)).isoformat(), "zamaninda": i != 501, "kod": "x",
            "hedef": {"spot:BTCUSDT": target},
        })
    (out / "test_ma.jsonl").write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
    res = score(SPEC, tmp_path / "veri", out_dir=out, now=frame.index[-1])
    # 501'in kaydı geç: hedefi kullanılmaz, 500'ün hedefi (1,0) korunur → tek kesintisiz işlem.
    assert res["kayit"] == 3 and res["zamaninda"] == 2
    assert res["olcu_1x"]["trades"] == 1
    assert res["olcu_1x"]["start"].startswith(str(frame.index[501].date()))
