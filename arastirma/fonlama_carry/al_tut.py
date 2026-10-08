"""Al-tut karşılaştırması (deftere yazılmaz: strateji denemesi değildir).

Kullanım: python al_tut.py dev_train            (tarama sırasında)
          python al_tut.py dev_train dev_valid  (dondurmadan sonra)
"""
import sys
import pandas as pd
from grafik_analiz.research import StrategySpec, evaluate

pencereler = tuple(sys.argv[1:]) or ("dev_train",)


def uzun(data, funding, baslangic=None):
    out = {}
    for leg, df in data.items():
        s = pd.Series(1.0, index=df.index)
        if leg[0] == "futures":
            f = funding[leg[1]]
            s[df.index < f.index.min()] = 0.0
        out[leg] = s
    return out


ornekler = [
    ("BTC spot", "1d", (("spot", "BTCUSDT"),)),
    ("ETH spot", "1d", (("spot", "ETHUSDT"),)),
    ("SOL spot", "1d", (("spot", "SOLUSDT"),)),
    ("BTC/ETH/SOL spot eşit ağırlık", "1d", (("spot", "BTCUSDT"), ("spot", "ETHUSDT"), ("spot", "SOLUSDT"))),
    ("BTC vadeli uzun (fonlama dahil)", "4h", (("futures", "BTCUSDT"),)),
    ("BTC/ETH/SOL vadeli uzun eşit ağırlık (fonlama dahil)", "4h", (("futures", "BTCUSDT"), ("futures", "ETHUSDT"), ("futures", "SOLUSDT"))),
]
rows = []
for ad, iv, legs in ornekler:
    spec = StrategySpec("al_tut", "al_tut", iv, legs, uzun, {})
    res = evaluate(spec, windows=pencereler, cost_multipliers=(1.0,), record=False)
    for w in pencereler:
        m = res[w][1.0]
        rows.append({"ad": ad, "pencere": w, "baslangic": m.get("start"), "getiri": m.get("total_return"), "cagr": m.get("cagr"),
                     "sharpe": m.get("sharpe"), "maxdd": m.get("max_drawdown"), "fonlama": m.get("total_funding")})
df = pd.DataFrame(rows)
print(df.round(4).to_string(index=False))
df.to_csv(f"al_tut_{'_'.join(pencereler)}.csv", index=False)
