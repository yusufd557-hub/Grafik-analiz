"""Tanılama 6 (betimleyici, yalnız eğitim < 2025-01-01; deftere yazılmaz).

Geniş evren: o ay evrende olan her altcoin için altcoin/BTC 4h log yayılımı (1:1).
Şok: son k barlık yayılım hareketi / önceki 500 barlık bar oynaklığı·√k. Büyük şoktan sonra
bir sonraki açılıştan H bar sonrasına dönüş yönünde ortalama yayılım getirisi (bp).
Yalnız indirmesi tamamlanmış semboller (alfabetik bir alt küme olabilir).
"""
import numpy as np
import pandas as pd

from grafik_analiz.research.data import available_symbols, load, load_universe
from grafik_analiz.research.protocol import DEV_TRAIN_END

u = load_universe()
u = u[u["ay"] < DEV_TRAIN_END]
av = set(available_symbols("futures", "4h"))
members = sorted(s for s in u["sembol"].unique() if s in av and s not in ("BTCUSDT",))
btc = load("BTCUSDT", "4h", "futures")
btc = btc[btc.index < DEV_TRAIN_END]
res = {}
n_sym = 0
for sym in members:
    try:
        f = load(sym, "4h", "futures")
    except FileNotFoundError:
        continue
    f = f[f.index < DEV_TRAIN_END]
    if len(f) < 600:
        continue
    n_sym += 1
    idx = f.index.intersection(btc.index)
    lc = np.log(f["close"].reindex(idx)) - np.log(btc["close"].reindex(idx))
    lo = np.log(f["open"].reindex(idx)) - np.log(btc["open"].reindex(idx))
    month = idx.tz_convert("UTC").tz_localize(None).to_period("M").to_timestamp().tz_localize("UTC")
    inuni = pd.Series(month, index=idx).isin(set(u.loc[u["sembol"] == sym, "ay"]))
    for k in (1, 2, 3):
        vol = lc.diff().rolling(500).std().shift(k) * np.sqrt(k)
        z = (lc - lc.shift(k)) / vol
        for H in (1, 2, 3, 6):
            fwd = lo.shift(-1 - H) - lo.shift(-1)
            g = -np.sign(z) * fwd
            for thr in (3.0, 4.0, 5.0):
                ev = (z.abs() > thr) & inuni & g.notna()
                res.setdefault((k, H, thr), []).append(g[ev])
print("sembol sayısı:", n_sym)
for (k, H, thr), parts in sorted(res.items()):
    g = pd.concat(parts)
    yr = g.groupby(g.index.year).mean() * 1e4
    print(f"k{k} H{H} z>{thr}: n{len(g)} ort {g.mean()*1e4:+.1f}bp medyan {g.median()*1e4:+.1f}bp  yıllık "
          + " ".join(f"{y}:{v:+.0f}" for y, v in yr.items()), flush=True)
