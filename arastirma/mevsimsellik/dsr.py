"""Deflated Sharpe (Bailey & López de Prado 2014) — dondurulmuş yapılandırmalar için.

Deneme sayısı: defterdeki pencere=='dev_train' ve maliyet_kat==1.0 satırları.
Varyans: bu satırların yıllık Sharpe değerlerinin varyansı.
Çarpıklık/basıklık ve gün sayısı: dev_valid günlük getirileri (summarize).
Muhafazakâr sürüm: deneme sayısına keşifte incelenen 660 betimsel hücre eklenir.
"""
import json
from pathlib import Path

import numpy as np

from grafik_analiz.research import deflated_sharpe
from grafik_analiz.research.ledger import trials

KESIF_HUCRE = 660
here = Path(__file__).resolve().parent
t = trials("mevsimsellik")
tr = t[(t.pencere == "dev_train") & (t.maliyet_kat == 1.0)]
sh = np.array([r.get("sharpe") for r in tr.olcu], dtype=float)
sh = sh[np.isfinite(sh)]
n_trials = len(tr)
var = float(np.var(sh, ddof=1))
print(f"deneme (dev_train 1x satırı) = {n_trials}, benzersiz ad = {tr.strateji.nunique()}, Sharpe varyansı = {var:.4f} (std {np.sqrt(var):.3f}), "
      f"dev_valid satırı = {int((t.pencere == 'dev_valid').sum())}")
res = json.loads((here / "dondurulmus_sonuclar.json").read_text(encoding="utf-8"))
out = {}
for name, r in res.items():
    v = r["metrics"]["dev_valid"]["1.0"]
    tt = r["metrics"]["dev_train"]["1.0"]
    days = int(v["days"]) + 1
    d1 = deflated_sharpe(v["sharpe"], days, n_trials, var, v["skew"], v["kurtosis"])
    d2 = deflated_sharpe(v["sharpe"], days, n_trials + KESIF_HUCRE, var, v["skew"], v["kurtosis"])
    # bilgi için: dev_train Sharpe'ının kendi DSR'si (seçim yanlılığı dahil)
    d3 = deflated_sharpe(tt["sharpe"], int(tt["days"]) + 1, n_trials, var, tt["skew"], tt["kurtosis"])
    out[name] = {"dsr_dev_valid": d1, "dsr_dev_valid_muhafazakar": d2, "dsr_dev_train": d3, "n_days_valid": days,
                 "skew_valid": v["skew"], "kurt_valid": v["kurtosis"], "sharpe_valid": v["sharpe"]}
    print(f"{name:30s} SR_valid {v['sharpe']:6.2f} skew {v['skew']:5.2f} kurt {v['kurtosis']:6.2f} gün {days} -> DSR {d1:.4f} (muhafazakâr {d2:.4f}); dev_train SR {tt['sharpe']:.2f} DSR {d3:.4f}")
(here / "dsr.json").write_text(json.dumps({"n_trials": n_trials, "sharpe_var": var, "kesif_hucre": KESIF_HUCRE, "sonuc": out}, indent=1), encoding="utf-8")
