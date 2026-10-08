"""specs() sayılarının yeniden üretimi: yalnız dev_train, record=False (deftere yazmaz, dev_valid'e ikinci bakış yok)."""
import json
from pathlib import Path

from grafik_analiz.research import evaluate
from grafik_analiz.strategies import all_specs
from grafik_analiz.strategies.formasyon import FAMILY, specs

HERE = Path(__file__).resolve().parent
ref = json.loads((HERE / "dondurulmus_sonuclar.json").read_text(encoding="utf-8"))
assert len([s for s in all_specs() if s.family == FAMILY]) == len(ref)
ok = True
for spec in specs():
    res = evaluate(spec, windows=("dev_train",), cost_multipliers=(1.0, 2.0), record=False)
    for m in ("1.0", "2.0"):
        a = res["dev_train"][float(m)]
        b = ref[spec.name]["sonuc"]["dev_train"][m]
        for k in ("total_return", "sharpe", "max_drawdown", "trades"):
            same = abs(a[k] - b[k]) < 1e-9
            ok &= same
        print(spec.name, m, "getiri", round(a["total_return"], 6), "ref", round(b["total_return"], 6), "işlem", a["trades"], b["trades"], "aynı" if same else "FARKLI")
print("SONUÇ:", "hepsi aynı" if ok else "FARK VAR")
