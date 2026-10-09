"""Duman testi: sinyal üretimi, süre ve pozisyon yapısı (performans bilgisi yok)."""
import time

import numpy as np
import pandas as pd

from grafik_analiz.research import protocol
from grafik_analiz.research.data import load_universe
from grafik_analiz.research.evaluate import compute_signals, load_data
from grafik_analiz.strategies.t2_genis_evren import make_spec

assert protocol.PROTOCOL_VERSION == "2"
for interval, params in [("1d", {"skor": "mom_28"}), ("1d", {"skor": "fon_7", "notr": "beta", "boyut": "ters_oyn"}), ("4h", {"skor": "rev_1", "reb": 1})]:
    spec = make_spec("t2_genis_evren_duman", interval, params)
    t0 = time.time()
    data, funding = load_data(spec)
    t1 = time.time()
    sig = compute_signals(spec, data, funding)
    t2 = time.time()
    print(interval, params, f"yükleme {t1-t0:.1f}s sinyal {t2-t1:.1f}s")
    pos = pd.DataFrame({leg[1]: s for leg, s in sig.items()}).fillna(0.0)
    nl = (pos > 0).sum(axis=1); ns = (pos < 0).sum(axis=1)
    gross = pos.abs().sum(axis=1) / len(spec.legs)
    net = pos.sum(axis=1) / len(spec.legs)
    print("  uzun sayısı:", nl.describe()[["mean", "min", "max"]].round(2).to_dict(), "kısa:", ns.describe()[["mean", "min", "max"]].round(2).to_dict())
    print("  brüt maruziyet ort/maks:", round(gross.mean(), 4), round(gross.max(), 4), "net ort:", round(net.mean(), 5))
    first = pos.index[(pos != 0).any(axis=1)][0]
    print("  ilk pozisyon:", first)
    # Evren uyumu: t'deki hedef sıfır değilse t+1 barının ayında evrende olmalı
    u = load_universe("dev")
    step = pos.index.to_series().diff().median()
    bad = 0
    for t in pos.index[::7]:
        held = pos.columns[pos.loc[t] != 0]
        mth = (t + step).replace(day=1, hour=0, minute=0)
        mem = set(u.loc[u.ay == mth, "sembol"])
        bad += len(set(held) - mem)
    print("  evren dışı tutulan (örneklem):", bad)
