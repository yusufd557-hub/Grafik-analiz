"""specs() yapılandırmalarının dondurulmuş sonuçları yeniden ürettiğini doğrular (deftere yazmaz)."""
import json

from grafik_analiz.research import evaluate
from grafik_analiz.strategies.ortalamaya_donus import specs
from ortak import KLASOR

ref = json.loads((KLASOR / "dondurulmus_sonuclar.json").read_text())["sonuc"]
for spec in specs():
    r = evaluate(spec, record=False)
    for w in ("dev_train", "dev_valid"):
        for m in ("1.0", "2.0"):
            a = r[w][float(m)]
            b = ref[spec.name]["results"][w][m]
            for k in ("total_return", "sharpe", "max_drawdown", "trades"):
                assert abs(a[k] - b[k]) < 1e-9, (spec.name, w, m, k, a[k], b[k])
    print(spec.name, "OK")
