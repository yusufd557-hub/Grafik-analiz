"""Modelin hangi koşullarda alım kararı verdiği (yalnız dev_train satırları; getiri hesaplanmaz).

Karar barlarında (edge > eşik) özelliklerin ortalaması / bütün barlardaki ortalama, saat ve
oynaklık sırası dağılımı.
"""
import json
import sys

import numpy as np
import pandas as pd

from grafik_analiz.research.evaluate import load_data
from grafik_analiz.strategies import makine_ogrenmesi as mo

END = pd.Timestamp("2024-01-01", tz="UTC")
interval, market, params = json.loads(sys.argv[1])
spec = mo.make_spec("tani", interval, market, **params)
p = spec.params
data, funding = load_data(spec, "dev")
edges = mo.cached_edges(data, funding, p)
rows = []
for leg, df in data.items():
    if p.get("egitim") == "spot" and leg[0] == "spot" and market == "futures":
        continue
    X = mo.leg_features(df, p["ozellik"], funding.get(leg[1]), None)
    e = edges[leg].reindex(df.index)
    thr = p["k"] * mo.RT_COST[leg[0]]
    m = (df.index < END) & e.notna()
    X = X[m].copy()
    X["karar"] = (e[m] > thr).astype(int)
    X["saat"] = X.index.hour
    X["coin"] = leg[1][:3]
    X["edge"] = e[m]
    rows.append(X)
A = pd.concat(rows)
print("karar oranı:", A["karar"].mean().round(4), "| coin bazında:", A.groupby("coin")["karar"].mean().round(4).to_dict())
cols = ["z1", "z4", "z16", "z64", "vol_sira", "vol_oran_s", "rsi", "bb_pos", "ema20", "ema200", "hacim20", "alici", "kapanis_yeri", "tepe_dusus", "dc20"]
g = A.groupby("karar")[cols].mean().T
g.columns = ["karar_yok", "alim"]
print(g.round(3).to_string())
print("saat dağılımı (alım oranı):", A.groupby("saat")["karar"].mean().round(3).to_dict())
A["vol_q"] = pd.qcut(A["vol_sira"], 5, labels=False)
print("oynaklık sırası beşte birlik dilimine göre alım oranı:", A.groupby("vol_q")["karar"].mean().round(3).to_dict())
A["z4_q"] = pd.qcut(A["z4"], 5, labels=False)
print("z4 beşte birlik dilimine göre alım oranı:", A.groupby("z4_q")["karar"].mean().round(3).to_dict())
