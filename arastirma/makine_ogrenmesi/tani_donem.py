"""dev_train içinde, tahminlerin/işlemin fiilen başladığı tarihten 2023 sonuna Sharpe (deftere yazılmaz;
yalnız defterde zaten kayıtlı yapılandırmalar). egitim="spot" vadeli spec'lerde birleşik getiri serisi
2017'de başlar (sıfır ağırlıklı spot bacaklar); bu tanı 2020-01-01'den ölçer."""
import json
import sys

import pandas as pd

from grafik_analiz.research import run, summarize
from grafik_analiz.strategies import makine_ogrenmesi as mo
from ortak import ad_uret, onceki_adlar

END = pd.Timestamp("2024-01-01", tz="UTC")
for interval, market, params, start in json.loads(sys.argv[1]):
    ad = ad_uret(interval, market, "PORT3", params)
    assert ad in onceki_adlar(), ad
    spec = mo.make_spec(ad, interval, market, **params)
    for cost in (1.0, 2.0):
        res = run(spec, "dev", cost)
        r = res.returns[res.returns.index < END]
        s = summarize(r, None, None, None, None, pd.Timestamp(start, tz="UTC"), END)
        print(f"{ad} {cost}x [{start} – 2023]: getiri={s['total_return']:+.3f} sharpe={s['sharpe']:.3f} mdd={s['max_drawdown']:.3f}", flush=True)
