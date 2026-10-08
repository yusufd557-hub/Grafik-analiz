"""specs() modülünün raporlanan sayıları ürettiğinin kontrolü.

dev_valid'e yeniden bakmamak için yalnız dev_train penceresi, record=False ile
(deftere yazılmaz) hesaplanır ve dondurulmus_sonuclar.json ile karşılaştırılır.
"""
import json
import math
from pathlib import Path

import grafik_analiz.strategies as strategies
from grafik_analiz.research import evaluate
from grafik_analiz.strategies.mevsimsellik import specs

saved = json.loads((Path(__file__).resolve().parent / "dondurulmus_sonuclar.json").read_text(encoding="utf-8"))
names = [s.name for s in strategies.all_specs()]
assert len(specs()) == len(saved) == 4
for spec in specs():
    assert spec.name in names and spec.family == "mevsimsellik" and spec.name in saved
    assert spec.params == saved[spec.name]["params"]
    res = evaluate(spec, windows=("dev_train",), record=False)
    for m in (1.0, 2.0):
        a = res["dev_train"][m]
        b = saved[spec.name]["metrics"]["dev_train"][str(m)]
        for k in ("total_return", "sharpe", "max_drawdown", "trades"):
            assert math.isclose(float(a[k]), float(b[k]), rel_tol=1e-9, abs_tol=1e-12), (spec.name, m, k, a[k], b[k])
    print("yeniden üretildi:", spec.name)
