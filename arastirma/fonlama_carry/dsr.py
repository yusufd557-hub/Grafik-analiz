"""Deflated Sharpe: deneme sayısı = defterde pencere=='dev_train' ve maliyet_kat==1.0 satırları;
varyans = bu satırların yıllık Sharpe değerlerinin varyansı (NaN Sharpe'lı satırlar — hiç işlem yok —
sayıya dahil, varyansa dahil değil); çarpıklık/basıklık = dev_valid günlük getirilerinden (summarize)."""
import json
from pathlib import Path

import numpy as np
from grafik_analiz.research import deflated_sharpe
from grafik_analiz.research.ledger import trials

KLASOR = Path(__file__).resolve().parent
t = trials("fonlama_carry")
tr = t[(t["pencere"] == "dev_train") & (t["maliyet_kat"] == 1.0)].copy()
tr["sharpe"] = tr["olcu"].apply(lambda o: o.get("sharpe"))
tr["kind"] = tr["parametreler"].apply(lambda p: p.get("kind"))
s = tr["sharpe"].astype(float)
N = len(tr)
var = float(np.nanvar(s, ddof=1))
print(f"deneme satiri N={N}, finite Sharpe={int(s.notna().sum())}, var={var:.4f}, ort={np.nanmean(s):.3f}, maks={np.nanmax(s):.3f}")
car = tr[tr["kind"] == "carry"]["sharpe"].astype(float)
var_c = float(np.nanvar(car, ddof=1))
print(f"yalniz carry: N={len(car)}, var={var_c:.4f}, ort={np.nanmean(car):.3f}")
gamma = 0.5772156649
from scipy import stats
def sr0(n, v):
    return np.sqrt(v) * ((1 - gamma) * stats.norm.ppf(1 - 1 / n) + gamma * stats.norm.ppf(1 - 1 / (n * np.e)))
print(f"SR0 (yillik, tum aile) = {sr0(N, var):.3f}; SR0 (yalniz carry) = {sr0(len(car), var_c):.3f}")
d = json.loads((KLASOR / "dondurulmus_sonuclar.json").read_text(encoding="utf-8"))
out = {"N": N, "var": var, "N_carry": int(len(car)), "var_carry": var_c, "sr0": float(sr0(N, var)), "sr0_carry": float(sr0(len(car), var_c)), "dsr": {}}
for ad, v in d.items():
    m = v["sonuclar"]["dev_valid"]["1.0"]
    dsr = deflated_sharpe(m["sharpe"], m["days"], N, var, m["skew"], m["kurtosis"])
    dsr_c = deflated_sharpe(m["sharpe"], m["days"], len(car), var_c, m["skew"], m["kurtosis"])
    out["dsr"][ad] = {"sharpe_valid": m["sharpe"], "gun": m["days"], "skew": m["skew"], "kurt": m["kurtosis"], "dsr": dsr, "dsr_carry_alt": dsr_c}
    print(f"{ad:36s} SR={m['sharpe']:.3f} gun={m['days']} skew={m['skew']:.3f} kurt={m['kurtosis']:.3f} DSR={dsr:.4f} (yalniz carry denemeleriyle {dsr_c:.4f})")
(KLASOR / "dsr.json").write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
