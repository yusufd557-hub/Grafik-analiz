"""Aşama 4: yükselen trendde dip alımı — spot (2017'den, 2018 ayı piyasası dahil), 15m ve 4h karşılıkları (yalnız dev_train)."""
from ortak import calistir

L = {"side": "long"}
configs = []
# (a) spot 1h PORT3
for p in (
    {"kind": "ret", "n": 4, "entry": 3.0, "exit": None, "max_hold": 12, "trend_n": 480},
    {"kind": "ret", "n": 4, "entry": 3.0, "exit": None, "max_hold": 24, "trend_n": 480},
    {"kind": "ret", "n": 4, "entry": 3.0, "exit": None, "max_hold": 12, "trend_n": 1200},
    {"kind": "ret", "n": 4, "entry": 2.5, "exit": None, "max_hold": 6, "trend_n": 480},
    {"kind": "ret", "n": 1, "entry": 2.5, "exit": None, "max_hold": 24, "trend_n": 480},
    {"kind": "ret", "n": 1, "entry": 4.0, "exit": None, "max_hold": 12, "trend_n": 1200},
    {"kind": "vwap", "n": 72, "entry": 3.0, "exit": 0.0, "max_hold": 48, "trend_n": 1200},
    {"kind": "z", "n": 50, "entry": 2.5, "exit": 0.0, "max_hold": 48, "trend_n": 1200},
):
    configs.append(("spot", "PORT3", "1h", {**p, **L, "trend_mode": "with"}))
# (b) 15m vadeli PORT3 (1h karşılıkları ×4 bar)
for p in (
    {"kind": "ret", "n": 16, "entry": 3.0, "exit": None, "max_hold": 48, "trend_n": 1920},
    {"kind": "ret", "n": 16, "entry": 3.0, "exit": None, "max_hold": 96, "trend_n": 1920},
    {"kind": "ret", "n": 16, "entry": 3.0, "exit": None, "max_hold": 48, "trend_n": 4800},
    {"kind": "ret", "n": 4, "entry": 4.0, "exit": None, "max_hold": 48, "trend_n": 1920},
    {"kind": "ret", "n": 1, "entry": 5.0, "exit": None, "max_hold": 48, "trend_n": 1920},
    {"kind": "ret", "n": 1, "entry": 4.0, "exit": None, "max_hold": 24, "trend_n": 1920},
    {"kind": "vwap", "n": 288, "entry": 3.0, "exit": 0.0, "max_hold": 192, "trend_n": 4800},
    {"kind": "vwap", "n": 96, "entry": 3.0, "exit": 0.0, "max_hold": 192, "trend_n": 1920},
    {"kind": "rsi", "n": 6, "entry": 3.5, "exit": 0.0, "max_hold": 96, "trend_n": 1920},
):
    configs.append(("futures", "PORT3", "15m", {**p, **L, "trend_mode": "with", "vol_n": 2000}))
# (c) 4h vadeli PORT3 (1h karşılıkları ÷4 bar)
for p in (
    {"kind": "ret", "n": 1, "entry": 3.0, "exit": None, "max_hold": 3, "trend_n": 120},
    {"kind": "ret", "n": 1, "entry": 3.0, "exit": None, "max_hold": 6, "trend_n": 120},
    {"kind": "ret", "n": 1, "entry": 2.5, "exit": None, "max_hold": 6, "trend_n": 300},
    {"kind": "ret", "n": 2, "entry": 2.5, "exit": None, "max_hold": 6, "trend_n": 120},
    {"kind": "vwap", "n": 18, "entry": 3.0, "exit": 0.0, "max_hold": 12, "trend_n": 300},
    {"kind": "z", "n": 20, "entry": 2.5, "exit": 0.0, "max_hold": 12, "trend_n": 300},
    {"kind": "rsi", "n": 6, "entry": 3.0, "exit": 0.0, "max_hold": 12, "trend_n": 120},
):
    configs.append(("futures", "PORT3", "4h", {**p, **L, "trend_mode": "with", "vol_n": 125}))

if __name__ == "__main__":
    calistir(configs, "tarama4.csv")
