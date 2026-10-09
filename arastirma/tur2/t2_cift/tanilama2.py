"""Betimleyici tanılama 2 (yalnız eğitim verisi): büyük yayılım hareketinden sonraki
ortalama yayılım getirisi (1h). Strateji değerlendirmesi değildir; deftere yazılmaz."""
import numpy as np
import pandas as pd

from grafik_analiz.research.data import load
from grafik_analiz.research.protocol import DEV_TRAIN_END

iv = "1h"
o = pd.DataFrame({s: load(s, iv, "futures")["open"] for s in ["BTCUSDT", "ETHUSDT", "SOLUSDT"]})
c = pd.DataFrame({s: load(s, iv, "futures")["close"] for s in ["BTCUSDT", "ETHUSDT", "SOLUSDT"]})
o, c = o[o.index < DEV_TRAIN_END], c[c.index < DEV_TRAIN_END]
lc, lo = np.log(c), np.log(o)
for a, b in [("ETHUSDT", "BTCUSDT"), ("SOLUSDT", "BTCUSDT"), ("SOLUSDT", "ETHUSDT")]:
    s_close = lc[a] - lc[b]
    s_open = lo[a] - lo[b]
    for k in (1, 3, 6):
        mv = s_close - s_close.shift(k)  # son k barlık yayılım hareketi (kapanışta bilinir)
        vol = s_close.diff().rolling(500).std() * np.sqrt(k)
        zz = mv / vol
        res = []
        for H in (1, 3, 6, 24):
            fwd = s_open.shift(-1 - H) - s_open.shift(-1)  # bir sonraki açılıştan H bar sonrasına (yalnız tanılama)
            row = []
            for thr in (2, 3, 4):
                m_up = fwd[zz > thr].mean()
                m_dn = fwd[zz < -thr].mean()
                n = int((zz.abs() > thr).sum())
                # ortalamaya dönüş kazancı: yukarı hareketten sonra kısa, aşağıdan sonra uzun
                gain = (-m_up * (zz > thr).sum() + m_dn * (zz < -thr).sum()) / max(1, n)
                row.append(f"t{thr}:n{n} {gain*1e4:+.1f}bp")
            res.append(f"H{H}: " + " ".join(row))
        print(a[:3] + "/" + b[:3], f"k={k}", " | ".join(res))
