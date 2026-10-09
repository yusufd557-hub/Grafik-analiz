"""Tarama 1: tek faktörler, 1d, temel ayarlar (yalnız dev_train, 1×)."""
from pathlib import Path

from ortak import run_grid

HERE = Path(__file__).resolve().parent
configs = []
for skor in ["rev_1", "rev_3", "mom_7", "mom_14", "mom_28", "mom_56", "mom_90", "mom_28_7"]:
    for reb in (1, 7):
        for k in (0.2, 0.5):
            configs.append(("1d", {"skor": skor, "reb": reb, "k_oran": k}))
for F in (1, 3, 7, 14, 30):
    for reb in (1, 7):
        for k in (0.2, 0.5):
            configs.append(("1d", {"skor": f"fon_{F}", "reb": reb, "k_oran": k}))
for V in (14, 30, 60):
    for k in (0.2, 0.5):
        for notr in ("dolar", "beta"):
            configs.append(("1d", {"skor": f"oyn_{V}", "reb": 7, "k_oran": k, "notr": notr}))
print(len(configs), "yapılandırma", flush=True)
run_grid(configs, HERE / "tarama1.csv")
