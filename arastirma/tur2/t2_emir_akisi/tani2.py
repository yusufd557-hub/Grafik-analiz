"""Tanı 2 (yalnız dev_train): defterde zaten olan aday yapılandırmaların yoğunlaşma,
yön ve karşılıklı korelasyon tanısı. run() ile yeniden hesaplanır, çıktı DEV_TRAIN_END
öncesine kesilir; dev_valid'e bakılmaz, deftere yazılmaz.
"""
import numpy as np
import pandas as pd

from grafik_analiz.research.evaluate import run
from grafik_analiz.research.metrics import daily_returns
from grafik_analiz.research.protocol import DEV_TRAIN_END
from grafik_analiz.strategies import t2_emir_akisi as ea

C = {
    "uyum5m": ("futures", "5m", dict(kind="uyumsuzluk", n=72, L=2000, k=3.5, mode="devam", hold=12)),
    "uyum15m": ("futures", "15m", dict(kind="uyumsuzluk", n=24, L=2000, k=3.5, mode="devam", hold=2)),
    "uyum5m_n36": ("futures", "5m", dict(kind="uyumsuzluk", n=36, L=2000, k=3.5, mode="devam", hold=24)),
    "artik15m": ("futures", "15m", dict(kind="akis_artik", n=12, L=2000, k=3.5, mode="devam", hold=8)),
    "artik5m": ("futures", "5m", dict(kind="akis_artik", n=144, L=2000, k=3.0, mode="devam", hold=24)),
    "uyum_spot5m": ("spot", "5m", dict(kind="uyumsuzluk", n=72, L=2000, k=3.5, mode="devam", hold=12, side="uzun")),
    "getiri5m_k5": ("futures", "5m", dict(kind="getiri", n=72, L=2000, k=5.0, mode="donus", hold=12)),
}
daily = {}
for key, (mkt, iv, p) in C.items():
    spec = ea.make_spec("tani_" + key, mkt, iv, **p)
    rr = run(spec, "dev", 1.0)
    r = rr.returns[rr.returns.index < DEV_TRAIN_END]
    d = daily_returns(r)
    daily[key] = d
    t = rr.trades[rr.trades["entry_time"] < DEV_TRAIN_END]
    lg = np.log1p(d)
    top = lg.sort_values(ascending=False)
    active = int((d != 0).sum())
    tot = lg.sum()
    yr = (1 + r).groupby(r.index.year).prod() - 1
    print(f"\n== {key}: toplam log {tot:+.3f}, aktif gün {active}, en iyi 5 gün payı {top.iloc[:5].sum()/tot:.2f}, "
          f"en iyi 10 gün {top.iloc[:10].sum()/tot:.2f}, en iyi 20 gün {top.iloc[:20].sum()/tot:.2f}")
    print("   en iyi 5 gün:", ", ".join(f"{i.date()} {v*100:+.1f}%" for i, v in d.sort_values(ascending=False).iloc[:5].items()))
    print("   en kötü 5 gün:", ", ".join(f"{i.date()} {v*100:+.1f}%" for i, v in d.sort_values().iloc[:5].items()))
    for dirn, g in t.groupby("direction"):
        print(f"   yön {dirn:+d}: işlem {len(g)}, ort net {g.net_return.mean()*1e4:+.1f} bps (portföy payı), toplam {g.net_return.sum()*100:+.1f}%")
    print("   yıllar:", " ".join(f"{y}:{v*100:+.0f}%" for y, v in yr.items()))
    # 2020-03 ve 2021-05 gibi aşırı ayları çıkarınca
    m = (1 + r).groupby(r.index.to_period("M")).prod() - 1
    print("   en iyi 5 ay:", ", ".join(f"{p} {v*100:+.1f}%" for p, v in m.sort_values(ascending=False).iloc[:5].items()),
          f"| pozitif ay oranı {np.mean(m > 0):.2f} ({len(m)} ay)")
D = pd.DataFrame(daily).fillna(0.0)
print("\nGünlük getiri korelasyonu (dev_train):")
print(D.corr().round(2).to_string())
