"""dev_train içi yıllık döküm (defterde zaten kayıtlı yapılandırmalar için; seri 2024-01-01'de kesilir).

Kullanım: python tani.py '<json listesi: [[interval, market, {params}], ...]>'
"""
import json
import sys

from ortak import yillik

cfgs = json.loads(sys.argv[1])
for interval, market, params in cfgs:
    for cost in (1.0, 2.0):
        y = yillik(interval, market, cost=cost, **params)
        yil = " ".join(f"{int(r.yil)}:{r.getiri:+.2f}/{r.sharpe:.2f}" for r in y.itertuples())
        print(f"{interval} {market} {params} {cost}x | {yil} | bacak " + " ".join(f"{k[:3]}:{v:+.2f}" for k, v in y.attrs["bacak"].items()), flush=True)
