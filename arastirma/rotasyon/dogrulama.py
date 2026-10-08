"""Dondurulmuş yapılandırmaların TEK SEFERLİK değerlendirmesi (dev_train + dev_valid, 1× ve 2×).

Bu betik bir kez çalıştırılır. Sonuçlar dondurulmus_sonuclar.json dosyasına yazılır.
"""
import json
import math
import pickle
from pathlib import Path

from grafik_analiz.research import candidate_check, evaluate
from grafik_analiz.strategies.rotasyon import specs

KLASOR = Path(__file__).resolve().parent
hedef = KLASOR / "dondurulmus_sonuclar.json"
assert not hedef.exists(), "dev_valid değerlendirmesi zaten yapılmış; tekrar çalıştırılmaz"

ham = {}
for spec in specs():
    res = evaluate(spec)
    ham[spec.name] = {"sonuc": res, "aday": candidate_check(res)}
    with open(KLASOR / "dondurulmus_sonuclar.pkl", "wb") as fh:
        pickle.dump(ham, fh)


def temiz(v):
    if isinstance(v, dict):
        return {str(k): temiz(x) for k, x in v.items()}
    if isinstance(v, (list, tuple)):
        return [temiz(x) for x in v]
    if isinstance(v, float):
        return v if math.isfinite(v) else None
    if hasattr(v, "item"):
        return temiz(v.item())
    return v


hedef.write_text(json.dumps(temiz(ham), ensure_ascii=False, indent=1, default=str), encoding="utf-8")
for ad, x in ham.items():
    v1 = x["sonuc"]["dev_valid"][1.0]
    v2 = x["sonuc"]["dev_valid"][2.0]
    t1 = x["sonuc"]["dev_train"][1.0]
    print(ad)
    print("  dev_train getiri %.4f sharpe %.3f | dev_valid getiri %.4f (2x %.4f) sharpe %.3f maxdd %.4f islem %d | aday %s"
          % (t1["total_return"], t1["sharpe"], v1["total_return"], v2["total_return"], v1["sharpe"], v1["max_drawdown"], v1["trades"], x["aday"]["aday"]))
    print("  ", x["aday"])
