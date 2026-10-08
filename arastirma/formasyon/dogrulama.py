"""Dondurulan yapılandırmaların TEK seferlik değerlendirmesi: dev_train + dev_valid, 1× ve 2× maliyet.

Her spec yalnız bir kez evaluate() edilir; sonuç hemen dondurulmus_sonuclar.json'a yazılır ve
yeniden çalıştırmada zaten değerlendirilmiş spec atlanır (dev_valid'e ikinci bakış olmasın diye).
"""
import json
import math
from pathlib import Path

from grafik_analiz.research import candidate_check, evaluate
from grafik_analiz.strategies.formasyon import specs

OUT = Path(__file__).resolve().parent / "dondurulmus_sonuclar.json"


def clean(v):
    if isinstance(v, dict):
        return {str(k): clean(x) for k, x in v.items()}
    if isinstance(v, (list, tuple)):
        return [clean(x) for x in v]
    if isinstance(v, float):
        return None if not math.isfinite(v) else v
    return v


done = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {}
for spec in specs():
    if spec.name in done:
        print("zaten değerlendirildi, atlandı:", spec.name)
        continue
    res = evaluate(spec)
    chk = candidate_check(res)
    done[spec.name] = clean({"interval": spec.interval, "legs": [list(l) for l in spec.legs], "params": spec.params,
                             "sonuc": {w: {str(m): met for m, met in d.items()} for w, d in res.items()}, "candidate_check": chk})
    OUT.write_text(json.dumps(done, ensure_ascii=False, indent=1), encoding="utf-8")
    t1, t2 = res["dev_train"][1.0], res["dev_train"][2.0]
    v1, v2 = res["dev_valid"][1.0], res["dev_valid"][2.0]
    print(f"\n== {spec.name}")
    for lab, m in (("train 1x", t1), ("train 2x", t2), ("valid 1x", v1), ("valid 2x", v2)):
        print(f"  {lab}: getiri={m['total_return']:+.4f} sharpe={m['sharpe']:.3f} mdd={m['max_drawdown']:.3f} işlem={m.get('trades')} p={m['p_value']:.3f} maruz={m.get('exposure', float('nan')):.2f}")
    print("  candidate_check:", chk)
