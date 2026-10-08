"""Al-tut kıyası, ML tahminlerinin başladığı tarihten 2023 sonuna (dev_train içi; deftere yazılmaz).

Spot tahminleri 2018-09-01'de, vadeli tahminleri (kendi verisiyle eğitim) 2021-01-01'de başlar.
Ayrıca yıl bazında al-tut getirisi.
"""
import pandas as pd

from grafik_analiz.research import StrategySpec, run, summarize
from grafik_analiz.strategies.makine_ogrenmesi import COINS
from al_tut import hep_uzun  # noqa: E402  (betik olarak çalışır)

END = pd.Timestamp("2024-01-01", tz="UTC")
rows = []
for interval in ("4h",):
    for market, start in (("spot", "2018-09-01"), ("futures", "2021-01-01"), ("futures", "2020-01-01")):
        legs = tuple((market, c) for c in COINS)
        spec = StrategySpec(f"al_tut_{market}", "makine_ogrenmesi_kiyas", interval, legs, hep_uzun, {"oran": 1.0})
        res = run(spec, "dev", 1.0)
        s = summarize(res.returns, None, None, None, None, pd.Timestamp(start, tz="UTC"), END)
        rows.append({"aralik": interval, "piyasa": market, "baslangic": start, "getiri": s["total_return"], "sharpe": s["sharpe"], "mdd": s["max_drawdown"]})
        r = res.returns[(res.returns.index >= pd.Timestamp(start, tz="UTC")) & (res.returns.index < END)]
        print(market, start, {int(y): round(float((1 + g).prod() - 1), 3) for y, g in r.groupby(r.index.year)})
print(pd.DataFrame(rows).to_string(index=False, float_format=lambda x: f"{x:.3f}"))
