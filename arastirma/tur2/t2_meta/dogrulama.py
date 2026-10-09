"""Dondurulan 5 yapılandırmanın TEK SEFERLİK iç doğrulama (dev_valid) değerlendirmesi.

Her spec için `evaluate(spec)` (dev_train + dev_valid, 1× ve 2×; deftere yazılır) ve
`candidate_check`. Ardından Deflated Sharpe (deneme sayısı = defterde pencere=dev_train ve
maliyet_kat=1,0 satırları), al-tut kıyası ve günlük getiri korelasyonları.
"""
import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ortak  # noqa: E402,F401
from grafik_analiz.research import ledger  # noqa: E402
from grafik_analiz.research.evaluate import benchmark_daily, candidate_check, evaluate, run  # noqa: E402
from grafik_analiz.research.metrics import daily_returns, deflated_sharpe, window  # noqa: E402
from grafik_analiz.research.protocol import PERIODS  # noqa: E402
from grafik_analiz.strategies import t2_meta as tm  # noqa: E402

K = Path(__file__).resolve().parent
KEEP = ["total_return", "cagr", "sharpe", "sortino", "volatility", "max_drawdown", "trades", "win_rate", "exposure",
        "alfa", "beta", "alfa_t", "p_value", "skew", "kurtosis", "days", "total_costs", "total_funding", "total_without_best", "best_trade"]


def main():
    specs = tm.specs()
    assert len(specs) <= 5
    out = {}
    for spec in specs:
        res = evaluate(spec)
        cc = candidate_check(res)
        out[spec.name] = {
            "interval": spec.interval,
            "params": spec.params,
            "sonuc": {w: {str(m): {k: res[w][m].get(k) for k in KEEP} for m in res[w]} for w in res},
            "candidate_check": cc,
        }
        v1, v2, t1 = res["dev_valid"][1.0], res["dev_valid"][2.0], res["dev_train"][1.0]
        print(f"{spec.name}\n  egitim: ret {t1['total_return']:+.4f} sh {t1['sharpe']:.3f} alfa {t1['alfa']:+.4f} beta {t1['beta']:+.3f} t {t1['alfa_t']:+.3f} tr {t1['trades']}"
              f"\n  dogrulama 1x: ret {v1['total_return']:+.4f} sh {v1['sharpe']:.3f} dd {v1['max_drawdown']:.4f} tr {v1['trades']} alfa {v1['alfa']:+.4f} beta {v1['beta']:+.3f} t {v1['alfa_t']:+.3f}"
              f"\n  dogrulama 2x: ret {v2['total_return']:+.4f} sh {v2['sharpe']:.3f}\n  aday: {cc}", flush=True)

    # Deflated Sharpe
    tr = ledger.trials(tm.FAMILY)
    base = tr[(tr["pencere"] == "dev_train") & (tr["maliyet_kat"] == 1.0)]
    srs = base["olcu"].map(lambda m: m.get("sharpe")).astype(float)
    srs = srs[np.isfinite(srs)]
    n_trials = int(len(base))
    var = float(np.var(srs, ddof=1))
    for name, o in out.items():
        v = o["sonuc"]["dev_valid"]["1.0"]
        o["dsr"] = deflated_sharpe(v["sharpe"], int(v["days"]), n_trials, var, v["skew"], v["kurtosis"])
        o["dsr_girdi"] = {"deneme": n_trials, "sharpe_varyans": var}
        print(f"DSR {name}: {o['dsr']:.4f} (deneme {n_trials}, varyans {var:.3f})", flush=True)

    # Al-tut kıyası (vadeli BTC/ETH/SOL eşit ağırlık; stratejilerin alfa kıyası)
    spec0 = specs[0]
    bench = benchmark_daily(spec0)
    bh = {}
    for w in ("dev_train", "dev_valid"):
        s, e = PERIODS[w]
        b = window(bench, s, e)
        eq = (1 + b).cumprod()
        bh[w] = {"total_return": float(eq.iloc[-1] - 1), "max_drawdown": float((eq / eq.cummax() - 1).min()),
                 "sharpe": float(b.mean() / b.std() * math.sqrt(365))}
    out["_al_tut_vadeli_esit"] = bh
    print("al-tut", bh, flush=True)

    # dev_valid günlük getiri korelasyonu
    s, e = PERIODS["dev_valid"]
    daily = {}
    for spec in specs:
        r = run(spec).returns
        daily[spec.name] = daily_returns(window(r, s, e))
    corr = pd.DataFrame(daily).corr()
    out["_korelasyon_dev_valid"] = corr.round(4).to_dict()
    print(corr.round(3).to_string(), flush=True)
    (K / "dogrulama_sonuc.json").write_text(json.dumps(out, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    print("BITTI", flush=True)


if __name__ == "__main__":
    main()
