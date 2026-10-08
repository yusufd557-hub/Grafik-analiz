"""Modülün temiz içe aktarıldığını ve specs()'in dondurulmuş dev_train sonuçlarını yeniden ürettiğini denetler.
record=False ve yalnız dev_train: deftere yazılmaz, dev_valid'e yeniden bakılmaz."""
import json
from pathlib import Path
from grafik_analiz.research import evaluate
from grafik_analiz.strategies import all_specs
from grafik_analiz.strategies.fonlama_carry import specs

K = Path(__file__).resolve().parent
d = json.loads((K / "dondurulmus_sonuclar.json").read_text(encoding="utf-8"))
assert {s.name for s in specs()} == set(d), "specs() dondurulan listeyle aynı değil"
assert all(any(a.name == s.name for a in all_specs()) for s in specs())
for s in specs():
    r = evaluate(s, windows=("dev_train",), cost_multipliers=(1.0, 2.0), record=False)
    for m in ("1.0", "2.0"):
        a = r["dev_train"][float(m)]; b = d[s.name]["sonuclar"]["dev_train"][m]
        assert abs(a["total_return"] - b["total_return"]) < 1e-10 and abs(a["sharpe"] - b["sharpe"]) < 1e-8 and a["trades"] == b["trades"], s.name
    assert s.family == "fonlama_carry"
    print("ayni", s.name)
