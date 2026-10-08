"""Dondurma öncesi tanı (yalnız dev_train; deftere yazılmaz; yalnız defterde kayıtlı yapılandırmalar).

Her yapılandırma için 1× ve 2× maliyette: yıllık getiri/Sharpe, bacak getirisi ve tahminlerin
fiilen başladığı tarihten (spot 2018-09-01, vadeli 2020-01-01) 2023 sonuna özet. Seri
hesaplamadan ÖNCE 2024-01-01'de kesilir.
Kullanım: python tani_secim.py '<json: [[interval, market, {params}], ...]>'
"""
import json
import sys

import pandas as pd

from grafik_analiz.research import run, summarize
from grafik_analiz.research.metrics import daily_returns, sharpe
from grafik_analiz.strategies import makine_ogrenmesi as mo
from ortak import ad_uret, onceki_adlar

END = pd.Timestamp("2024-01-01", tz="UTC")
for interval, market, params in json.loads(sys.argv[1]):
    ad = ad_uret(interval, market, "PORT3", params)
    assert ad in onceki_adlar(), ad
    spec = mo.make_spec(ad, interval, market, **params)
    start = pd.Timestamp("2018-09-01" if market == "spot" else "2020-01-01", tz="UTC")
    for cost in (1.0, 2.0):
        res = run(spec, "dev", cost)
        r = res.returns[res.returns.index < END]
        s = summarize(r, None, None, None, None, start, END)
        yil = " ".join(f"{y}:{(1 + g).prod() - 1:+.2f}/{sharpe(daily_returns(g)):.2f}" for y, g in r[r.index >= start].groupby(r[r.index >= start].index.year))
        bacak = " ".join(f"{leg[1][:3]}:{(1 + lr.net[lr.net.index < END]).prod() - 1:+.2f}" for leg, lr in res.legs.items() if spec.leg_weights()[leg] > 0)
        print(f"{ad} {cost}x | {start.date()}–2023: getiri={s['total_return']:+.2f} sharpe={s['sharpe']:.2f} mdd={s['max_drawdown']:.2f} | {yil} | {bacak}", flush=True)
