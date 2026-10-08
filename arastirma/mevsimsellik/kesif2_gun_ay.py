"""Keşif 2 (yalnız dev_train): haftanın günü, hafta sonu, ay dönümü, ay içi gün.

Günlük getiri = 1d barının açılıştan bir sonraki açılışa getirisi (UTC gün).
"""
import numpy as np
import pandas as pd

from ortak import COINS, bar_returns, train_frame, tstat

pd.set_option("display.width", 250)
cells = 0
GUN = ["Pzt", "Sal", "Car", "Per", "Cum", "Cmt", "Paz"]

print("=== Haftanın günü (UTC), ortalama günlük getiri bp; t; pozitif yıl / yıl ===")
for market in ("spot", "futures"):
    for sym in COINS:
        df = train_frame(sym, "1d", market)
        if market == "futures":
            df = df[df.index >= "2020-01-01"]
        r = bar_returns(df)
        out = []
        for d in range(7):
            x = r[r.index.dayofweek == d]
            by = x.groupby(x.index.year).mean()
            out.append(f"{GUN[d]} {x.mean()*1e4:6.1f} (t={tstat(x):5.2f}, {int((by>0).sum())}/{len(by)})")
            cells += 1
        print(f"{market:7s} {sym}: " + " | ".join(out))

print("\n=== Ay dönümü: ayın son k günü ve ilk k günü (UTC gün), ortalama bp / gün ===")
for market in ("spot", "futures"):
    for sym in COINS:
        df = train_frame(sym, "1d", market)
        if market == "futures":
            df = df[df.index >= "2020-01-01"]
        r = bar_returns(df)
        idx = r.index
        dim = idx.days_in_month
        dom = idx.day
        from_end = dom - dim - 1  # son gün = -1
        rel = np.where(dom <= 10, dom, np.where(from_end >= -10, from_end, 0))
        s = pd.Series(r.values, index=rel)
        g = s.groupby(level=0).agg(["mean", "count"])
        g["mean"] *= 1e4
        txt = " ".join(f"{k:+d}:{v:5.1f}" for k, v in g["mean"].items() if k != 0)
        print(f"{market:7s} {sym}: {txt}")
        cells += 20
        # ay dönümü penceresi: son 3 gün + ilk 3 gün
        for a, b in [(-3, 3), (-2, 2), (-5, 5), (-1, 4)]:
            m = ((rel >= a) & (rel < 0)) | ((rel >= 1) & (rel <= b))
            x = r[m]
            other = r[~m]
            by_year = x.groupby(x.index.year).mean() - other.groupby(other.index.year).mean()
            print(f"    pencere [{a},{b}] ort {x.mean()*1e4:5.1f} bp/gün vs diğer {other.mean()*1e4:5.1f}; t(fark)~{(x.mean()-other.mean())/np.sqrt(x.var()/len(x)+other.var()/len(other)):5.2f}; yıllık fark>0: {int((by_year>0).sum())}/{len(by_year)}")

print("\n=== Hafta sonu (Cmt+Paz) vs hafta içi, ortalama bp / gün ===")
for market in ("spot", "futures"):
    for sym in COINS:
        df = train_frame(sym, "1d", market)
        if market == "futures":
            df = df[df.index >= "2020-01-01"]
        r = bar_returns(df)
        we = r.index.dayofweek >= 5
        by = r[we].groupby(r[we].index.year).mean() - r[~we].groupby(r[~we].index.year).mean()
        print(f"{market:7s} {sym}: hafta sonu {r[we].mean()*1e4:5.1f}  hafta içi {r[~we].mean()*1e4:5.1f}  yıllık fark>0 {int((by>0).sum())}/{len(by)}  std hs {r[we].std()*1e2:4.2f}% hi {r[~we].std()*1e2:4.2f}%")
        cells += 1
print("\nincelenen hücre:", cells)
