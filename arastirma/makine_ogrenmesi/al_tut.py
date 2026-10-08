"""Al-tut kıyası (harness run() + summarize; deftere yazılmaz, strateji denemesi değildir).

Kullanım: python al_tut.py dev_train            (arama sırasında yalnız bu)
          python al_tut.py dev_train dev_valid  (dondurma sonrası)
Vadelide coinin ilk fonlama kaydından önce pozisyon 0 (stratejilerle aynı kural).
"""
import sys

import pandas as pd

from grafik_analiz.research import PERIODS, StrategySpec, run, summarize
from grafik_analiz.strategies.makine_ogrenmesi import COINS


def hep_uzun(data, funding, oran=1.0):
    out = {}
    for leg, df in data.items():
        s = pd.Series(oran, index=df.index)
        if leg[0] == "futures":
            f = funding.get(leg[1])
            s = s.where(df.index >= f.index.min(), 0.0) if f is not None and len(f) else s * 0.0
        out[leg] = s
    return out


def main():
    windows = sys.argv[1:] or ["dev_train"]
    rows = []
    for interval in ("1h", "4h", "1d"):
        for market in ("spot", "futures"):
            for oran in (1.0, 0.5):
                legs = tuple((market, c) for c in COINS)
                spec = StrategySpec(f"al_tut_{market}_{interval}_{oran}", "makine_ogrenmesi_kiyas", interval, legs, hep_uzun, {"oran": oran})
                res = run(spec, "dev", 1.0)
                for w in windows:
                    start, end = PERIODS[w]
                    s = summarize(res.returns, None, None, None, None, start, end)
                    rows.append({"pencere": w, "aralik": interval, "piyasa": market, "oran": oran, "baslangic": s.get("start"),
                                 "getiri": s.get("total_return"), "sharpe": s.get("sharpe"), "mdd": s.get("max_drawdown"),
                                 "gun": s.get("days")})
    df = pd.DataFrame(rows)
    pd.set_option("display.width", 200)
    print(df.to_string(index=False, float_format=lambda x: f"{x:.3f}"))
    df.to_csv(f"al_tut_{'_'.join(windows)}.csv", index=False)


if __name__ == "__main__":
    main()
