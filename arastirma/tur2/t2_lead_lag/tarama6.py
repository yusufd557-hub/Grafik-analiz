"""Aşama 2-C: limit emir ve yön kısıtı, Aşama 2-A/B'nin dev_train'de öne çıkan 5 temel yapılandırması üzerinde.
Piyasa emirli temel sürümler zaten defterde; burada yalnız varyantlar ölçülür. dev_train 1×.
"""
import json

import pandas as pd

from ortak import KLASOR, log_to, tara

TEMEL = [
    ("baz_15m_kendi_w192_e5_t8", "tarama4.csv"),
    ("baz_5m_kendi_w288_e6_t12", "tarama4.csv"),
    ("baz_5m_hepsi_w288_e5_t12", "tarama4.csv"),
    ("sv_5m_hepsi_k4_e4_t12", "tarama5.csv"),
    ("sv_5m_hepsi_k6_e4_t36", "tarama5.csv"),
]
LIMIT = {
    "limc0bx": dict(limit_bps=0.0, limit_mod="cikis", limit_bar=None),
    "limc0b3": dict(limit_bps=0.0, limit_mod="cikis", limit_bar=3),
    "limt0b1": dict(limit_bps=0.0, limit_mod="tum", limit_bar=1),
    "limt2b2": dict(limit_bps=2.0, limit_mod="tum", limit_bar=2),
    "limg0b1": dict(limit_bps=0.0, limit_mod="giris", limit_bar=1),
}


def temel():
    out = []
    for ad, csv in TEMEL:
        tab = pd.read_csv(KLASOR / csv)
        row = tab[tab["ad"] == "t2_lead_lag_" + ad].iloc[0]
        out.append((ad, row["interval"], json.loads(row["params"])))
    return out


def configs():
    out = []
    for ad, iv, p in temel():
        for lad, lp in LIMIT.items():
            out.append((f"{ad}_{lad}", iv, {**p, **lp}))
        out.append((f"{ad}_uzun", iv, {**p, "taraf": "uzun"}))
        out.append((f"{ad}_uzun_limc0bx", iv, {**p, "taraf": "uzun", **LIMIT["limc0bx"]}))
    return out


if __name__ == "__main__":
    tara(configs(), KLASOR / "tarama6.csv", log=log_to(KLASOR / "tarama6.log"))
