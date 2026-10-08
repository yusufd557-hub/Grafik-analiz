"""Aşama 6: dip alımı toplulukları (bileşen pozisyonlarının ortalaması), 1h ve 15m (yalnız dev_train, 1× ve 2× maliyet)."""
from ortak import calistir

COMMON_1H = {"side": "long", "trend_n": 1200, "trend_mode": "with"}
COMP_1H = [
    {"kind": "ret", "n": 4, "entry": 3.0, "exit": None, "max_hold": 12},
    {"kind": "ret", "n": 1, "entry": 4.0, "exit": None, "max_hold": 12},
    {"kind": "vwap", "n": 72, "entry": 3.0, "exit": 0.0, "max_hold": 48},
    {"kind": "rsi", "n": 6, "entry": 3.5, "exit": 0.0, "max_hold": 48},
]
COMP_RET_1H = [{"kind": "ret", "n": n, "entry": 3.0, "exit": None, "max_hold": 12} for n in (2, 4, 8)]
COMMON_15M = {"side": "long", "trend_n": 4800, "trend_mode": "with", "vol_n": 2000}
COMP_15M = [
    {"kind": "ret", "n": 16, "entry": 3.0, "exit": None, "max_hold": 48},
    {"kind": "ret", "n": 4, "entry": 4.0, "exit": None, "max_hold": 48},
    {"kind": "vwap", "n": 288, "entry": 3.0, "exit": 0.0, "max_hold": 192},
    {"kind": "rsi", "n": 6, "entry": 3.5, "exit": 0.0, "max_hold": 96},
]

configs = [
    ("futures", "PORT3", "1h", {**COMMON_1H, "components": COMP_1H}),
    ("spot", "PORT3", "1h", {**COMMON_1H, "components": COMP_1H}),
    ("futures", "PORT3", "1h", {**COMMON_1H, "components": COMP_RET_1H}),
    ("futures", "PORT3", "15m", {**COMMON_15M, "components": COMP_15M}),
]

if __name__ == "__main__":
    calistir(configs, "tarama6.csv", mults=(1.0, 2.0))
