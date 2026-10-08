"""Defterde kayıtlı yapılandırmalar için yalnız dev_train yıllık/bacak tanısı (2024 öncesine kesilir)."""
import json
import sys

from ortak import done_keys, train_diagnostics

names = sys.argv[1:]
rows = {r["name"]: r for r in done_keys().values()}
for nm in names:
    r = rows[nm]
    d = train_diagnostics(r["interval"], r["market"], r["universe"], r["params"])
    print("==", nm, "ret1=%.2f sh1=%.2f" % (r["ret1"], r["sharpe1"]))
    for mult in (1.0, 2.0):
        ys = " ".join(f"{y}:{v['ret']:+.2f}/{(v['sharpe'] or 0):.2f}/{v['trades']}" for y, v in d[mult]["years"].items())
        print(f"  {mult}x yıllar (getiri/sharpe/işlem): {ys}")
    ls = " ".join(f"{k}:{v['ret']:+.2f}/{(v['sharpe'] or 0):.2f}/mdd{v['mdd']:.2f}" for k, v in d[1.0]["legs"].items())
    print(f"  1x bacaklar: {ls}")
    ds = " ".join(f"yon{k}: n={v['n']} toplam={v['sum_net']:+.2f} ort={v['mean_net']:+.4f} kazanma={v['win']:.2f}" for k, v in d[1.0]["dirs"].items())
    print(f"  1x yön (portföy ağırlıklı işlem net getirisi toplamı): {ds}")
