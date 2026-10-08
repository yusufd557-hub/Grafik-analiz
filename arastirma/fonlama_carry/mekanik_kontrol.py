"""Mekanik kontrol: pozisyon zamanlaması, fonlama işareti, ilk fonlama kaydından önce pozisyon yok.
Performans ölçüsüne bakılmaz; yalnız dev_train başlangıcındaki birkaç bar incelenir."""
import numpy as np
import pandas as pd
from grafik_analiz.research.evaluate import load_data, compute_signals, backtest
from grafik_analiz.strategies.fonlama_carry import make_spec

for iv in ("4h", "1h", "1d"):
    spec = make_spec("kontrol", "carry", "SEPET3", iv, {"n": 3, "giris": 0.0001, "cikis": 0.0, "son_neg": True})
    data, funding = load_data(spec, "dev")
    sig = compute_signals(spec, data, funding)
    for leg in spec.legs:
        s = sig[leg]
        nz = s[s != 0]
        print(iv, leg, "ilk pozisyon:", nz.index.min(), "ilk fonlama:", funding[leg[1]].index.min(), "deger aralik", s.min(), s.max(), "NaN", int(s.isna().sum()))
    res = backtest(spec, data, funding, sig, 1.0)
    leg = ("futures", "BTCUSDT")
    lr = res.legs[leg]
    # Kısa pozisyonda pozitif fonlama alınır -> fund (ödeme) negatif olmalı
    m = (lr.position < 0)
    fr = lr.funding[m]
    print(iv, "BTC kisa barlarda fonlama odemesi toplam (negatif=alindi):", round(float(fr.sum()), 4), "ilk 2020-01 kayitlari isaret kontrolu")
    print(lr.funding[lr.funding != 0].head(3))
