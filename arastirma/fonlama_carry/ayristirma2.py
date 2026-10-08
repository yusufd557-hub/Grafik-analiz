"""Sepet carry adaylarının dev_train yıllık getirisi, yıllık işlem sayısı ve ayrıştırması.
Hepsi tarama1/tarama2'de evaluate() ile deftere yazılmıştır."""
import json
from ortak import ayristir

for iv, n, g, c in (("4h", 1, 1.5e-4, 0.5e-4), ("4h", 3, 1.5e-4, 0.5e-4), ("4h", 7, 1.5e-4, 0.5e-4),
                    ("4h", 3, 0.9e-4, 0.0), ("4h", 7, 0.5e-4, -0.5e-4), ("1d", 3, 0.5e-4, 0.0)):
    a = ayristir("carry", "SEPET3", iv, {"n": n, "giris": g, "cikis": c, "son_neg": False})
    print(iv, n, g, c, json.dumps({k: (round(v, 4) if isinstance(v, float) else v) for k, v in a.items()}, default=str))
