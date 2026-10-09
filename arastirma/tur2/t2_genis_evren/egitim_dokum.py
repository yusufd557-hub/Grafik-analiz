"""Eğitim içi döküm (yalnız dev_train): veri 31.12.2024 sonrasında kesilir, sonra harness
`compute_signals` + `backtest` ile yıllık getiri, uzun/kısa taraf katkısı, maliyet, fonlama.
Yalnız deftere yazılmış yapılandırmalar için kullanılır. Kullanım: python egitim_dokum.py '<json listesi>'"""
import json
import sys

import numpy as np
import pandas as pd

from grafik_analiz.research import protocol
from grafik_analiz.research.evaluate import backtest, benchmark_daily, compute_signals, load_data
from grafik_analiz.research.metrics import alpha_beta, daily_returns, sharpe, window
from grafik_analiz.strategies.t2_genis_evren import make_spec

assert protocol.PROTOCOL_VERSION == "2"
END = protocol.DEV_TRAIN_END

_cache = {}


def train_data(interval):
    if interval not in _cache:
        spec = make_spec("t2_genis_evren_dokum", interval, {})
        data, funding = load_data(spec)
        data = {k: v[v.index < END] for k, v in data.items()}
        data = {k: v for k, v in data.items()}
        funding = {k: v[v.index < END] for k, v in funding.items()}
        _cache[interval] = (data, funding)
    return _cache[interval]


def dokum(interval, params, mult=1.0):
    spec = make_spec("t2_genis_evren_dokum", interval, params)
    data, funding = train_data(interval)
    # Boş kalan (yalnız 2025 sonrası listelenen) bacaklara boş çerçeve verilir.
    data = {leg: data[leg] for leg in spec.legs}
    sig = spec.signal_fn({k: v for k, v in data.items() if len(v)}, funding, **spec.params)
    legs_nonempty = tuple(l for l in spec.legs if len(data[l]))
    spec2 = make_spec("t2_genis_evren_dokum", interval, params)
    spec2.legs = legs_nonempty
    spec2.weights = {l: 1.0 / len(spec.legs) for l in legs_nonempty}
    res = backtest(spec2, {l: data[l] for l in legs_nonempty}, funding, sig, mult)
    r = window(res.returns, None, END)
    d = daily_returns(r)
    yearly = ((1 + r).groupby(r.index.year).prod() - 1)
    w = 1.0 / len(spec.legs)
    long_c = pd.Series(0.0, index=r.index); short_c = pd.Series(0.0, index=r.index)
    for leg, lr in res.legs.items():
        pos = lr.position.reindex(r.index).fillna(0.0)
        net = lr.net.reindex(r.index).fillna(0.0) * w
        long_c += net.where(pos > 0, 0.0); short_c += net.where(pos < 0, 0.0)
    lc = ((1 + long_c).groupby(r.index.year).prod() - 1)
    sc = ((1 + short_c).groupby(r.index.year).prod() - 1)
    bench = benchmark_daily(spec2, "dev")
    ab = alpha_beta(d, bench)
    gross = res.exposure.reindex(r.index)
    yab = {}
    for y in sorted(set(d.index.year)):
        dy = d[d.index.year == y]
        yab[y] = alpha_beta(dy, bench)
    return {
        "yillik": yearly.round(4).to_dict(),
        "yillik_sharpe": {y: round(sharpe(d[d.index.year == y]), 2) for y in sorted(set(d.index.year))},
        "yillik_alfa_t": {y: round(v["alfa_t"], 2) for y, v in yab.items()},
        "uzun_taraf": lc.round(4).to_dict(), "kisa_taraf": sc.round(4).to_dict(),
        "toplam_maliyet": round(float(res.costs[res.costs.index < END].sum()), 4),
        "toplam_fonlama_odenen": round(float(res.funding[res.funding.index < END].sum()), 4),
        "ort_brut_maruziyet": round(float(gross.mean()), 4),
        "sharpe": round(sharpe(d), 3), "alfa_beta": {k: round(v, 4) for k, v in ab.items()},
    }


if __name__ == "__main__":
    for item in json.loads(sys.argv[1]):
        interval, params = item
        out = dokum(interval, params)
        print(interval, json.dumps(params), flush=True)
        for k, v in out.items():
            print("   ", k, v, flush=True)
