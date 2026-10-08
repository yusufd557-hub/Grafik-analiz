"""Dondurma SONRASI betimsel tanı (hiçbir parametre değişmez, deftere yazılmaz).

- dev_valid'de ay dönümü penceresi (a=4, b=5) içi / dışı günlük brüt getiri, coin bazında
- dev_valid'de her ay dönümünün PORT3 penceresi getirisi
- bilgi amaçlı: yalnız ay dönümü denemelerinin Sharpe varyansıyla dev_train DSR'si
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd

from grafik_analiz.research import DEV_TRAIN_END, deflated_sharpe, load
from grafik_analiz.research.ledger import trials
from grafik_analiz.strategies.mevsimsellik import _rel_day

here = Path(__file__).resolve().parent
COINS = ("BTCUSDT", "ETHUSDT", "SOLUSDT")
print("=== dev_valid: pencere (son 4 + ilk 5 gün) içi/dışı ortalama günlük brüt getiri (bp), spot ===")
win = {}
for c in COINS:
    df = load(c, "1d", "spot", scope="dev")
    r = (df["open"].shift(-1) / df["open"] - 1).fillna(df["close"] / df["open"] - 1)
    for name, sl in (("dev_train", r[r.index < DEV_TRAIN_END]), ("dev_valid", r[r.index >= DEV_TRAIN_END])):
        rel = _rel_day(sl.index)
        m = ((rel >= -4) & (rel < 0)) | ((rel >= 1) & (rel <= 5))
        print(f"{c} {name}: içi {sl[m].mean()*1e4:6.1f}  dışı {sl[~m].mean()*1e4:6.1f}  (gün {m.sum()}/{(~m).sum()})")
        if name == "dev_valid":
            key = np.where(rel < 0, (sl.index + pd.offsets.MonthBegin(1)).strftime("%Y-%m"), sl.index.strftime("%Y-%m"))
            s = pd.Series(np.log1p(sl[m].values), index=key[m])
            win[c] = np.expm1(s.groupby(level=0).sum())
w = pd.DataFrame(win)
w["PORT3"] = w.mean(axis=1)
print("\n=== dev_valid: her ay dönümünün pencere getirisi (brüt, %) ===")
print((w * 100).round(1).to_string())
print(f"pozitif ay dönümü (PORT3): {(w['PORT3'] > 0).sum()}/{len(w)}; medyan {w['PORT3'].median()*100:.2f}%")

t = trials("mevsimsellik")
tr = t[(t.pencere == "dev_train") & (t.maliyet_kat == 1.0)]
tom = tr[tr.strateji.str.startswith("tom")]
sh = np.array([r["sharpe"] for r in tom.olcu], dtype=float)
var = float(np.var(sh, ddof=1))
res = json.loads((here / "dondurulmus_sonuclar.json").read_text(encoding="utf-8"))
print(f"\nYalnız ay dönümü denemeleri: n={len(tom)}, Sharpe std {np.sqrt(var):.3f}")
for name, r in res.items():
    tt = r["metrics"]["dev_train"]["1.0"]
    d = deflated_sharpe(tt["sharpe"], int(tt["days"]) + 1, len(tom), var, tt["skew"], tt["kurtosis"])
    print(f"  {name}: dev_train SR {tt['sharpe']:.2f} -> DSR (yalnız ay dönümü varyansı, N={len(tom)}) {d:.3f}")
