"""Tarama 3 (kesintiden sonra): öne çıkan bileşiklerin komşulukları ve artık momentum, 1d
(yalnız dev_train, 1× ve 2×)."""
from pathlib import Path

from ortak import run_grid

HERE = Path(__file__).resolve().parent
C = []
for skor in ["fon_3+mom_90", "fon_3+mom_28+oyn_60", "fon_3+mom_28+mom_90"]:
    C.append(("1d", {"skor": skor, "reb": 3, "k_oran": 0.5}))
    C.append(("1d", {"skor": skor, "reb": 7, "k_oran": 0.33}))
    C.append(("1d", {"skor": skor, "reb": 7, "k_oran": 0.5, "boyut": "ters_oyn"}))
    C.append(("1d", {"skor": skor, "reb": 7, "k_oran": 0.5, "notr": "beta"}))
    C.append(("1d", {"skor": skor, "reb": 1, "k_oran": 0.5, "tampon": 0.1}))
for skor in ["fon_7+mom_90", "fon_1+mom_90", "fon_7+mom_28+oyn_60", "fon_3+mom_90+oyn_60",
             "fon_3+mom_56+oyn_60", "fon_3+mom_28+oyn_30", "fon_3+oyn_60", "fon_3+mom_28+mom_90+oyn_60"]:
    C.append(("1d", {"skor": skor, "reb": 7, "k_oran": 0.5}))
for skor in ["rmom_28", "rmom_90", "fon_3+rmom_90", "fon_3+rmom_28+oyn_60"]:
    C.append(("1d", {"skor": skor, "reb": 7, "k_oran": 0.5}))
print(len(C), "yapılandırma", flush=True)
run_grid(C, HERE / "tarama3.csv", mults=(1.0, 2.0))
