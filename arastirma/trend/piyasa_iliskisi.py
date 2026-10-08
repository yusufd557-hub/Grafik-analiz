"""Betimleyici analiz (dondurmadan SONRA, ayar yok): dondurulan stratejilerin ortalama
pozisyonu ve günlük getirilerinin aynı piyasadaki al-tut ile korelasyonu / betası.

Parametre değiştirmez, yeni yapılandırma denemez; deney defterine yazmaz.
"""

from __future__ import annotations

import pandas as pd

from grafik_analiz.research import StrategySpec, daily_returns, run
from grafik_analiz.research.metrics import window
from grafik_analiz.research.protocol import PERIODS
from grafik_analiz.strategies.trend import specs


def hold(data, funding):
    return {leg: pd.Series(1.0, index=df.index) for leg, df in data.items()}


rows = []
for spec in specs():
    res = run(spec)
    bench = run(StrategySpec("al_tut", "trend_benchmark", spec.interval, spec.legs, hold))
    for w in ("dev_train", "dev_valid"):
        start, end = PERIODS[w]
        s = daily_returns(window(res.returns, start, end))
        b = daily_returns(window(bench.returns, start, end))
        s, b = s.align(b, join="inner")
        pos = window(res.exposure, start, end)
        rows.append(
            {
                "strateji": spec.name,
                "pencere": w,
                "ort_pozisyon": round(float(pos.mean()), 3),
                "korelasyon": round(float(s.corr(b)), 3),
                "beta": round(float(s.cov(b) / b.var()), 3),
            }
        )
print(pd.DataFrame(rows).to_string(index=False))

# Yarı al-tut: her bacakta sabit 0,5 pozisyon (strateji değil; record=False, deneme sayılmaz).
from grafik_analiz.research import evaluate  # noqa: E402
from grafik_analiz.strategies.trend import legs_for  # noqa: E402


def half(data, funding):
    return {leg: pd.Series(0.5, index=df.index) for leg, df in data.items()}


rows = []
for market, interval in (("spot", "1d"), ("spot", "4h"), ("futures", "4h")):
    spec = StrategySpec(f"yari_al_tut_{market}_{interval}", "trend_benchmark", interval, legs_for(market, "PORT3"), half)
    res = evaluate(spec, record=False, cost_multipliers=(1.0,))
    for w in ("dev_train", "dev_valid"):
        m = res[w][1.0]
        rows.append({"kiyas": spec.name, "pencere": w, "getiri": round(m["total_return"], 4), "sharpe": round(m["sharpe"], 3), "max_dusus": round(m["max_drawdown"], 4)})
print(pd.DataFrame(rows).to_string(index=False))
