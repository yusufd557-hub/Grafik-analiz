"""Dondurulan yapılandırmaların TEK SEFERLİK değerlendirmesi (dev_train + dev_valid, 1× ve 2×).

Bu betik bir kez çalıştırılır. Sonuçlar dondurulmus_sonuclar.json'a yazılır.
"""
import json
import math
from pathlib import Path

import numpy as np

from grafik_analiz.research import PERIODS, candidate_check, daily_returns, deflated_sharpe, evaluate, run
from grafik_analiz.research import ledger
from grafik_analiz.research.metrics import window
from grafik_analiz.strategies.kirilim import specs

HERE = Path(__file__).resolve().parent
OUT = HERE / "dondurulmus_sonuclar.json"
assert not OUT.exists(), "dondurulmuş yapılandırmalar zaten değerlendirildi; tekrar çalıştırılmaz"

results = {}
for spec in specs():
    res = evaluate(spec)  # dev_train + dev_valid, 1x ve 2x; deftere yazılır
    cc = candidate_check(res)
    # dev_valid günlük getiri sayısı (DSR için) — aynı yapılandırma, kayıt dışı run()
    r = run(spec, "dev", 1.0)
    start, end = PERIODS["dev_valid"]
    n_days = len(daily_returns(window(r.returns, start, end)))
    results[spec.name] = {"params": spec.params, "interval": spec.interval, "legs": [list(l) for l in spec.legs],
                          "metrics": {w: {str(m): v for m, v in d.items()} for w, d in res.items()},
                          "candidate_check": cc, "n_days_valid": n_days}

t = ledger.trials("kirilim")
tr = t[(t["pencere"] == "dev_train") & (t["maliyet_kat"] == 1.0)]
sh = np.array([o.get("sharpe") for o in tr["olcu"]], dtype=float)
sh = sh[np.isfinite(sh)]
n_trials = int(len(tr))
var_sh = float(np.var(sh, ddof=1))
for name, d in results.items():
    v = d["metrics"]["dev_valid"]["1.0"]
    d["dsr"] = deflated_sharpe(v["sharpe"], d["n_days_valid"], n_trials, var_sh, v["skew"], v["kurtosis"])
    d["dsr_girdi"] = {"n_trials": n_trials, "sharpe_var": var_sh, "n_days": d["n_days_valid"], "sr": v["sharpe"], "skew": v["skew"], "kurt": v["kurtosis"]}

OUT.write_text(json.dumps(results, indent=1, ensure_ascii=False, default=lambda x: None if isinstance(x, float) and not math.isfinite(x) else str(x)), encoding="utf-8")
for name, d in results.items():
    print("==", name)
    for w in ("dev_train", "dev_valid"):
        for m in ("1.0", "2.0"):
            x = d["metrics"][w][m]
            print(f"  {w} {m}x: getiri={x['total_return']:+.4f} sharpe={x['sharpe']:.3f} mdd={x['max_drawdown']:.3f} islem={x['trades']} p={x['p_value']:.3f}")
    print("  candidate_check:", d["candidate_check"])
    print("  DSR:", round(d["dsr"], 4), d["dsr_girdi"])
