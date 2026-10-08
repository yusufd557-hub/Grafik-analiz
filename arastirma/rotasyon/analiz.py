"""Dondurulmuş sonuçların analizi: Deflated Sharpe, al-tut karşılaştırması, yıllık döküm.

Yeni yapılandırma değerlendirmez; al-tut ölçümleri deftere yazılmaz (record=False).
"""
import json
import pickle
from pathlib import Path

import numpy as np
import pandas as pd

from grafik_analiz.research import COSTS, StrategySpec, deflated_sharpe, evaluate, run
from grafik_analiz.research.ledger import trials
from grafik_analiz.research.protocol import DEV_TRAIN_END
from grafik_analiz.strategies.rotasyon import specs

KLASOR = Path(__file__).resolve().parent
ham = pickle.load(open(KLASOR / "dondurulmus_sonuclar.pkl", "rb"))

# ---- Deflated Sharpe
t = trials("rotasyon")
dt = t[(t["pencere"] == "dev_train") & (t["maliyet_kat"] == 1.0)]
sr = dt["olcu"].apply(lambda o: o.get("sharpe")).astype(float).dropna()
n_trials = len(dt)
n_unique = dt["parametreler"].apply(lambda p: json.dumps(p, sort_keys=True)).nunique()
var_sr = float(np.var(sr, ddof=1))
print(f"deneme (dev_train, 1x satır): {n_trials}  benzersiz yapılandırma: {n_unique}  Sharpe varyansı: {var_sr:.4f}  ort: {sr.mean():.3f}  maks: {sr.max():.3f}")
print("dev_valid satırı:", int((t["pencere"] == "dev_valid").sum()) // 2, "yapılandırma")

ozet = {"n_trials": n_trials, "n_unique": n_unique, "var_sr": var_sr, "stratejiler": {}}
for spec in specs():
    res = ham[spec.name]["sonuc"]
    v1 = res["dev_valid"][1.0]
    v2 = res["dev_valid"][2.0]
    t1 = res["dev_train"][1.0]
    t2 = res["dev_train"][2.0]
    dsr_v = deflated_sharpe(v1["sharpe"], v1["days"], n_trials, var_sr, v1["skew"], v1["kurtosis"])
    dsr_t = deflated_sharpe(t1["sharpe"], t1["days"], n_trials, var_sr, t1["skew"], t1["kurtosis"])
    per_side = COSTS[spec.legs[0][0]].per_side
    ciro_v = v1["total_costs"] / per_side / (v1["days"] / 365.25)
    ciro_t = t1["total_costs"] / per_side / (t1["days"] / 365.25)
    # dönem içi döküm (dondurulmuş yapılandırma, yeni değerlendirme değil)
    r = run(spec, "dev").returns
    yil = (1 + r).groupby(r.index.year).prod() - 1
    yari = {}
    rv = r[r.index >= DEV_TRAIN_END]
    for ad, (a, b) in {"2024-H1": ("2024-01-01", "2024-07-01"), "2024-H2": ("2024-07-01", "2025-01-01"), "2025-H1": ("2025-01-01", "2025-07-01")}.items():
        x = rv[(rv.index >= pd.Timestamp(a, tz="UTC")) & (rv.index < pd.Timestamp(b, tz="UTC"))]
        yari[ad] = float((1 + x).prod() - 1)
    ozet["stratejiler"][spec.name] = {
        "dsr_dev_valid": dsr_v,
        "dsr_dev_train": dsr_t,
        "ciro_yillik_valid": ciro_v,
        "ciro_yillik_train": ciro_t,
        "yillik": {str(k): float(v) for k, v in yil.items()},
        "yarim_yil_valid": yari,
        "aday": ham[spec.name]["aday"],
        "train": {k: t1.get(k) for k in ("total_return", "cagr", "sharpe", "max_drawdown", "trades", "exposure", "total_costs", "total_funding", "skew", "kurtosis", "days", "p_value")},
        "train_2x": {k: t2.get(k) for k in ("total_return", "sharpe")},
        "valid": {k: v1.get(k) for k in ("total_return", "cagr", "sharpe", "max_drawdown", "trades", "exposure", "total_costs", "total_funding", "skew", "kurtosis", "days", "p_value", "win_rate", "profit_factor", "total_without_best")},
        "valid_2x": {k: v2.get(k) for k in ("total_return", "sharpe", "max_drawdown")},
    }
    print(spec.name, f"DSR(valid)={dsr_v:.4f} DSR(train)={dsr_t:.4f} ciro/yıl train={ciro_t:.1f} valid={ciro_v:.1f}")
    print("   yıllık:", {k: round(v, 3) for k, v in ozet["stratejiler"][spec.name]["yillik"].items()}, "yarım yıl:", {k: round(v, 3) for k, v in yari.items()})
    print("   valid:", {k: (round(v, 4) if isinstance(v, float) else v) for k, v in ozet["stratejiler"][spec.name]["valid"].items()})

# ---- al-tut (deftere yazılmaz)
def hep(data, funding):
    return {leg: pd.Series(1.0, index=df.index) for leg, df in data.items()}

bh = {}
for ad, legs in {
    "BTC spot": (("spot", "BTCUSDT"),),
    "ETH spot": (("spot", "ETHUSDT"),),
    "SOL spot": (("spot", "SOLUSDT"),),
    "BTC/ETH/SOL spot eşit ağırlık": (("spot", "BTCUSDT"), ("spot", "ETHUSDT"), ("spot", "SOLUSDT")),
    "BTC vadeli uzun (fonlama dahil)": (("futures", "BTCUSDT"),),
}.items():
    res = evaluate(StrategySpec("al_tut", "rotasyon_karsilastirma", "1d", legs, hep, {}), record=False)
    bh[ad] = {w: {k: res[w][1.0].get(k) for k in ("start", "total_return", "cagr", "sharpe", "max_drawdown")} for w in ("dev_train", "dev_valid")}
    print("al-tut", ad, {w: {k: (round(v, 3) if isinstance(v, float) else v) for k, v in d.items()} for w, d in bh[ad].items()})
ozet["al_tut"] = bh
(KLASOR / "analiz.json").write_text(json.dumps(ozet, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
