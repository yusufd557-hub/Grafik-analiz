"""Aşama 7: ikinci (200 günlük) trend filtresi — 2022 tipi ayı piyasası rallilerinde alımı önler mi? (yalnız dev_train)"""
from ortak import calistir
from tarama6 import COMMON_1H, COMMON_15M, COMP_1H, COMP_15M

CORE = {"kind": "ret", "n": 4, "entry": 3.0, "exit": None, "max_hold": 12, **COMMON_1H}
configs = [
    ("futures", "PORT3", "1h", {**CORE, "trend2_n": 4800}),
    ("futures", "PORT3", "1h", {**COMMON_1H, "trend2_n": 4800, "components": COMP_1H}),
    ("spot", "PORT3", "1h", {**COMMON_1H, "trend2_n": 4800, "components": COMP_1H}),
    ("futures", "PORT3", "15m", {**COMMON_15M, "trend2_n": 19200, "components": COMP_15M}),
]

if __name__ == "__main__":
    calistir(configs, "tarama7.csv", mults=(1.0, 2.0))
