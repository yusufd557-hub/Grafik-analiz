"""Tanı: SOL carry'deki büyük düşüşün kaynağı (dev_train içinde, 2022-11 FTX dönemi).
Yapılandırmalar tarama2'de deftere yazılmıştır. Yalnız 2024 öncesi incelenir."""
import pandas as pd
from grafik_analiz.research import run, DEV_TRAIN_END
from grafik_analiz.strategies.fonlama_carry import make_spec

for iv, p in (("4h", {"n": 1, "giris": 0.5e-4, "cikis": 0.0, "son_neg": False}),
              ("4h", {"n": 1, "giris": 1.5e-4, "cikis": 0.5e-4, "son_neg": False}),
              ("4h", {"n": 3, "giris": 0.5e-4, "cikis": 0.0, "son_neg": False})):
    spec = make_spec("tani", "carry", "SOLUSDT", iv, p)
    res = run(spec, "dev")
    w = spec.leg_weights()
    r = res.returns[res.returns.index < DEV_TRAIN_END]
    eq = (1 + r).cumprod()
    dd = eq / eq.cummax() - 1
    t = dd.idxmin()
    peak = eq[:t].idxmax()
    print(iv, p, "en derin dusus", round(dd.min(), 4), "tepe", peak, "dip", t)
    sl = slice(peak - pd.Timedelta(days=2), t + pd.Timedelta(days=1))
    g = sum(w[l] * res.legs[l].gross for l in spec.legs)
    parca = pd.DataFrame({"fiyat": g, "maliyet": -res.costs, "fonlama": -res.funding, "net": res.returns,
                          "spot_poz": res.legs[("spot", "SOLUSDT")].position, "vadeli_poz": res.legs[("futures", "SOLUSDT")].position})
    seg = parca.loc[(parca.index >= peak) & (parca.index <= t)]
    print("  tepe->dip toplam:", seg[["fiyat", "maliyet", "fonlama", "net"]].sum().round(4).to_dict())
    big = parca.loc[sl]
    big = big[(big.net.abs() > 0.003)]
    print(big.round(4).head(20).to_string())
