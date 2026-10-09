"""dev_valid sonrası betimleyici: dondurulanların dev_valid günlük getiri korelasyonu (deftere yazılmaz)."""
import pandas as pd

from grafik_analiz.research import protocol
from grafik_analiz.research.evaluate import run
from grafik_analiz.research.metrics import daily_returns, window
from grafik_analiz.strategies.t2_cift import specs

d = {}
for kod, spec in zip("BCD", specs()):
    r = run(spec, "dev", 1.0)
    d[kod] = daily_returns(window(r.returns, *protocol.PERIODS["dev_valid"]))
print(pd.DataFrame(d).corr().round(3).to_string())
