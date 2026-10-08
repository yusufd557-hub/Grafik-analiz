"""Kısa liste: dev_train yıllık getiri ve yıllık işlem sayısı (dev_valid'e bakılmaz)."""
import pandas as pd
from grafik_analiz.strategies.rotasyon import SPOT3, FUT3
from ortak import yillik_islem

SB = (("futures", "SOLUSDT"), ("futures", "BTCUSDT"))
SE = (("futures", "SOLUSDT"), ("futures", "ETHUSDT"))
S = {
    "S1 spot karma L28 k1 R7": ("rotasyon", SPOT3, dict(lookback=28, skor="karma", top_k=1, every=7, filtre="mutlak")),
    "S2 spot karma L28 k2 R7": ("rotasyon", SPOT3, dict(lookback=28, skor="karma", top_k=2, every=7, filtre="mutlak")),
    "S3 spot L14 k1 R7 gunluk": ("rotasyon", SPOT3, dict(lookback=14, skor="getiri", top_k=1, every=7, filtre="mutlak", gunluk_filtre=True)),
    "S4 spot L28 k2 R7 gunluk": ("rotasyon", SPOT3, dict(lookback=28, skor="getiri", top_k=2, every=7, filtre="mutlak", gunluk_filtre=True)),
    "S5 spot L28 k1 R1": ("rotasyon", SPOT3, dict(lookback=28, skor="getiri", top_k=1, every=1, filtre="mutlak")),
    "K3 spot TS-kontrol L28": ("rotasyon", SPOT3, dict(lookback=28, skor="getiri", top_k=3, every=7, filtre="mutlak")),
    "L1 LS L21 R1 vol30": ("uzun_kisa", FUT3, dict(lookback=21, skor="getiri", every=1, mod="ls", ma=100, vol_esit=30)),
    "L2 LS L28 R1 vol30": ("uzun_kisa", FUT3, dict(lookback=28, skor="getiri", every=1, mod="ls", ma=100, vol_esit=30)),
    "L3 LS karma L28 R7": ("uzun_kisa", FUT3, dict(lookback=28, skor="karma", every=7, mod="ls", ma=100)),
    "L4 LS L21 R7": ("uzun_kisa", FUT3, dict(lookback=21, skor="getiri", every=7, mod="ls", ma=100)),
    "L5 LS karma L14 R7": ("uzun_kisa", FUT3, dict(lookback=14, skor="karma", every=7, mod="ls", ma=100)),
    "L6 LS L21 R7 vol30": ("uzun_kisa", FUT3, dict(lookback=21, skor="getiri", every=7, mod="ls", ma=100, vol_esit=30)),
    "O1 SOLBTC n50 yukari R1": ("oran", SB, dict(alt="SOLUSDT", baz="BTCUSDT", n=50, mod="yukari", every=1)),
    "O2 SOLETH n50 yukari R1": ("oran", SE, dict(alt="SOLUSDT", baz="ETHUSDT", n=50, mod="yukari", every=1)),
}
g, t = {}, {}
for k, (kind, legs, p) in S.items():
    g[k], t[k] = yillik_islem(kind, legs, p)
pd.set_option("display.width", 250)
print("yıllık net getiri (dev_train)")
print(pd.DataFrame(g).T.round(3).to_string())
print("\nyıllık işlem sayısı (dev_train)")
print(pd.DataFrame(t).T.fillna(0).astype(int).to_string())
