"""dev_valid betimleyici döküm (değerlendirmeden SONRA; parametre değişmez, deftere yazmaz).

- En büyük düşüşün yeri (bar düzeyinde özsermaye) ve süresi.
- En iyi olay günü / en iyi ay çıkarılınca getiri.
- DSR duyarlılığı: deneme varyansı yalnız baz/spot_vadeli satırlarından hesaplanınca.
"""
import json

import numpy as np
import pandas as pd

from grafik_analiz.research import protocol
from grafik_analiz.research.evaluate import backtest, compute_signals, load_data
from grafik_analiz.research.ledger import ledger_path
from grafik_analiz.research.metrics import daily_returns, deflated_sharpe, window
from grafik_analiz.strategies.t2_lead_lag import FAMILY, specs

assert protocol.PROTOCOL_VERSION == "2"
s, e = protocol.PERIODS["dev_valid"]
sonuc = json.load(open("dogrulama_sonuc.json"))
rows = [json.loads(l) for l in ledger_path(FAMILY).open(encoding="utf-8")]
tr = [r for r in rows if r["pencere"] == "dev_train" and r["maliyet_kat"] == 1.0]
sub = [r for r in tr if r["parametreler"].get("tur") in ("baz", "spot_vadeli")]
sr_sub = np.array([r["olcu"]["sharpe"] for r in sub if r["olcu"].get("sharpe") is not None], dtype=float)
var_sub = float(np.var(sr_sub, ddof=1))
print(f"DSR duyarlılığı: baz/spot_vadeli satırları {len(sub)}, Sharpe varyansı {var_sub:.4f}")
for spec in specs():
    data, funding = load_data(spec, "dev")
    r = backtest(spec, data, funding, compute_signals(spec, data, funding), 1.0)
    rv = window(r.returns, s, e)
    eq = (1 + rv).cumprod()
    dd = eq / eq.cummax() - 1
    tmin = dd.idxmin()
    tpeak = eq[:tmin].idxmax()
    dv = daily_returns(rv)
    tot = float(eq.iloc[-1] - 1)
    best_day = dv.idxmax()
    wo_day = float((1 + tot) / (1 + dv.max()) - 1)
    ay = (1 + dv).groupby(dv.index.strftime("%Y-%m")).prod() - 1
    wo_month = float((1 + tot) / (1 + ay.max()) - 1)
    active_days = int((dv != 0).sum())
    m = sonuc["sonuclar"][spec.name]["metrics"]["dev_valid"]["1.0"]
    dsr_sub = deflated_sharpe(m["sharpe"], int(m["days"]), len(sub), var_sub, m["skew"], m["kurtosis"])
    print(f"{spec.name}: toplam {tot:+.4f} | en büyük düşüş {dd.min():+.4f} tepe {tpeak} dip {tmin} | "
          f"en iyi gün {best_day.date()} {dv.max():+.4f}, o gün çıkınca {wo_day:+.4f} | en iyi ay {ay.idxmax()} {ay.max():+.4f}, "
          f"o ay çıkınca {wo_month:+.4f} | işlem olan gün {active_days} | DSR (baz/sv varyansı) {dsr_sub:.4f}")
