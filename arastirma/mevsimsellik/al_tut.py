"""Al-tut kıyası (harness run() + summarize; deftere yazılmaz, strateji değil).

Dondurma sonrası dev_train ve dev_valid pencereleri. Vadelide ilk fonlama kaydından önce pozisyon 0.
"""
import pandas as pd

from grafik_analiz.research import PERIODS, StrategySpec, run, summarize

COINS = ("BTCUSDT", "ETHUSDT", "SOLUSDT")


def hep_uzun(data, funding):
    out = {}
    for leg, df in data.items():
        s = pd.Series(1.0, index=df.index)
        if leg[0] == "futures":
            s[df["close_time"] < funding[leg[1]].index.min()] = 0.0
        out[leg] = s
    return out


rows = []
for m in ("spot", "futures"):
    for u in ("PORT3", "PORT2", "BTCUSDT", "ETHUSDT", "SOLUSDT"):
        legs = tuple((m, c) for c in (COINS if u == "PORT3" else COINS[:2] if u == "PORT2" else (u,)))
        spec = StrategySpec(f"al_tut_{m}_{u}", "mevsimsellik_kiyas", "1d", legs, hep_uzun, {})
        for mult in (1.0, 2.0):
            res = run(spec, "dev", mult)
            for w in ("dev_train", "dev_valid"):
                s = summarize(res.returns, None, res.exposure, res.costs, res.funding, *PERIODS[w])
                rows.append({"pencere": w, "maliyet": mult, "piyasa": m, "evren": u, "getiri": s["total_return"], "sharpe": s["sharpe"],
                             "mdd": s["max_drawdown"], "cagr": s["cagr"], "fonlama": s.get("total_funding")})
df = pd.DataFrame(rows)
pd.set_option("display.width", 200)
print(df[df.maliyet == 1.0].drop(columns="maliyet").to_string(index=False, float_format=lambda x: f"{x:.3f}"))
df.to_csv("al_tut_dev_train_dev_valid.csv", index=False)
