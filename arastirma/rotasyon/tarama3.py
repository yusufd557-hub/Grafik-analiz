"""3. aşama (yalnız dev_train): oynaklığı eşitlenmiş vadeli uzun/kısa — 5 yapılandırma."""
from grafik_analiz.strategies.rotasyon import FUT3
from ortak import tara

s = []
for L, R in ((21, 1), (21, 7), (28, 1), (28, 7)):
    s.append(("uzun_kisa", "f3", FUT3, dict(lookback=L, skor="getiri", every=R, mod="ls", ma=100, vol_esit=30)))
s.append(("uzun_kisa", "f3", FUT3, dict(lookback=28, skor="karma", every=7, mod="ls", ma=100, vol_esit=30)))
print("yapılandırma:", len(s), flush=True)
tara(s, "tarama3.csv")
