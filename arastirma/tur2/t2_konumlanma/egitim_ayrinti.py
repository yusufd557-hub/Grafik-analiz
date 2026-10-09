"""Eğitim dönemi (dev_train) içi ayrıntı: coin, yıl ve yön kırılımı.

Yalnız daha önce `evaluate` ile deftere yazılmış yapılandırmalar için kullanılır.
Sonuçlar hesaplanır hesaplanmaz DEV_TRAIN_END'de kesilir; iç doğrulama
dönemine ait hiçbir değer üretilmez ya da yazdırılmaz.
"""

from __future__ import annotations

import json
import sys

import numpy as np
import pandas as pd

from grafik_analiz.research.backtest import backtest_leg
from grafik_analiz.research.evaluate import benchmark_daily, compute_signals, load_data
from grafik_analiz.research.metrics import alpha_beta, daily_returns, sharpe
from grafik_analiz.research.protocol import DEV_TRAIN_END, PROTOCOL_VERSION
from grafik_analiz.strategies.t2_konumlanma import make_spec


def _train(s: pd.Series) -> pd.Series:
    return s[s.index < DEV_TRAIN_END]


def breakdown(universe: str, interval: str, params: dict) -> dict:
    assert PROTOCOL_VERSION == "2"
    spec = make_spec("ayrinti", universe, interval, params)
    data, funding = load_data(spec)
    signals = compute_signals(spec, data, funding)
    bench = _train(benchmark_daily(spec))
    w = spec.leg_weights()
    out = {}
    total = None
    for leg in spec.legs:
        sig = signals[leg]
        for side, s in (("hepsi", sig), ("uzun", sig.clip(lower=0)), ("kisa", sig.clip(upper=0))):
            res = backtest_leg(data[leg], s, market="futures", symbol=leg[1], funding=funding.get(leg[1]))
            net = _train(res.net)
            d = daily_returns(net)
            yearly = (1 + net).groupby(net.index.year).prod() - 1
            ab = alpha_beta(d, bench)
            out[f"{leg[1]}:{side}"] = {
                "getiri": float((1 + net).prod() - 1),
                "sharpe": sharpe(d),
                "alfa": ab["alfa"],
                "beta": ab["beta"],
                "yillik": {int(k): round(float(v), 3) for k, v in yearly.items()},
            }
            if side == "hepsi":
                total = net * w[leg] if total is None else total.add(net * w[leg], fill_value=0.0)
    yearly = (1 + total).groupby(total.index.year).prod() - 1
    out["sepet_yillik"] = {int(k): round(float(v), 3) for k, v in yearly.items()}
    return out


if __name__ == "__main__":
    universe, interval, params = sys.argv[1], sys.argv[2], json.loads(sys.argv[3])
    res = breakdown(universe, interval, params)
    for k, v in res.items():
        if isinstance(v, dict) and "getiri" in v:
            print(f"{k:22s} ret {v['getiri']:+8.3f} sh {v['sharpe']:5.2f} alfa {v['alfa']:+.3f} beta {v['beta']:+.2f} yillik {v['yillik']}")
        else:
            print(k, v)
