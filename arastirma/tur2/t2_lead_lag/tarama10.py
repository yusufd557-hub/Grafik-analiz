"""Aşama 2-G: uzun + limit birleşimleri 2× maliyetle (dev_train). Parametreler tarama9.csv'den."""
import json

import pandas as pd

from ortak import KLASOR, log_to, tara

HAVUZ = ["baz_5m_hepsi_w288_e5_t12_uzun_limt2b2", "baz_5m_kendi_w288_e6_t12_uzun_limt2b2",
         "sv_5m_hepsi_k4_e4_t12_uzun_limt2b2", "baz_15m_kendi_w192_e5_t8_uzun_limt2b2"]


def configs():
    tab = pd.read_csv(KLASOR / "tarama9.csv")
    out = []
    for ad in HAVUZ:
        row = tab[tab["ad"] == "t2_lead_lag_" + ad].iloc[0]
        out.append((ad, row["interval"], json.loads(row["params"])))
    return out


if __name__ == "__main__":
    tara(configs(), KLASOR / "tarama10.csv", mults=(2.0,), log=log_to(KLASOR / "tarama10.log"))
