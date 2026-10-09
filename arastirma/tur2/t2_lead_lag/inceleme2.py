"""Eğitim içi inceleme 2 (yalnız defterde ölçülmüş yapılandırmalar; veri 2025-01-01'de kesilir).

inceleme.py'ye ek olarak yön (uzun/kısa) ve yıl × yön kırılımı, aylık pozitiflik oranı.
Kullanım: python inceleme2.py <csv> <ad1> [<ad2> ...]   (ad, 't2_lead_lag_' öneki olmadan da olur)
"""
import json
import sys

import numpy as np
import pandas as pd

from inceleme import incele
from ortak import KLASOR
from grafik_analiz.research.metrics import daily_returns

if __name__ == "__main__":
    tab = pd.read_csv(KLASOR / sys.argv[1])
    for ad in sys.argv[2:]:
        if not ad.startswith("t2_lead_lag_"):
            ad = "t2_lead_lag_" + ad
        row = tab[tab["ad"] == ad].iloc[0]
        res = incele(ad, row["interval"], json.loads(row["params"]))
        t = res.trades.copy()
        t["yil"] = pd.to_datetime(t["entry_time"]).dt.year
        g = t.groupby("direction")["net_return"].agg(["count", "sum", "mean"])
        print("   yön: " + " ".join(f"{int(d):+d}:n={int(r['count'])},toplam={r['sum']:+.3f},ort={r['mean']*1e4:+.1f}bps" for d, r in g.iterrows()))
        gy = t.groupby(["yil", "direction"])["net_return"].sum().unstack()
        print("   yıl×yön toplam: " + " ".join(f"{y}:[" + ",".join(f"{c:+d}:{v:+.3f}" for c, v in r.dropna().items()) + "]" for y, r in gy.iterrows()))
        d = daily_returns(res.returns)
        m = (1 + d).groupby(d.index.to_period("M")).prod() - 1
        aktif = m[m != 0]
        print(f"   aylık: pozitif ay oranı={float((aktif > 0).mean()):.2f} (aktif ay {len(aktif)}), en iyi ay {aktif.max():+.3f} ({aktif.idxmax()}), en kötü ay {aktif.min():+.3f} ({aktif.idxmin()})")
