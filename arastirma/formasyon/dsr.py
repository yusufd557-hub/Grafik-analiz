"""Deflated Sharpe (Bailey & López de Prado 2014) dondurulan yapılandırmalar için.

Deneme sayısı: defterde pencere=='dev_train' ve maliyet_kat==1.0 satırları.
Deneme Sharpe varyansı: bu satırların yıllık Sharpe değerleri (boş/NaN olanlar hariç).
Gözlenen Sharpe, çarpıklık, basıklık: dev_valid 1× (summarize, dondurulmus_sonuclar.json).
Gün sayısı: dev_valid günlük getiri sayısı (01.01.2024–30.06.2025 = 547).
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd

from grafik_analiz.research import PERIODS, deflated_sharpe
from grafik_analiz.research.ledger import trials

HERE = Path(__file__).resolve().parent
res = json.loads((HERE / "dondurulmus_sonuclar.json").read_text(encoding="utf-8"))
t = trials("formasyon")
tr = t[(t["pencere"] == "dev_train") & (t["maliyet_kat"] == 1.0)]
sh = pd.to_numeric(tr["olcu"].apply(lambda o: o.get("sharpe")), errors="coerce")
n_trials = len(tr)
var = float(np.nanvar(sh.to_numpy(dtype=float), ddof=1))
start, end = PERIODS["dev_valid"]
n_days = int((end - start).days)
print(f"deneme sayısı (dev_train 1× satırı): {n_trials}; Sharpe'ı tanımlı: {int(sh.notna().sum())}; yıllık Sharpe varyansı: {var:.4f}; dev_valid gün: {n_days}")
print(f"dev_train 1× Sharpe dağılımı: ortalama {np.nanmean(sh):.3f}, medyan {np.nanmedian(sh):.3f}, en yüksek {np.nanmax(sh):.3f}")
out = {"deneme_sayisi": n_trials, "sharpe_varyansi": var, "gun": n_days, "stratejiler": {}}
for name, r in res.items():
    v = r["sonuc"]["dev_valid"]["1.0"]
    d = deflated_sharpe(v["sharpe"], n_days, n_trials, var, v["skew"], v["kurtosis"])
    out["stratejiler"][name] = {"sharpe": v["sharpe"], "skew": v["skew"], "kurtosis": v["kurtosis"], "dsr": d}
    print(f"{name}: dev_valid Sharpe {v['sharpe']:.3f} çarpıklık {v['skew']:.3f} basıklık {v['kurtosis']:.2f} → DSR {d:.4f}")
(HERE / "dsr.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
