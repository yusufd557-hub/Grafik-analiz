"""Dondurulan yapılandırmaların TEK SEFERLİK iç doğrulaması (dev_valid).

Kullanım:  python arastirma/trend/dogrulama.py

Her spec için: assert_causal → evaluate(spec) (dev_train + dev_valid, 1× ve 2×)
→ candidate_check. Ardından Deflated Sharpe: deneme sayısı = defterde
pencere=="dev_train" ve maliyet_kat==1.0 satırları; varyans = bu satırların
yıllık Sharpe varyansı; çarpıklık/basıklık = dev_valid günlük getirilerinden.

Sonuç `dogrulama_sonuc.json` dosyasına yazılır. Dosya varsa betik çalışmaz
(dev_valid'e ikinci kez bakılmasın diye).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from grafik_analiz.research import assert_causal, candidate_check, deflated_sharpe, evaluate
from grafik_analiz.research.ledger import _clean, trials
from grafik_analiz.strategies.trend import FAMILY, specs

HERE = Path(__file__).resolve().parent
OUT = HERE / "dogrulama_sonuc.json"

KEYS = (
    "total_return", "cagr", "sharpe", "sortino", "volatility", "max_drawdown", "trades", "win_rate",
    "profit_factor", "best_trade", "total_without_best", "exposure", "total_costs", "total_funding",
    "p_value", "skew", "kurtosis", "days", "start", "end",
)


def main() -> dict:
    if OUT.exists():
        sys.exit(f"{OUT.name} zaten var: dev_valid değerlendirmesi bir kez yapılır.")
    results = {}
    for spec in specs():
        assert spec.family == FAMILY
        assert_causal(spec)
        res = evaluate(spec)
        results[spec.name] = {
            "params": _clean({"interval": spec.interval, "legs": [list(l) for l in spec.legs], **spec.params}),
            "metrics": {w: {str(m): {k: res[w][m].get(k) for k in KEYS} for m in res[w]} for w in res},
            "candidate_check": candidate_check(res),
            "causal_check": True,
        }
        print(spec.name, results[spec.name]["candidate_check"], flush=True)

    t = trials(FAMILY)
    t = t[(t["pencere"] == "dev_train") & (t["maliyet_kat"] == 1.0)]
    sr = t["olcu"].apply(lambda o: o.get("sharpe")).astype(float).dropna()
    n_trials, var_sr = int(len(t)), float(sr.var(ddof=1))
    for name, r in results.items():
        v = r["metrics"]["dev_valid"]["1.0"]
        r["deflated_sharpe"] = deflated_sharpe(v["sharpe"], int(v["days"]), n_trials, var_sr, v["skew"], v["kurtosis"])
    out = {"n_trials": n_trials, "sharpe_var_trials": var_sr, "results": results}
    OUT.write_text(json.dumps(_clean(out), ensure_ascii=False, indent=1), encoding="utf-8")
    return out


if __name__ == "__main__":
    main()
