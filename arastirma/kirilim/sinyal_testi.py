"""Sinyal üretiminin doğruluk/zaman testi. Getiri hesaplanmaz; yalnız pozisyon serileri ve assert_causal."""
import time
import numpy as np
import pandas as pd
from grafik_analiz.research import assert_causal
from grafik_analiz.research.evaluate import load_data, compute_signals
from grafik_analiz.strategies.kirilim import make_spec

tests = [
    ("4h", "futures", "BTCUSDT", {"yontem": "kanal", "n": 20, "n_cikis": 10, "atr_k": 3.0, "hacim_k": 1.5}),
    ("1h", "futures", "BTCUSDT", {"yontem": "sikisma", "bb_n": 20, "bb_k": 2.0, "kc_k": 1.5, "min_sik": 6, "pencere": 3, "atr_k": 2.5, "cikis_orta": True}),
    ("4h", "futures", "BTCUSDT", {"yontem": "nr", "nr_n": 7, "atr_k": 2.0, "max_bar": 12}),
    ("15m", "futures", "BTCUSDT", {"yontem": "acilis", "or_saat": 1, "stop": "karsi"}),
    ("1h", "futures", "BTCUSDT", {"yontem": "williams", "k": 0.5, "stop": "yok"}),
    ("1h", "spot", "PORT3", {"yontem": "kanal", "n": 48, "atr_k": 3.0, "trend_n": 200, "vol_ust": 0.7, "rejim_n": 500}),
]
for iv, mk, uni, p in tests:
    spec = make_spec("test", iv, mk, uni, p)
    t0 = time.time()
    data, funding = load_data(spec, "dev")
    sig = compute_signals(spec, data, funding)
    t1 = time.time()
    for leg, s in sig.items():
        s = pd.Series(s)
        ch = (s.diff().abs() > 0).sum()
        print(iv, mk, leg, p["yontem"], "bars", len(s), "changes", int(ch), "long%", round((s > 0).mean(), 3), "short%", round((s < 0).mean(), 3), "t", round(t1 - t0, 2))
    if p["yontem"] in ("acilis", "williams"):
        s = pd.Series(sig[spec.legs[0]])
        df = data[spec.legs[0]]
        # gün sonu kontrolü: 23:xx son barlarında pozisyon 0 olmalı (karar), ve gün başında pozisyon yok
        last = s[(df.index.hour == 23) & (df.index.minute == (45 if iv == "15m" else 0))]
        print("  son bar pozisyon !=0:", int((last != 0).sum()), " ilk saat pozisyon !=0:", int((s[df.index.hour == 0] != 0).sum()))
        # Gün başına giriş sayısı
        ent = (s.diff().fillna(s) != 0) & (s != 0)
        print("  gün başına giriş dağılımı:", ent.groupby(df.index.floor('1D')).sum().value_counts().to_dict())
    t2 = time.time()
    assert_causal(spec)
    print("  assert_causal OK", round(time.time() - t2, 1), "s")
