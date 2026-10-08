"""Pencere seçimi kuralı (dev_valid görülmeden önce yazıldı):
a, b ∈ {2..5} (iç noktalar) arasından, 3×3 komşuluğunun dev_train 1× Sharpe ortalaması
(spot ve vadeli PORT3 ortalaması) en yüksek olan seçilir. Ayrıca yıllık pozitiflik sayılır."""
import json

import numpy as np
import pandas as pd

from grafik_analiz.strategies.mevsimsellik import make_spec
from ortak import SONUC, yillik

rows = [json.loads(l) for l in SONUC.read_text().splitlines() if l.strip()]
sh = {}
for r in rows:
    n = r["name"]
    if n.startswith("tom_1d_") and "_PORT3_" in n and r["params"].get("yon", "uzun") == "uzun":
        m = "spot" if "_spot_" in n else "futures"
        a, b = r["params"]["a"], r["params"]["b"]
        if a >= 1 and b >= 1:
            sh[(m, a, b)] = r["sharpe_1x"]
tab = {}
for a in range(2, 6):
    for b in range(2, 6):
        vals = []
        for m in ("spot", "futures"):
            nb = [sh[(m, a + i, b + j)] for i in (-1, 0, 1) for j in (-1, 0, 1)]
            vals.append(np.mean(nb))
        tab[(a, b)] = (np.mean(vals), vals[0], vals[1], sh[("spot", a, b)], sh[("futures", a, b)])
df = pd.DataFrame(tab, index=["komsu_ort", "komsu_spot", "komsu_vadeli", "spot", "vadeli"]).T.sort_values("komsu_ort", ascending=False)
print(df.round(3).to_string())
best = df.index[0]
print("seçilen (a, b):", best)
for a, b in [best, (3, 3), (4, 3), (3, 4)]:
    for m, tag in (("spot", "spot"), ("futures", "fut")):
        spec = make_spec(f"tom_1d_{tag}_PORT3_a{a}_b{b}", "1d", m, "PORT3", {"yontem": "ay_donumu", "a": a, "b": b})
        y = yillik(spec)
        y2 = yillik(spec, 2.0)
        print(f"  {spec.name:28s} yıllık>0 1x {(y > 0).sum()}/{(y != 0).sum()}  2x {(y2 > 0).sum()}/{(y2 != 0).sum()} : " + " ".join(f"{k}:{v:+.3f}" for k, v in y.items()))
