"""1. aşama taraması (yalnız dev_train, 1× ve 2× maliyet).

A) Spot rotasyon BTC/ETH/SOL: L × skor × top_k × yeniden dengeleme × filtre = 5×2×2×2×3 = 120
B) Vadeli uzun/kısa BTC/ETH/SOL: L × skor × yeniden dengeleme × mod = 5×2×2×2 = 40
C) Vadeli oran trendi: çift × n × mod × yeniden dengeleme = 3×4×2×2 = 48
"""
import itertools

from grafik_analiz.strategies.rotasyon import SPOT3, FUT3
from ortak import tara

satirlar = []
for L, skor, k, R, filtre in itertools.product((7, 14, 28, 56, 91), ("getiri", "risk"), (1, 2), (1, 7), ("yok", "mutlak", "ma100")):
    satirlar.append(("rotasyon", "s3", SPOT3, dict(lookback=L, skor=skor, top_k=k, every=R, filtre=filtre)))
for L, skor, R, mod in itertools.product((7, 14, 28, 56, 91), ("getiri", "risk"), (1, 7), ("ls", "ls_trend")):
    satirlar.append(("uzun_kisa", "f3", FUT3, dict(lookback=L, skor=skor, every=R, mod=mod, ma=100)))
for (alt, baz), n, mod, R in itertools.product((("ETHUSDT", "BTCUSDT"), ("SOLUSDT", "BTCUSDT"), ("SOLUSDT", "ETHUSDT")), (20, 50, 100, 200), ("ls", "yukari"), (1, 7)):
    legs = (("futures", alt), ("futures", baz))
    satirlar.append(("oran", "f2", legs, dict(alt=alt, baz=baz, n=n, mod=mod, every=R)))
print("yapılandırma:", len(satirlar), flush=True)
tara(satirlar, "tarama1.csv")
