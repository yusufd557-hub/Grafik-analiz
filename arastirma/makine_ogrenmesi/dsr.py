"""Dondurulan yapılandırmalar için Deflated Sharpe (dev_valid) ve özet tablo.

Deneme sayısı: defterde pencere=="dev_train" ve maliyet_kat==1.0 olan satırlar (dondurulan
yapılandırmaların son değerlendirmesi dahil). Sharpe varyansı: bu satırların yıllık Sharpe
değerlerinin örneklem varyansı. Çarpıklık/basıklık: dev_valid günlük getirileri (summarize).
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd

from grafik_analiz.research import deflated_sharpe
from grafik_analiz.research.ledger import trials
from grafik_analiz.strategies.makine_ogrenmesi import FAMILY

HERE = Path(__file__).resolve().parent
t = trials(FAMILY)
tr = t[(t["pencere"] == "dev_train") & (t["maliyet_kat"] == 1.0)]
sh = np.array([o.get("sharpe") for o in tr["olcu"]], dtype=float)
sh = sh[np.isfinite(sh)]
n_trials = int(len(tr))
var_sh = float(np.var(sh, ddof=1))
print(f"deneme sayısı={n_trials} (farklı ad: {tr['strateji'].nunique()}), dev_train 1× Sharpe varyansı={var_sh:.4f}, "
      f"ort={sh.mean():.3f}, en büyük={sh.max():.3f}; dev_valid satırı={int((t['pencere'] == 'dev_valid').sum())}")
rows = []
gunluk = {}
for f in sorted((HERE / "dondurulmus").glob("*.json")):
    d = json.loads(f.read_text(encoding="utf-8"))
    v = d["metrics"]["dev_valid"]["1.0"]
    n = d["ek"]["1.0"]["n_gun"]
    dsr = deflated_sharpe(v["sharpe"], n, n_trials, var_sh, v["skew"], v["kurtosis"])
    dsr1 = deflated_sharpe(v["sharpe"], n, 1, 0.0, v["skew"], v["kurtosis"])
    gunluk[d["ad"]] = pd.Series(d["ek"]["gunluk_1x"])
    rows.append({"ad": d["ad"], "sr_valid": v["sharpe"], "n_gun": n, "skew": v["skew"], "kurt": v["kurtosis"],
                 "DSR": dsr, "PSR(0)": dsr1, "aday": d["candidate_check"]["aday"]})
out = pd.DataFrame(rows)
pd.set_option("display.width", 250)
print(out.to_string(index=False, float_format=lambda x: f"{x:.4f}"))
if len(gunluk) > 1:
    print("dev_valid günlük getiri korelasyonu (1×):")
    print(pd.DataFrame(gunluk).corr().round(3).to_string())
(HERE / "dsr_sonuc.json").write_text(json.dumps({"n_trials": n_trials, "sharpe_var": var_sh, "satirlar": rows},
                                                ensure_ascii=False, indent=1, default=float), encoding="utf-8")
