"""Aşama 2-E: öne çıkan yapılandırmalar 2× maliyetle (dev_train). Parametreler önceki tarama csv'lerinden okunur."""
import json

import pandas as pd

from ortak import KLASOR, log_to, tara

HAVUZ = [
    "baz_15m_kendi_w192_e5_t8", "baz_15m_kendi_w192_e5_t8_limt2b2",
    "baz_5m_kendi_w288_e6_t12", "baz_5m_kendi_w288_e6_t12_limt2b2", "baz_5m_kendi_w288_e6_t12_uzun",
    "baz_5m_hepsi_w288_e5_t12", "baz_5m_hepsi_w288_e5_t12_limt2b2", "baz_5m_hepsi_w288_e5_t12_uzun",
    "sv_5m_hepsi_k4_e4_t12", "sv_5m_hepsi_k4_e4_t12_uzun",
    "sv_5m_hepsi_k6_e4_t36", "sv_5m_hepsi_k6_e4_t36_limt2b2",
    "baz_15m_kendi_w96_e4_t8",
]


def configs():
    tab = pd.concat([pd.read_csv(KLASOR / f"tarama{i}.csv") for i in (2, 4, 5, 6)], ignore_index=True)
    tab = tab[tab["maliyet"] == 1.0]
    out = []
    for ad in HAVUZ:
        row = tab[tab["ad"] == "t2_lead_lag_" + ad].iloc[0]
        out.append((ad, row["interval"], json.loads(row["params"])))
    return out


if __name__ == "__main__":
    tara(configs(), KLASOR / "tarama8.csv", mults=(2.0,), log=log_to(KLASOR / "tarama8.log"))
