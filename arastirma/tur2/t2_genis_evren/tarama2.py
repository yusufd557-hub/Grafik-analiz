"""Tarama 2: bileşikler ve en iyi tek faktörlerin komşulukları, 1d (yalnız dev_train, 1× ve 2×)."""
from pathlib import Path

from ortak import run_grid

HERE = Path(__file__).resolve().parent
C = []
for skor in ["fon_3+mom_28", "fon_3+mom_90", "fon_7+mom_28", "fon_3+mom_7", "fon_3+mom_28+mom_90", "fon_3+mom_28+oyn_60"]:
    for reb in (1, 7):
        for k in (0.2, 0.5):
            C.append(("1d", {"skor": skor, "reb": reb, "k_oran": k}))
for skor in ["fon_3", "mom_28", "mom_90"]:
    for reb in (3, 14):
        for k in (0.2, 0.5):
            C.append(("1d", {"skor": skor, "reb": reb, "k_oran": k}))
    C.append(("1d", {"skor": skor, "reb": 7, "k_oran": 0.5, "notr": "beta"}))
    C.append(("1d", {"skor": skor, "reb": 7, "k_oran": 0.5, "boyut": "ters_oyn"}))
    C.append(("1d", {"skor": skor, "reb": 7, "k_oran": 0.5, "boyut": "sira"}))
    C.append(("1d", {"skor": skor, "reb": 7, "k_oran": 0.5, "top_n": 20}))
    C.append(("1d", {"skor": skor, "reb": 7, "k_oran": 0.33}))
C.append(("1d", {"skor": "fon_3", "reb": 1, "k_oran": 0.5, "notr": "beta"}))
for skor in ["fon_3", "mom_28", "mom_7"]:
    for t in (0.1, 0.2):
        C.append(("1d", {"skor": skor, "reb": 1, "k_oran": 0.2, "tampon": t}))
C.append(("1d", {"skor": "fon_3", "reb": 7, "k_oran": 0.5, "delist_cik": False}))
C.append(("1d", {"skor": "mom_28", "reb": 7, "k_oran": 0.5, "delist_cik": False}))
print(len(C), "yapılandırma", flush=True)
run_grid(C, HERE / "tarama2.csv", mults=(1.0, 2.0))
