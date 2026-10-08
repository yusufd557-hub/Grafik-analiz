"""Keşif 3 (yalnız dev_train): fonlama anları çevresi ve New York saati.

Fonlama: 00/08/16 UTC. Bir önceki (bilinen) fonlama oranının işaretine/büyüklüğüne
göre, fonlamadan önceki ve sonraki saatlerin ortalama getirisi.
New York saati: America/New_York'a çevrilmiş saat (yaz saati dahil).
"""
import numpy as np
import pandas as pd

from ortak import COINS, bar_returns, train_frame, train_funding, tstat

pd.set_option("display.width", 250)
cells = 0
print("=== Fonlama anına göre saat konumu (vadeli 1h): k = fonlamaya göre bar başlangıcı (saat) ===")
print("    'son' = bu bardan önce bilinen son fonlama oranı (zaman damgası <= bar açılışı)")
for sym in COINS:
    df = train_frame(sym, "1h", "futures")
    r = bar_returns(df)
    f = train_funding(sym)["funding_rate"]
    # bar açılışında bilinen son fonlama (damga <= açılış zamanı; açılış = önceki barın kapanışı)
    last = f.reindex(r.index.union(f.index)).ffill().reindex(r.index)
    pos8 = (r.index.hour % 8)  # 0 => fonlama anında açılan bar; 7 => fonlamadan hemen önceki bar
    rows = []
    for k in range(8):
        m = pos8 == k
        x = r[m]
        hi = x[last[m] > 0.0003]
        lo = x[last[m] < 0]
        rows.append(f"k={k}: tum {x.mean()*1e4:5.2f}(t{tstat(x):5.2f}) yuksek+ {hi.mean()*1e4:6.2f}(n{len(hi)},t{tstat(hi):5.2f}) negatif {lo.mean()*1e4:6.2f}(n{len(lo)},t{tstat(lo):5.2f})")
        cells += 3
    print(f"-- {sym}")
    print("\n".join("   " + s for s in rows))

print("\n=== New York saatine göre (spot 1h), ortalama bp, t ===")
for sym in COINS[:2]:
    df = train_frame(sym, "1h", "spot")
    r = bar_returns(df)
    ny = r.index.tz_convert("America/New_York")
    wk = ny.dayofweek < 5
    out = []
    for h in range(24):
        x = r[(ny.hour == h) & wk]
        out.append(f"{h:02d}:{x.mean()*1e4:5.1f}({tstat(x):4.1f})")
        cells += 1
    print(f"{sym} (hafta içi, NY saati): " + " ".join(out))

print("\n=== ABD seansı (NY 09:30-16:00, hafta içi) ve gece (16:00-09:30) toplamları, 15m spot ===")
for sym in COINS[:2]:
    df = train_frame(sym, "15m", "spot")
    r = np.log1p(bar_returns(df))
    ny = r.index.tz_convert("America/New_York")
    mins = ny.hour * 60 + ny.minute
    day = ny.normalize()
    sess = (mins >= 570) & (mins < 960) & (ny.dayofweek < 5)
    first = (mins >= 570) & (mins < 630) & (ny.dayofweek < 5)
    pre = (mins >= 510) & (mins < 570) & (ny.dayofweek < 5)
    for name, m in [("seans", sess), ("ilk saat 9:30-10:30", first), ("açılış öncesi 8:30-9:30", pre)]:
        s = r[m].groupby(day[m]).sum()
        by = s.groupby(s.index.year).mean()
        print(f"{sym} {name}: gunluk toplam ort {s.mean()*1e4:6.2f} bp t={tstat(s):5.2f} yillar>0 {int((by>0).sum())}/{len(by)}")
        cells += 1
print("\nincelenen hücre:", cells)
