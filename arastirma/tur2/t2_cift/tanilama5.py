"""Tanılama 5 (betimleyici, yalnız eğitim verisi < 2025-01-01; deftere yazılmaz).

Şok olaylarında (1h, bir, son k barlık yayılım hareketi / önceki 500 bar oynaklığı) açık
pozisyon (OI) değişiminin sonraki dönüşle ilişkisi. OI ölçümü yalnız bar kapanışından önce
(< bar açılışı + 1 saat) alınır. Olay kümesi 2021-12 sonrası (ETH/SOL ölçüleri o tarihte başlıyor).
Getiri: bir sonraki açılıştan H bar sonraki açılışa ortalamaya dönüş yönünde yayılım getirisi.
"""
import numpy as np
import pandas as pd

from grafik_analiz.research.data import load, load_metrics
from grafik_analiz.research.protocol import DEV_TRAIN_END

iv = "1h"
S = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
o = pd.DataFrame({s: load(s, iv, "futures")["open"] for s in S})
c = pd.DataFrame({s: load(s, iv, "futures")["close"] for s in S})
o, c = o[o.index < DEV_TRAIN_END], c[c.index < DEV_TRAIN_END]
oi = {}
for s in S:
    m = load_metrics(s)["oi_usdt"]
    m = m[m.index < DEV_TRAIN_END]
    key = pd.DataFrame({"t": c.index + pd.Timedelta(hours=1)})
    j = pd.merge_asof(key, m.rename("oi").reset_index().rename(columns={"zaman": "t"}), on="t",
                      direction="backward", allow_exact_matches=False)
    oi[s] = pd.Series(j["oi"].to_numpy(), index=c.index)
oi = pd.DataFrame(oi)
lc, lo = np.log(c), np.log(o)
for a, b in [("SOLUSDT", "BTCUSDT"), ("SOLUSDT", "ETHUSDT"), ("ETHUSDT", "BTCUSDT")]:
    s_c = lc[a] - lc[b]
    s_o = lo[a] - lo[b]
    for k in (3, 6):
        vol = s_c.diff().rolling(500).std().shift(k) * np.sqrt(k)
        z = (s_c - s_c.shift(k)) / vol
        doi_a = np.log(oi[a] / oi[a].shift(k))
        doi_b = np.log(oi[b] / oi[b].shift(k))
        for H in (3, 6):
            fwd = s_o.shift(-1 - H) - s_o.shift(-1)
            gain = -np.sign(z) * fwd  # dönüş yönünde
            for thr in (3.0, 4.0):
                ev = (z.abs() > thr) & doi_a.notna() & doi_b.notna() & (z.index >= "2021-12-01")
                g = gain[ev]
                da, db = doi_a[ev], doi_b[ev]
                both = (da + db) / 2
                parts = {
                    "hepsi": g,
                    "oiA<-1%": g[da < -0.01], "oiA>+1%": g[da > 0.01],
                    "ort<-1%": g[both < -0.01], "ort>+1%": g[both > 0.01],
                    "ort<0": g[both < 0], "ort>=0": g[both >= 0],
                }
                txt = " ".join(f"{n}:n{len(v)} {v.mean()*1e4:+.0f}bp" for n, v in parts.items())
                print(f"{a[:3]}/{b[:3]} k{k} H{H} z>{thr}: {txt}", flush=True)
