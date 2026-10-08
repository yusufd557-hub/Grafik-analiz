"""Dondurulan yapılandırmaların tanılaması (dev_valid değerlendirmesinden SONRA; yeniden ayar yapılmadı).

Bacak (coin) ve dönem bazında döküm, işlem başına brüt kenar. Deney defterine yazılmaz.
"""
import pandas as pd

from grafik_analiz.research import PERIODS
from grafik_analiz.research.evaluate import run
from grafik_analiz.research.metrics import summarize
from grafik_analiz.strategies.ortalamaya_donus import specs

pd.set_option("display.width", 250)
DILIMLER = {
    "2020": ("2020-01-01", "2021-01-01"), "2021": ("2021-01-01", "2022-01-01"),
    "2022": ("2022-01-01", "2023-01-01"), "2023": ("2023-01-01", "2024-01-01"),
    "2024H1": ("2024-01-01", "2024-07-01"), "2024H2": ("2024-07-01", "2025-01-01"), "2025H1": ("2025-01-01", "2025-07-01"),
}
for spec in specs():
    res = run(spec, "dev", 1.0)
    print("==", spec.name)
    rows = []
    for k, (a, b) in DILIMLER.items():
        a, b = pd.Timestamp(a, tz="UTC"), pd.Timestamp(b, tz="UTC")
        m = summarize(res.returns, res.trades, res.exposure, res.costs, res.funding, a, b)
        rows.append({"dilim": k, "getiri": m.get("total_return"), "sharpe": m.get("sharpe"), "maxdd": m.get("max_drawdown"), "islem": m.get("trades")})
    print(pd.DataFrame(rows).round(4).to_string(index=False))
    rows = []
    for w in ("dev_train", "dev_valid"):
        a, b = PERIODS[w]
        for leg, r in res.legs.items():
            t = r.trades
            t = t[(t["entry_time"] < b) & ((a is None) | (t["entry_time"] >= a))] if a is not None else t[t["entry_time"] < b]
            net = r.net[(r.net.index < b) & ((r.net.index >= a) if a is not None else True)]
            rows.append({"pencere": w, "bacak": leg[1], "islem": len(t), "ort_brut": t["gross_return"].mean(), "ort_net": t["net_return"].mean(),
                         "kazanma": (t["net_return"] > 0).mean(), "bacak_getiri": float((1 + net).prod() - 1)})
    print(pd.DataFrame(rows).round(4).to_string(index=False))
