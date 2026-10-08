"""Ana carry varyantlarının dev_train getiri ayrıştırması (fiyat/baz, maliyet, fonlama) ve yıllık döküm.
Hepsi tarama1'de evaluate() ile deftere yazılmıştır."""
import json
from ortak import ayristir

for u in ("BTCUSDT", "ETHUSDT", "SOLUSDT", "SEPET3"):
    for p in ({"n": 0, "giris": 0.0, "cikis": 0.0, "son_neg": False},
              {"n": 3, "giris": 1e-4, "cikis": 0.0, "son_neg": False},
              {"n": 1, "giris": 1e-4, "cikis": 0.0, "son_neg": False}):
        a = ayristir("carry", u, "4h", p)
        print(u, p["n"], p["giris"], json.dumps({k: (round(v, 4) if isinstance(v, float) else v) for k, v in a.items()}, default=str))
