"""Son modülden yeniden üretim kontrolü: evaluate(record=False) sonuçları dogrulama_sonuc.json ile aynı mı."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ortak  # noqa: E402,F401
from grafik_analiz.research.evaluate import candidate_check, evaluate  # noqa: E402
from grafik_analiz.strategies import t2_meta as tm  # noqa: E402

ref = json.loads((Path(__file__).resolve().parent / "dogrulama_sonuc.json").read_text(encoding="utf-8"))
worst = 0.0
for spec in tm.specs():
    res = evaluate(spec, record=False)
    for w in ("dev_train", "dev_valid"):
        for m in (1.0, 2.0):
            for k in ("total_return", "sharpe", "alfa", "beta", "alfa_t", "max_drawdown"):
                d = abs(res[w][m][k] - ref[spec.name]["sonuc"][w][str(m)][k])
                worst = max(worst, d)
            assert res[w][m]["trades"] == ref[spec.name]["sonuc"][w][str(m)]["trades"]
    print(spec.name, candidate_check(res)["aday"], flush=True)
print("en buyuk fark", worst)
