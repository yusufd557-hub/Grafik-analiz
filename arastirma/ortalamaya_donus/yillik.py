"""Kayıtlı yapılandırmaların dev_train içi yıllık dökümü.

Veri DEV_TRAIN_END'de kesilir; dev_valid verisi sinyal hesabına bile girmez.
Yeni yapılandırma değildir (deney defterine yazılmaz); defterdeki satırların
yıllara göre ayrıştırmasıdır.
"""
import json
import sys

import pandas as pd

from grafik_analiz.research import DEV_TRAIN_END
from grafik_analiz.research.evaluate import backtest, compute_signals, load_data
from grafik_analiz.research.metrics import summarize
from grafik_analiz.strategies.ortalamaya_donus import make_spec


def yillik(market, universe, interval, params, mult=1.0):
    spec = make_spec("yillik", market, universe, interval, **params)
    data, funding = load_data(spec, "dev")
    data = {k: v[v.index < DEV_TRAIN_END] for k, v in data.items()}
    funding = {k: v[v.index < DEV_TRAIN_END] for k, v in funding.items()}
    res = backtest(spec, data, funding, compute_signals(spec, data, funding), mult)
    rows = []
    for y in sorted(set(res.returns.index.year)):
        s = pd.Timestamp(f"{y}-01-01", tz="UTC")
        e = min(pd.Timestamp(f"{y + 1}-01-01", tz="UTC"), DEV_TRAIN_END)
        m = summarize(res.returns, res.trades, res.exposure, res.costs, res.funding, s, e)
        rows.append({"yil": y, "getiri": m.get("total_return"), "sharpe": m.get("sharpe"), "maxdd": m.get("max_drawdown"), "islem": m.get("trades"), "ort_islem": m.get("avg_trade")})
    leg_rows = []
    for leg, r in res.legs.items():
        t = r.trades
        leg_rows.append({"bacak": leg[1], "islem": len(t), "ort_net": t["net_return"].mean() if len(t) else None, "toplam_net": float((1 + r.net).prod() - 1)})
    return pd.DataFrame(rows), pd.DataFrame(leg_rows)


if __name__ == "__main__":
    for line in sys.argv[1:]:
        market, universe, interval, params = json.loads(line)
        y, l = yillik(market, universe, interval, params)
        print(market, universe, interval, params)
        print(y.round(4).to_string(index=False))
        print(l.round(4).to_string(index=False))
        print()
