"""Betimleyici tanılama (yalnız eğitim verisi, 31.12.2024 öncesi): yayılım getirilerinin
otokorelasyonu ve varyans oranları. Strateji değerlendirmesi değildir; deftere yazılmaz."""
import numpy as np
import pandas as pd

from grafik_analiz.research.data import load
from grafik_analiz.research.protocol import DEV_TRAIN_END

for iv in ["1h", "4h"]:
    c = {s: load(s, iv, "futures")["close"] for s in ["BTCUSDT", "ETHUSDT", "SOLUSDT"]}
    c = pd.DataFrame(c)
    c = c[c.index < DEV_TRAIN_END]
    lp = np.log(c)
    for a, b in [("ETHUSDT", "BTCUSDT"), ("SOLUSDT", "BTCUSDT"), ("SOLUSDT", "ETHUSDT")]:
        s = (lp[a] - lp[b]).dropna()
        r = s.diff().dropna()
        ac = [r.autocorr(k) for k in (1, 2, 3, 6, 12)]
        vr = {}
        for k in ([6, 24, 72, 168, 500] if iv == "1h" else [6, 18, 42, 90, 180]):
            rk = s.diff(k).dropna()
            vr[k] = rk.var() / (k * r.var())
        print(iv, a[:3] + "/" + b[:3], "otokor:", np.round(ac, 3), "VR:", {k: round(v, 2) for k, v in vr.items()})
    # yıllara göre VR (orta ufuk)
    k = 72 if iv == "1h" else 18
    for a, b in [("ETHUSDT", "BTCUSDT"), ("SOLUSDT", "BTCUSDT"), ("SOLUSDT", "ETHUSDT")]:
        s = (lp[a] - lp[b]).dropna()
        out = {}
        for y, g in s.groupby(s.index.year):
            r = g.diff().dropna()
            out[y] = round(g.diff(k).dropna().var() / (k * r.var()), 2)
        print("  yıllık VR", k, a[:3] + "/" + b[:3], out)
