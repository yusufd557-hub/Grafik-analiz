"""Aşama 1: 1h vadeli, 3 coin portföyü. Dört sapma ölçüsünün kaba haritası (yalnız dev_train)."""
from ortak import calistir

configs = []
for trend in ("none", "with"):
    tp = {"trend_n": 480, "trend_mode": "with"} if trend == "with" else {}
    for n in (20, 50):
        for e in (2.0, 2.5, 3.0):
            configs.append(("futures", "PORT3", "1h", {"kind": "z", "n": n, "entry": e, "exit": 0.0, "max_hold": 48, **tp}))
    for n in (24, 72):
        for e in (2.0, 3.0, 4.0):
            configs.append(("futures", "PORT3", "1h", {"kind": "vwap", "n": n, "entry": e, "exit": 0.0, "max_hold": 48, **tp}))
    for n in (6, 14):
        for e in (2.5, 3.0, 3.5):
            configs.append(("futures", "PORT3", "1h", {"kind": "rsi", "n": n, "entry": e, "exit": 0.0, "max_hold": 48, **tp}))
    for n in (1, 4):
        for e in (3.0, 4.0, 5.0):
            configs.append(("futures", "PORT3", "1h", {"kind": "ret", "n": n, "entry": e, "exit": None, "max_hold": 12, **tp}))

if __name__ == "__main__":
    calistir(configs, "tarama1.csv")
