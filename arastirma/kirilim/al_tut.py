"""Al-tut karşılaştırması (harness run() + summarize, deftere yazılmaz; strateji değil, kıyas).

Kullanım: python al_tut.py dev_train        (arama sırasında yalnız bu)
          python al_tut.py dev_train dev_valid (dondurma sonrası)
"""
import json
import sys

import pandas as pd

from grafik_analiz.research import PERIODS, StrategySpec, run, summarize

def hep_uzun(data, funding):
    return {leg: pd.Series(1.0, index=df.index) for leg, df in data.items()}

windows = sys.argv[1:] or ["dev_train"]
rows = []
for interval in ("4h",):
    for market in ("spot", "futures"):
        for uni in ("BTCUSDT", "ETHUSDT", "SOLUSDT", "PORT3"):
            legs = tuple((market, c) for c in ("BTCUSDT", "ETHUSDT", "SOLUSDT")) if uni == "PORT3" else ((market, uni),)
            spec = StrategySpec(f"al_tut_{market}_{uni}", "kirilim_kiyas", interval, legs, hep_uzun, {})
            res = run(spec, "dev", 1.0)
            for w in windows:
                start, end = PERIODS[w]
                s = summarize(res.returns, None, None, None, None, start, end)
                rows.append({"pencere": w, "piyasa": market, "evren": uni, "baslangic": s.get("start"), "getiri": s.get("total_return"),
                             "sharpe": s.get("sharpe"), "mdd": s.get("max_drawdown"), "cagr": s.get("cagr")})
df = pd.DataFrame(rows)
pd.set_option("display.width", 200)
print(df.to_string(index=False, float_format=lambda x: f"{x:.3f}"))
df.to_csv(f"al_tut_{'_'.join(windows)}.csv", index=False)
