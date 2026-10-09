"""Tanı: seçilmiş yapılandırmaların yıl ve coin kırılımı — YALNIZ dev_train (2025-01-01 öncesi).

`run()` bütün dev dönemi için sinyal üretir (nedensel); burada yalnız 2025-01-01 öncesi getiriler
kesilip yazdırılır. Deftere yazmaz (yapılandırmalar zaten defterde).
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ortak  # noqa: E402,F401
from grafik_analiz.research.evaluate import benchmark_daily, run  # noqa: E402
from grafik_analiz.research.metrics import alpha_beta, daily_returns, sharpe  # noqa: E402
from grafik_analiz.research.protocol import DEV_TRAIN_END  # noqa: E402
from grafik_analiz.strategies import t2_meta as tm  # noqa: E402


def rapor(interval: str, p: dict) -> None:
    name = ortak.isim(interval, p)
    spec = tm.make_spec(name, interval, **p)
    res = run(spec)
    r = res.returns[res.returns.index < DEV_TRAIN_END]
    bench = benchmark_daily(spec)
    bench = bench[bench.index < DEV_TRAIN_END]
    print(f"== {name}")
    rows = []
    for y, g in r.groupby(r.index.year):
        d = daily_returns(g)
        ab = alpha_beta(d, bench)
        legs = {leg[1][:3]: float((1 + res.legs[leg].net[(res.legs[leg].net.index.year == y)]).prod() - 1) for leg in spec.legs}
        rows.append({"yil": y, "getiri": float((1 + g).prod() - 1), "sharpe": sharpe(d), "alfa": ab["alfa"], "beta": ab["beta"], **legs})
    print(pd.DataFrame(rows).round(3).to_string(index=False))
    tr = res.trades[res.trades["entry_time"] < DEV_TRAIN_END]
    print("islem", len(tr), "uzun", int((tr["direction"] > 0).sum()), "kisa", int((tr["direction"] < 0).sum()),
          "uzun_net_top", round(float(tr.loc[tr["direction"] > 0, "net_return"].sum()), 3),
          "kisa_net_top", round(float(tr.loc[tr["direction"] < 0, "net_return"].sum()), 3), flush=True)


if __name__ == "__main__":
    for arg in sys.argv[1:]:
        iv, params = arg.split("|", 1)
        rapor(iv, json.loads(params))
