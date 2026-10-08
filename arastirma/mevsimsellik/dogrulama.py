"""Dondurulmuş yapılandırmaların TEK seferlik değerlendirmesi (dev_train + dev_valid, 1× ve 2× maliyet).

Her yapılandırma önce assert_causal'dan geçer, sonra evaluate(spec) bir kez çağrılır
ve candidate_check uygulanır. Sonuçlar dondurulmus_sonuclar.json'a yazılır.
Bu betik ikinci kez çalıştırılmamalıdır (çalıştırılırsa durur).
"""
import json
from pathlib import Path

from grafik_analiz.research import assert_causal, candidate_check, evaluate
from grafik_analiz.strategies.mevsimsellik import specs

out_path = Path(__file__).resolve().parent / "dondurulmus_sonuclar.json"
if out_path.exists():
    raise SystemExit("dondurulmuş değerlendirme zaten yapıldı; tekrar çalıştırılmaz")

out = {}
for spec in specs():
    assert_causal(spec)
    res = evaluate(spec)
    chk = candidate_check(res)
    out[spec.name] = {
        "params": spec.params,
        "interval": spec.interval,
        "legs": [list(l) for l in spec.legs],
        "causal": True,
        "candidate_check": {k: bool(v) for k, v in chk.items()},
        "metrics": {w: {str(m): v for m, v in d.items()} for w, d in res.items()},
    }
    t1, v1, v2 = res["dev_train"][1.0], res["dev_valid"][1.0], res["dev_valid"][2.0]
    print(f"{spec.name}: train R {t1['total_return']:.3f} S {t1['sharpe']:.2f} | valid R1x {v1['total_return']:.3f} R2x {v2['total_return']:.3f} "
          f"S {v1['sharpe']:.2f} MDD {v1['max_drawdown']:.3f} n {v1['trades']} p {v1['p_value']:.3f} | aday: {chk['aday']} {chk}")
out_path.write_text(json.dumps(out, ensure_ascii=False, indent=1, default=float), encoding="utf-8")
