"""Aşama 0 tanılama 3: spot–vadeli ve prim endeksi öncü–izleyen ilişkisi.
Yalnız eğitim verisi (< 2025-01-01). Kayan istatistikler geriye dönük.
"""
import numpy as np
import pandas as pd

from grafik_analiz.research import protocol
from grafik_analiz.research.data import load, load_premium

assert protocol.PROTOCOL_VERSION == "2"
END = protocol.DEV_TRAIN_END
COINS = ("BTCUSDT", "ETHUSDT", "SOLUSDT")

for interval, win in (("5m", 288), ("15m", 96)):
    fut = {s: load(s, interval, "futures", "dev") for s in COINS}
    spot = {s: load(s, interval, "spot", "dev") for s in COINS}
    for s in COINS:
        fut[s] = fut[s][fut[s].index < END]
        spot[s] = spot[s][spot[s].index < END].reindex(fut[s].index)
    print(f"=== {interval}: spot getirisi − vadeli getirisi (aynı bar) → vadeli sonraki getiri")
    for src in COINS:
        for dst in COINS:
            rs = np.log(spot[src]["close"]).diff()
            rf = np.log(fut[src]["close"]).diff()
            d = (rs - rf)
            z = d / d.rolling(win).std().shift(1)
            lo = np.log(fut[dst]["open"]).reindex(z.index)
            out = []
            for h in (1, 3, 12):
                fwd = lo.shift(-1 - h) - lo.shift(-1)
                for thr in (2.0, 3.0, 4.0):
                    m = z.abs() > thr
                    v = (np.sign(z[m]) * fwd[m]).dropna()
                    yrs = (np.sign(z[m]) * fwd[m]).groupby(z[m].index.year).mean() * 1e4
                    out.append(f"h={h} z>{thr}: n={len(v)} {v.mean()*1e4:+.2f}bps [{' '.join(f'{y}:{a:+.1f}' for y,a in yrs.items())}]")
            print(f"  spot−vadeli {src[:3]} → vadeli {dst[:3]}: " + " | ".join(out[:3]))
            print("      " + " | ".join(out[3:6]))
            print("      " + " | ".join(out[6:]))

print("=== prim endeksi (1h) kapanış z-skoru → vadeli sonraki getiri (1h)")
for s in COINS:
    p = load_premium(s, "1h")
    p = p[p.index < END]
    f = load(s, "1h", "futures", "dev")
    f = f[f.index < END]
    prem = p["close"].reindex(f.index)
    for win in (24, 168):
        z = (prem - prem.rolling(win).mean().shift(1)) / prem.rolling(win).std().shift(1)
        dz = prem.diff() / prem.diff().rolling(win).std().shift(1)
        lo = np.log(f["open"])
        res = []
        for name, zz in (("düzey", z), ("değişim", dz)):
            for h in (1, 4, 8):
                fwd = lo.shift(-1 - h) - lo.shift(-1)
                for thr in (2.0, 3.0):
                    m = zz.abs() > thr
                    v = (np.sign(zz[m]) * fwd[m]).dropna()
                    yrs = (np.sign(zz[m]) * fwd[m]).groupby(zz[m].index.year).mean() * 1e4
                    res.append(f"{name} h={h} z>{thr}: n={len(v)} {v.mean()*1e4:+.2f}bps [{' '.join(f'{y}:{a:+.0f}' for y,a in yrs.items())}]")
        print(f"  {s[:3]} win={win}:")
        for r_ in res:
            print("     ", r_)
