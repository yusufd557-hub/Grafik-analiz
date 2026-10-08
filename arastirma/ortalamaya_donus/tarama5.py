"""Aşama 5: 1h 'ret' dip alımı çevresinde plato kontrolü, coin bazında ayrım, 5m karşılığı, stop/onay (yalnız dev_train)."""
from ortak import calistir

B = {"kind": "ret", "n": 4, "entry": 3.0, "exit": None, "max_hold": 12, "side": "long", "trend_n": 1200, "trend_mode": "with"}
configs = []
for tn in (720, 2400):
    for h in (12, 24):
        configs.append(("futures", "PORT3", "1h", {**B, "trend_n": tn, "max_hold": h}))
for n in (2, 6):
    for e in (2.5, 3.0, 3.5):
        configs.append(("futures", "PORT3", "1h", {**B, "n": n, "entry": e}))
for e in (2.5, 3.5):
    configs.append(("futures", "PORT3", "1h", {**B, "entry": e}))
for h in (6, 24):
    configs.append(("futures", "PORT3", "1h", {**B, "max_hold": h}))
for c in ("BTCUSDT", "ETHUSDT", "SOLUSDT"):
    configs.append(("futures", c, "1h", dict(B)))
configs.append(("futures", "PORT3", "1h", {**B, "stop_atr": 3.0}))
configs.append(("futures", "PORT3", "1h", {**B, "confirm": True}))
# 5m karşılıkları (1h ×12 bar)
configs.append(("futures", "PORT3", "5m", {**B, "n": 48, "max_hold": 144, "trend_n": 14400, "vol_n": 6000}))
configs.append(("futures", "PORT3", "5m", {**B, "n": 12, "entry": 4.0, "max_hold": 144, "trend_n": 14400, "vol_n": 6000}))

if __name__ == "__main__":
    calistir(configs, "tarama5.csv")
