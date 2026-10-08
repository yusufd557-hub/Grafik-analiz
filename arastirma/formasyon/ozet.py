"""Arama özeti: yöntem / aralık / piyasa-yön / tip bazında dev_train dağılımı ve defter sayımları."""
import numpy as np
import pandas as pd

from grafik_analiz.research.ledger import trials
from ortak import table

t = table()
t["yontem"] = t["params"].apply(lambda p: p["yontem"])
t["yon"] = t["params"].apply(lambda p: p.get("yon"))
t["mod"] = t["market"].str[:3] + "-" + t["yon"]
t["filtre"] = t["params"].apply(lambda p: "+".join(k for k in ("trend_n", "hacim_k", "egilim_uyumu", "olcekler") if p.get(k)) or "-")
t["tip"] = t["params"].apply(lambda p: p["tipler"] if isinstance(p["tipler"], str) else "+".join(p["tipler"]))
t["cikis"] = t["params"].apply(lambda p: p.get("cikis"))
print("arama yapılandırması:", len(t), "aşama:", t["tag"].str[:1].value_counts().sort_index().to_dict())

def agg(g):
    return pd.Series({"sayi": len(g), "medyan_sh": np.nanmedian(g["sharpe1"].astype(float)), "en_iyi_sh": np.nanmax(g["sharpe1"].astype(float)),
                      "poz1": (g["ret1"] > 0).mean(), "poz2": (g["ret2"] > 0).mean(), "medyan_islem": g["trades"].median()})

pd.set_option("display.width", 220)
fmt = lambda x: f"{x:.2f}"
print("\n-- yöntem × aralık × mod")
print(t.groupby(["yontem", "interval", "mod"]).apply(agg).to_string(float_format=fmt))
print("\n-- aşama 1b grafik tip grupları (4h ve 1d, hedef/stop, filtresiz)")
g = t[t["tag"] == "1b"]
print(g.pivot_table(index="tip", columns=["interval", "mod"], values="sharpe1").to_string(float_format=fmt))
print("\n-- aşama 1c mum grupları (10 bar)")
g = t[t["tag"] == "1c"]
print(g.pivot_table(index="tip", columns=["interval", "mod"], values="sharpe1").to_string(float_format=fmt))
print("\n-- aşama 1a bütün grafik tipleri")
g = t[t["tag"] == "1a"]
print(g.pivot_table(index=["interval", "mod"], columns=["cikis", "filtre"], values="sharpe1").to_string(float_format=fmt))

led = trials("formasyon")
print("\ndefter satırları:", led.groupby(["pencere", "maliyet_kat"]).size().to_dict())
