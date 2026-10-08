"""Keşif 1 (yalnız dev_train): UTC saat, haftanın günü, ay dönümü etkileri.

Betimseldir; strateji değerlendirmesi değildir. İncelenen hücre sayısı
raporda deneme sayısına eklenir (muhafazakâr Deflated Sharpe).
"""
import numpy as np
import pandas as pd

from ortak import COINS, bar_returns, train_frame, tstat

pd.set_option("display.width", 250)
pd.set_option("display.max_columns", 40)

cells = 0
rows = []
for market in ("spot", "futures"):
    for sym in COINS:
        df = train_frame(sym, "1h", market)
        r = bar_returns(df)
        hour = r.index.hour
        year = r.index.year
        for h in range(24):
            x = r[hour == h]
            by_year = x.groupby(x.index.year).mean()
            rows.append({
                "market": market, "sym": sym, "hour": h, "n": len(x),
                "mean_bp": x.mean() * 1e4, "t": tstat(x),
                "pos_years": int((by_year > 0).sum()), "years": len(by_year),
                **{f"y{y}": v * 1e4 for y, v in by_year.items()},
            })
            cells += 1
tab = pd.DataFrame(rows)
print("=== Saatlik (UTC) ortalama getiri, baz puan; t; pozitif yıl sayısı ===")
for (m, s), g in tab.groupby(["market", "sym"]):
    print(f"\n-- {m} {s}")
    print(g.drop(columns=["market", "sym"]).round(2).to_string(index=False))

# Üç coin havuzlu (spot), coin-eşit ağırlık ortalama
print("\n=== Spot, 3 coin ortalaması (her saat) ===")
piv = tab[tab.market == "spot"].pivot(index="hour", columns="sym", values="mean_bp")
piv["ort"] = piv.mean(axis=1)
pt = tab[tab.market == "spot"].pivot(index="hour", columns="sym", values="t")
piv = piv.join(pt, rsuffix="_t")
print(piv.round(2).to_string())
print("\nincelenen saat hücresi:", cells)
tab.to_csv("kesif1_saat.csv", index=False)
