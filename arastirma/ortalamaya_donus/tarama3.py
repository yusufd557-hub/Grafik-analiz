"""Aşama 3: 1h vadeli PORT3, yalnız alım (yükselen trendde dip alımı). Kaba ızgara (yalnız dev_train)."""
from ortak import calistir

REPS = [
    {"kind": "z", "n": 50, "entry": 2.5, "exit": 0.0, "max_hold": 48},
    {"kind": "vwap", "n": 72, "entry": 3.0, "exit": 0.0, "max_hold": 48},
    {"kind": "rsi", "n": 6, "entry": 3.5, "exit": 0.0, "max_hold": 48},
    {"kind": "ret", "n": 4, "entry": 3.0, "exit": None, "max_hold": 12},
    {"kind": "ret", "n": 1, "entry": 4.0, "exit": None, "max_hold": 12},
]
L = {"side": "long"}
T = {"trend_n": 480, "trend_mode": "with"}

configs = []
for r in REPS:  # trend filtresi olmadan yalnız alım
    configs.append(("futures", "PORT3", "1h", {**r, **L}))
for r in REPS:  # daha uzun trend filtresi
    configs.append(("futures", "PORT3", "1h", {**r, **L, "trend_n": 1200, "trend_mode": "with"}))
for n in (1, 4, 8):
    for e in (2.5, 3.0, 4.0):
        for h in (6, 24):
            configs.append(("futures", "PORT3", "1h", {"kind": "ret", "n": n, "entry": e, "exit": None, "max_hold": h, **L, **T}))
for n, e in ((24, 2.0), (24, 3.0), (72, 2.0), (72, 4.0), (168, 3.0), (168, 4.0)):
    configs.append(("futures", "PORT3", "1h", {"kind": "vwap", "n": n, "entry": e, "exit": 0.0, "max_hold": 48, **L, **T}))
for ex, h in ((-0.5, 48), (1.0, 48), (0.0, 24), (0.0, 96)):
    configs.append(("futures", "PORT3", "1h", {"kind": "vwap", "n": 72, "entry": 3.0, "exit": ex, "max_hold": h, **L, **T}))

if __name__ == "__main__":
    calistir(configs, "tarama3.csv")
