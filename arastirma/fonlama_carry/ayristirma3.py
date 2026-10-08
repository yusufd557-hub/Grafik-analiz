"""Yönlü aday (sepet, negatif fonlamada uzun) dev_train yıllık dökümü. tarama2'de deftere yazılmıştır."""
import json
from ortak import ayristir
for p in ({"n": 3, "filtre": "yok", "m": 100, "tut": 2, "olcek": "mutlak", "yon": "uzun", "alt": -0.5e-4, "ust": 1.0},
          {"n": 1, "filtre": "yok", "m": 100, "tut": 2, "olcek": "mutlak", "yon": "uzun", "alt": 0.0, "ust": 1.0}):
    a = ayristir("yonlu", "SEPET3", "4h", p)
    print(json.dumps({k: (round(v, 4) if isinstance(v, float) else v) for k, v in a.items()}, default=str))
a = ayristir("carry", "BTCUSDT", "4h", {"n": 0, "giris": 0.0, "cikis": 0.0, "son_neg": False})
print("BTC surekli", json.dumps({k: (round(v, 4) if isinstance(v, float) else v) for k, v in a.items()}, default=str))
a = ayristir("yonlu", "SEPET3", "4h", {"n": 1, "filtre": "yok", "m": 100, "tut": 2, "olcek": "mutlak", "yon": "uzun", "alt": -0.5e-4, "ust": 1.0})
print("n1 alt-5e-5 tut2", json.dumps({k: (round(v, 4) if isinstance(v, float) else v) for k, v in a.items()}, default=str))
