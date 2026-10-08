"""Aşama 2: 1h vadeli PORT3. Rejim filtresi (trend uzunluğu, yön, ADX) temsilci kurallarla (yalnız dev_train)."""
from ortak import calistir

REPS = [
    {"kind": "z", "n": 50, "entry": 2.5, "exit": 0.0, "max_hold": 48},
    {"kind": "vwap", "n": 72, "entry": 3.0, "exit": 0.0, "max_hold": 48},
    {"kind": "rsi", "n": 6, "entry": 3.5, "exit": 0.0, "max_hold": 48},
    {"kind": "ret", "n": 4, "entry": 3.0, "exit": None, "max_hold": 12},
    {"kind": "ret", "n": 1, "entry": 4.0, "exit": None, "max_hold": 12},
]

configs = []
for tn in (120, 1200):
    for r in REPS:
        configs.append(("futures", "PORT3", "1h", {**r, "trend_n": tn, "trend_mode": "with"}))
for side in ("long", "short"):
    for r in REPS:
        configs.append(("futures", "PORT3", "1h", {**r, "trend_n": 480, "trend_mode": "with", "side": side}))
for r in REPS:
    configs.append(("futures", "PORT3", "1h", {**r, "adx_max": 20.0}))

if __name__ == "__main__":
    calistir(configs, "tarama2.csv")
