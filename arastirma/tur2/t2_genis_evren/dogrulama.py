"""Dondurulan yapılandırmaların TEK SEFERLİK iç doğrulama (dev_valid) değerlendirmesi.

Dondurma kararı NOTLAR.md "Dondurma kararı" bölümünde dev_valid'den önce yazıldı;
assert_causal: dondurma_kontrol.log. Her spec için bir kez `evaluate(spec)` (dev_train +
dev_valid, 1× ve 2×; deftere yazılır) ve `candidate_check`. Ardından Deflated Sharpe
(deneme sayısı = defterde pencere=="dev_train" ve maliyet_kat==1.0 satırları), al-tut
kıyası, ortalama brüt maruziyet ve günlük getiri korelasyonu (betimleyici).
Sonuç: dogrulama_sonuc.json.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

from grafik_analiz.research import protocol
from grafik_analiz.research.evaluate import benchmark_daily, candidate_check, evaluate, run
from grafik_analiz.research.ledger import _clean, trials
from grafik_analiz.research.metrics import daily_returns, deflated_sharpe, window
from grafik_analiz.strategies.t2_genis_evren import FAMILY, specs

assert protocol.PROTOCOL_VERSION == "2"
KLASOR = Path(__file__).resolve().parent
T0, T1 = protocol.PERIODS["dev_train"]
V0, V1 = protocol.PERIODS["dev_valid"]


def main():
    out, ham, gunluk = {}, {}, {}
    for s in specs():
        res = evaluate(s)
        chk = {k: bool(v) for k, v in candidate_check(res).items()}
        ham[s.name] = res
        out[s.name] = {"sonuclar": _clean(res), "candidate_check": chk}
        v1, v2 = res["dev_valid"][1.0], res["dev_valid"][2.0]
        print(
            f"{s.name}: dev_valid 1× {v1['total_return']:+.4f} 2× {v2['total_return']:+.4f} Sharpe {v1['sharpe']:.3f} "
            f"(2× {v2['sharpe']:.3f}) MDD {v1['max_drawdown']:.4f} işlem {v1['trades']} alfa {v1['alfa']:+.4f} "
            f"beta {v1['beta']:.4f} alfa_t {v1['alfa_t']:.2f} | aday: {chk['aday']}",
            flush=True,
        )
        r = run(s, "dev", 1.0)
        gunluk[s.name] = daily_returns(window(r.returns, V0, V1))
        out[s.name]["ort_brut_maruziyet"] = {
            "dev_train": float(window(r.exposure, T0, T1).mean()),
            "dev_valid": float(window(r.exposure, V0, V1).mean()),
        }

    tr = trials(FAMILY)
    tr = tr[(tr["pencere"] == "dev_train") & (tr["maliyet_kat"] == 1.0)]
    sh = np.array([o.get("sharpe") for o in tr["olcu"]], dtype=float)
    sh = sh[np.isfinite(sh)]
    n_trials, var = int(len(tr)), float(np.var(sh, ddof=1))
    for name, o in out.items():
        v = ham[name]["dev_valid"][1.0]
        o["dsr"] = deflated_sharpe(v["sharpe"], int(v["days"]), n_trials, var, v["skew"], v["kurtosis"])
    out["_dsr"] = {"deneme": n_trials, "egitim_sharpe_varyansi": var, "sonlu_sharpe": int(len(sh))}

    altut = {}
    dummy = type("S", (), {"legs": (("futures", "BTCUSDT"),)})()
    b = benchmark_daily(dummy, "dev")
    for w, (a, z) in (("dev_train", (T0, T1)), ("dev_valid", (V0, V1))):
        bv = b[(b.index < z) if a is None else ((b.index >= a) & (b.index < z))]
        if w == "dev_train":
            bv = bv[bv.index >= pd.Timestamp("2020-01-01", tz="UTC")]
        eq = (1 + bv).cumprod()
        altut[w] = {
            "getiri": float(eq.iloc[-1] - 1),
            "sharpe": float(bv.mean() / bv.std() * math.sqrt(365)),
            "en_buyuk_dusus": float((eq / eq.cummax() - 1).min()),
        }
    out["_altut_vadeli_btc_eth_sol"] = altut
    kor = pd.DataFrame(gunluk).corr().round(3)
    out["_korelasyon_dev_valid"] = kor.to_dict()
    print(json.dumps({k: out[k] for k in ("_dsr", "_altut_vadeli_btc_eth_sol")}, indent=1), flush=True)
    print({k: round(v["dsr"], 4) for k, v in out.items() if not k.startswith("_")}, flush=True)
    print({k: v["ort_brut_maruziyet"] for k, v in out.items() if not k.startswith("_")}, flush=True)
    print(kor.to_string(), flush=True)
    (KLASOR / "dogrulama_sonuc.json").write_text(json.dumps(_clean(out), ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    print("BITTI", flush=True)


if __name__ == "__main__":
    main()
