"""Duman testi: sinyal zamanlaması ve ileri bakış denetimi (performans hesaplanmaz, deftere yazılmaz)."""
import time

import pandas as pd

from grafik_analiz.research import DEV_TRAIN_END, assert_causal
from grafik_analiz.research.evaluate import compute_signals, load_data
from grafik_analiz.strategies.mevsimsellik import make_spec

tests = [
    ("t_tom", "1d", "spot", "BTCUSDT", {"yontem": "ay_donumu", "a": 3, "b": 3}),
    ("t_tom_fut", "1d", "futures", "BTCUSDT", {"yontem": "ay_donumu", "a": 3, "b": 3}),
    ("t_tom4h", "4h", "spot", "BTCUSDT", {"yontem": "ay_donumu", "a": 3, "b": 3, "kayma_saat": -4}),
    ("t_dow", "1d", "spot", "BTCUSDT", {"yontem": "hafta_gunu", "gunler": [0, 2]}),
    ("t_saat", "1h", "futures", "BTCUSDT", {"yontem": "saat", "saatler_uzun": [21, 22], "saatler_kisa": [2, 3]}),
    ("t_ny", "1h", "spot", "BTCUSDT", {"yontem": "saat", "tz": "America/New_York", "saatler_uzun": [17, 18], "hafta_ici": True}),
    ("t_fon", "1h", "futures", "ETHUSDT", {"yontem": "fonlama", "esik": 0.0003, "bas_dk": 0, "tut_dk": 60}),
    ("t_fon15", "15m", "futures", "ETHUSDT", {"yontem": "fonlama", "esik": 0.0003, "bas_dk": -60, "tut_dk": 120}),
    ("t_us", "1h", "futures", "BTCUSDT", {"yontem": "uyarlamali_saat", "L": 180, "esik_bp": 5}),
    ("t_ua", "1d", "spot", "BTCUSDT", {"yontem": "uyarlamali_ay", "L_ay": 0, "esik_bp": 20}),
]
for name, iv, m, u, p in tests:
    spec = make_spec(name, iv, m, u, p)
    t0 = time.time()
    data, funding = load_data(spec, "dev")
    data = {k: v[v.index < DEV_TRAIN_END] for k, v in data.items()}
    funding = {k: v[v.index < DEV_TRAIN_END] for k, v in funding.items()}
    sig = compute_signals(spec, data, funding)
    s = sig[spec.legs[0]]
    print(f"{name}: n={len(s)} mean={s.mean():.3f} min={s.min()} max={s.max()} nz_first={s[s!=0].index[:1].tolist()} ({time.time()-t0:.1f}s)")
    if name == "t_tom":
        print(s["2022-12-25":"2023-01-06"].to_string())
    if name == "t_tom4h":
        print(s["2022-12-28 08:00":"2022-12-29 04:00"].to_string())
    if name == "t_saat":
        print(s["2023-03-01 00:00":"2023-03-01 05:00"].to_string(), s["2023-03-01 19:00":"2023-03-01 23:00"].to_string())
    if name == "t_ny":
        print(s["2023-03-10 19:00":"2023-03-10 23:00"].to_string(), s["2023-03-14 19:00":"2023-03-14 23:00"].to_string())
    if name == "t_fon15":
        f = funding["ETHUSDT"]["funding_rate"]
        print(s[s != 0].head(10).to_string())
    t0 = time.time()
    assert_causal(spec)
    print(f"   assert_causal OK ({time.time()-t0:.1f}s)")
