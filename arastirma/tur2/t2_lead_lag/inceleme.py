"""Eğitim içi inceleme (yalnız defterde ölçülmüş yapılandırmalar; veri 2025-01-01'de kesilir).

Yıllık net getiri, yıllık işlem sayısı, en iyi işlemler ve en iyi 5/10 işlem
çıkarılınca kalan getiri. Kullanım: python inceleme.py <csv> <ad1> [<ad2> ...]
"""
import json
import sys

import numpy as np
import pandas as pd

from ortak import END, KLASOR, make_spec
from grafik_analiz.research.evaluate import backtest, compute_signals, load_data
from grafik_analiz.research.metrics import daily_returns


def incele(ad, iv, params, mult=1.0):
    spec = make_spec(ad, iv, **params)
    data, funding = load_data(spec, "dev")
    data = {leg: f[f["close_time"] < END] for leg, f in data.items()}
    funding = {s: f[f.index < END] for s, f in funding.items()}
    sig = compute_signals(spec, data, funding)
    res = backtest(spec, data, funding, sig, mult)
    d = daily_returns(res.returns)
    yil = (1 + d).groupby(d.index.year).prod() - 1
    t = res.trades
    ny = t.groupby(pd.to_datetime(t["entry_time"]).dt.year).size()
    tot = float((1 + res.returns).prod() - 1)
    srt = t.sort_values("net_return", ascending=False)
    lr = np.log1p(t["net_return"].astype(float))
    wo5 = float(np.expm1(np.log1p(tot) - np.log1p(srt["net_return"].head(5)).sum()))
    wo10 = float(np.expm1(np.log1p(tot) - np.log1p(srt["net_return"].head(10)).sum()))
    print(f"== {spec.name} x{mult}: toplam={tot:+.4f} islem={len(t)} ilk5_cikinca={wo5:+.4f} ilk10_cikinca={wo10:+.4f}")
    print("   yillik: " + " ".join(f"{y}:{v:+.3f}(n={ny.get(y, 0)})" for y, v in yil.items()))
    by_leg = t.groupby("leg")["net_return"].agg(["count", "sum"])
    print("   bacak: " + " ".join(f"{k}:n={int(r['count'])},toplam={r['sum']:+.3f}" for k, r in by_leg.iterrows()))
    print("   en iyi 5: " + "; ".join(f"{str(r.entry_time)[:16]} {r.leg.split(':')[1][:3]} {r.direction:+d} {r.net_return:+.4f}" for r in srt.head(5).itertuples()))
    print("   en kötü 3: " + "; ".join(f"{str(r.entry_time)[:16]} {r.leg.split(':')[1][:3]} {r.direction:+d} {r.net_return:+.4f}" for r in srt.tail(3).itertuples()))
    return res


if __name__ == "__main__":
    tab = pd.read_csv(KLASOR / sys.argv[1])
    for ad in sys.argv[2:]:
        row = tab[tab["ad"] == ad].iloc[0]
        incele(ad, row["interval"], json.loads(row["params"]))
