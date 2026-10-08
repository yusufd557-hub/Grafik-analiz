"""Hız ve sağlamlık denemesi: sinyal doğrudan hesaplanır, getiri HESAPLANMAZ (deftere yazılmaz)."""
import sys
import time

import numpy as np

from grafik_analiz.research.evaluate import load_data
from grafik_analiz.strategies import makine_ogrenmesi as mo

DEV_TRAIN_END = "2024-01-01"
cases = [
    ("4h", "spot", dict(model="logit", H=12)),
    ("4h", "futures", dict(model="hgb_clf", H=12)),
    ("1d", "futures", dict(model="hgb_reg", H=8, ozellik="temel+mum+fon+btc")),
    ("1h", "futures", dict(model="hgb_clf", H=12)),
]
if len(sys.argv) > 1:
    cases = [cases[int(i)] for i in sys.argv[1:]]
for interval, market, params in cases:
    spec = mo.make_spec("smoke", interval, market, **params)
    data, funding = load_data(spec, "dev")
    t0 = time.time()
    sig = spec.signal_fn(data, funding, **spec.params)
    dt = time.time() - t0
    msg = []
    for leg, s in sig.items():
        s = s[s.index < DEV_TRAIN_END]
        e = mo._CACHE[next(reversed(mo._CACHE))][leg]
        e = e[e.index < DEV_TRAIN_END]
        first = e.first_valid_index()
        msg.append(f"{leg[1][:3]} ilk_tahmin={first} pozda={float((s.abs()>0).mean()):.2f} ort_poz={float(s.mean()):.2f}")
    print(f"{interval} {market} {params} sure={dt:.1f}s | " + " | ".join(msg), flush=True)
