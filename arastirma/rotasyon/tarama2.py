"""2. aşama (yalnız dev_train): kontroller ve 1. aşamadaki sağlam bölgelerin çevresi.

- Kontrol: yalnız zaman serisi momentumu (top_k=3 + mutlak filtre, kesitsel seçim yok) — 3
- Kontrol: SOL'suz evren (BTC/ETH spot rotasyon) — 3
- Günlük filtre (haftalık dengeleme + her gün mutlak filtre ile çıkış) — 6
- Karma skor (L/2, L, 2L) spot — 4
- Vadeli uzun/kısa: L 21/42, her 3 gün, karma skor, SOL'suz kontrol — 4 + 3 + 4 + 3
"""
import itertools

from grafik_analiz.strategies.rotasyon import SPOT2, SPOT3, FUT2, FUT3
from ortak import tara

s = []
for L in (14, 28, 56):
    s.append(("rotasyon", "s3", SPOT3, dict(lookback=L, skor="getiri", top_k=3, every=7, filtre="mutlak")))
for L in (14, 28, 56):
    s.append(("rotasyon", "s2", SPOT2, dict(lookback=L, skor="getiri", top_k=1, every=7, filtre="mutlak")))
for L, k in itertools.product((14, 28, 56), (1, 2)):
    s.append(("rotasyon", "s3", SPOT3, dict(lookback=L, skor="getiri", top_k=k, every=7, filtre="mutlak", gunluk_filtre=True)))
for L, k in itertools.product((14, 28), (1, 2)):
    s.append(("rotasyon", "s3", SPOT3, dict(lookback=L, skor="karma", top_k=k, every=7, filtre="mutlak")))
for L, R in itertools.product((21, 42), (1, 7)):
    s.append(("uzun_kisa", "f3", FUT3, dict(lookback=L, skor="getiri", every=R, mod="ls", ma=100)))
for L in (14, 28, 56):
    s.append(("uzun_kisa", "f3", FUT3, dict(lookback=L, skor="getiri", every=3, mod="ls", ma=100)))
for L, R in itertools.product((14, 28), (1, 7)):
    s.append(("uzun_kisa", "f3", FUT3, dict(lookback=L, skor="karma", every=R, mod="ls", ma=100)))
for L in (14, 28, 56):
    s.append(("uzun_kisa", "f2", FUT2, dict(lookback=L, skor="getiri", every=7, mod="ls", ma=100)))
print("yapılandırma:", len(s), flush=True)
tara(s, "tarama2.csv")
