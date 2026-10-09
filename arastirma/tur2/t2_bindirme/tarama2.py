"""Tarama 2: portföy bileşen havuzu (tur 1, bütün bacakları vadeli, 19 yapılandırma). Yalnız dev_train.

Her bileşen `t2_bindirme_bilesen_<ad>` olarak deftere yazılır. Eğitim günlük getirileri
(veri 31.12.2024'te kesik) `bilesen_gunluk.csv` dosyasına kaydedilir.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import pandas as pd  # noqa: E402
from ortak import KLASOR, alt_donem, egitim_calistir, log, yaz  # noqa: E402

from grafik_analiz.research.evaluate import evaluate  # noqa: E402
from grafik_analiz.research.metrics import daily_returns  # noqa: E402
from grafik_analiz.strategies.t2_bindirme import bilesen_spec, round1_futures_pool  # noqa: E402


def main():
    pool = round1_futures_pool()
    if len(sys.argv) > 1:
        pool = [p for p in pool if any(a in p for a in sys.argv[1:])]
    out_csv = KLASOR / ("tarama2.csv" if len(sys.argv) == 1 else f"tarama2_{'_'.join(sys.argv[1:])}.csv")
    gun_csv = KLASOR / ("bilesen_gunluk.csv" if len(sys.argv) == 1 else f"bilesen_gunluk_{'_'.join(sys.argv[1:])}.csv")
    rows, gun = [], {}
    for i, name in enumerate(pool, 1):
        spec = bilesen_spec(name)
        res = evaluate(spec, windows=("dev_train",), cost_multipliers=(1.0, 2.0))
        m1, m2 = res["dev_train"][1.0], res["dev_train"][2.0]
        er, _ = egitim_calistir(spec)
        d = daily_returns(er.returns)
        gun[name] = d
        row = {
            "bilesen": name,
            "interval": spec.interval,
            "ret": m1.get("total_return"),
            "ret2": m2.get("total_return"),
            "sharpe": m1.get("sharpe"),
            "mdd": m1.get("max_drawdown"),
            "trades": m1.get("trades"),
            "alfa": m1.get("alfa"),
            "beta": m1.get("beta"),
            "alfa_t": m1.get("alfa_t"),
            "maruz": m1.get("exposure"),
            **alt_donem(spec, er),
        }
        rows.append(row)
        log(f"{i}/{len(pool)} {name} ret={row['ret']:.3f} ret2={row['ret2']:.3f} alfa={row['alfa']:.3f} t={row['alfa_t']:.2f} "
            f"a20_23={row['alfa_20_23']:.3f} a24={row['alfa_24']:.3f} vol={row['vol_20p']:.3f}")
        yaz(rows, out_csv)
        pd.DataFrame(gun).to_csv(gun_csv)
    log("BITTI")


if __name__ == "__main__":
    main()
