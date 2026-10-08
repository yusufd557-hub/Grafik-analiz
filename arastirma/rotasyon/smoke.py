"""Sinyal kodunun duman testi: yalnız pozisyonlara bakar (getiri hesaplanmaz) ve ileri bakış denetimi."""
import time
from grafik_analiz.research import assert_causal
from grafik_analiz.research.evaluate import load_data, compute_signals
from grafik_analiz.strategies.rotasyon import make_spec, SPOT3, FUT3

cfgs = [
    make_spec("t1", "rotasyon", SPOT3, dict(lookback=28, skor="risk", top_k=1, every=7, filtre="ma100")),
    make_spec("t2", "rotasyon", SPOT3, dict(lookback=14, skor="getiri", top_k=2, every=1, filtre="mutlak", tampon=0.05, gunluk_filtre=True)),
    make_spec("t3", "uzun_kisa", FUT3, dict(lookback=28, skor="getiri", every=7, mod="ls")),
    make_spec("t4", "uzun_kisa", FUT3, dict(lookback=14, skor="risk", every=1, mod="ls_trend", ma=100)),
    make_spec("t5", "oran", (("futures","ETHUSDT"),("futures","BTCUSDT")), dict(alt="ETHUSDT", baz="BTCUSDT", n=50, mod="ls", every=7)),
]
for spec in cfgs:
    t = time.time()
    data, funding = load_data(spec, "dev")
    sig = compute_signals(spec, data, funding)
    for leg, s in sig.items():
        s = s[s.index < "2024-01-01"]
        nz = s[s != 0]
        print(spec.name, leg, "ilk!=0:", nz.index[0] if len(nz) else None, "ort:", round(s.mean(), 3), "degisim:", int((s.diff().abs() > 0).sum()))
    assert_causal(spec)
    print(spec.name, "causal OK", round(time.time() - t, 2), "s")
