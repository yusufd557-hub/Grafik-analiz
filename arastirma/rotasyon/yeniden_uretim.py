"""Modülün temiz içe aktarıldığını ve dev_train sayılarını yeniden ürettiğini denetler.

Deftere yazmaz (record=False) ve yalnız dev_train penceresini hesaplar; dev_valid
sayıları dondurulmus_sonuclar.json'dadır (aynı kod yolu).
"""
import json
from pathlib import Path

from grafik_analiz.research import evaluate
from grafik_analiz.strategies import all_specs
from grafik_analiz.strategies.rotasyon import specs

KLASOR = Path(__file__).resolve().parent
kayit = json.loads((KLASOR / "dondurulmus_sonuclar.json").read_text(encoding="utf-8"))
assert len([s for s in all_specs() if s.family == "rotasyon"]) == 5
for spec in specs():
    r = evaluate(spec, windows=("dev_train",), cost_multipliers=(1.0, 2.0), record=False)["dev_train"]
    k = kayit[spec.name]["sonuc"]["dev_train"]
    for m in ("1.0", "2.0"):
        a, b = r[float(m)]["total_return"], k[m]["total_return"]
        assert abs(a - b) < 1e-12, (spec.name, m, a, b)
    print("yeniden üretildi:", spec.name, round(r[1.0]["total_return"], 4), round(r[1.0]["sharpe"], 3))
