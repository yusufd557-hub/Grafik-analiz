"""Seçilmiş 1. aşama yapılandırmalarının dev_train yıllık dökümü (dev_valid'e bakılmaz)."""
import pandas as pd
from grafik_analiz.strategies.rotasyon import SPOT3, FUT3
from ortak import yillik

S = [
    ("rotasyon", SPOT3, dict(lookback=28, skor="getiri", top_k=2, every=7, filtre="mutlak")),
    ("rotasyon", SPOT3, dict(lookback=28, skor="getiri", top_k=1, every=7, filtre="mutlak")),
    ("rotasyon", SPOT3, dict(lookback=56, skor="getiri", top_k=1, every=7, filtre="mutlak")),
    ("rotasyon", SPOT3, dict(lookback=14, skor="getiri", top_k=1, every=7, filtre="mutlak")),
    ("rotasyon", SPOT3, dict(lookback=28, skor="getiri", top_k=1, every=7, filtre="yok")),
    ("rotasyon", SPOT3, dict(lookback=28, skor="getiri", top_k=1, every=7, filtre="ma100")),
    ("uzun_kisa", FUT3, dict(lookback=28, skor="getiri", every=1, mod="ls", ma=100)),
    ("uzun_kisa", FUT3, dict(lookback=28, skor="getiri", every=7, mod="ls", ma=100)),
    ("uzun_kisa", FUT3, dict(lookback=14, skor="getiri", every=7, mod="ls", ma=100)),
    ("oran", (("futures", "SOLUSDT"), ("futures", "BTCUSDT")), dict(alt="SOLUSDT", baz="BTCUSDT", n=50, mod="yukari", every=1)),
    ("oran", (("futures", "SOLUSDT"), ("futures", "BTCUSDT")), dict(alt="SOLUSDT", baz="BTCUSDT", n=50, mod="ls", every=1)),
    ("oran", (("futures", "ETHUSDT"), ("futures", "BTCUSDT")), dict(alt="ETHUSDT", baz="BTCUSDT", n=20, mod="yukari", every=1)),
]
rows = {}
for kind, legs, p in S:
    key = kind + " " + " ".join(f"{k}={v}" for k, v in p.items() if k not in ("ma",))
    rows[key] = yillik(kind, legs, p)
pd.set_option("display.width", 250)
print(pd.DataFrame(rows).T.round(3).to_string())
