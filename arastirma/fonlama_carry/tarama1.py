"""1. aşama: nakit-carry (spot uzun + vadeli kısa), 4s bar. Yalnız dev_train, 1× ve 2× maliyet.

Evren: BTC, ETH, SOL, üç coinlik sepet. Her evren için:
- her zaman pozisyonda (n=0) taban çizgisi,
- n ∈ {1,3,7,14} gün ortalama fonlama; (giriş, çıkış) eşikleri (8 saatlik eşdeğer oran)
  {(0,0), (1e-4,0), (1e-4,5e-5), (2e-4,0), (2e-4,1e-4), (3e-4,1e-4)}; son kayıt negatifse çıkış {hayır, evet}.
"""
from ortak import tara

satirlar = []
for u in ("BTCUSDT", "ETHUSDT", "SOLUSDT", "SEPET3"):
    satirlar.append(("carry", u, "4h", {"n": 0, "giris": 0.0, "cikis": 0.0, "son_neg": False}))
    for n in (1, 3, 7, 14):
        for giris, cikis in ((0.0, 0.0), (1e-4, 0.0), (1e-4, 5e-5), (2e-4, 0.0), (2e-4, 1e-4), (3e-4, 1e-4)):
            for sn in (False, True):
                satirlar.append(("carry", u, "4h", {"n": n, "giris": giris, "cikis": cikis, "son_neg": sn}))
tara(satirlar, "tarama1.csv")
