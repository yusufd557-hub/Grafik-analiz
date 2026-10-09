"""Aşama 1-A: spot_vadeli (spot öncülüğü), piyasa emri, dev_train 1×.

Kullanım: python tarama1.py [ilk_n]
"""
import itertools
import sys

from ortak import KLASOR, log_to, tara

ISLEM = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
KAYNAK = {"kendi": "kendi", "BTC": "BTCUSDT", "hepsi": "hepsi"}


def configs():
    out = []
    for iv, ks, tuts in (("15m", (1,), (2, 4, 12)), ("5m", (1, 3), (6, 12, 36))):
        for (kad, kay), k, esik, tut in itertools.product(KAYNAK.items(), ks, (3.0, 4.0, 5.0), tuts):
            ad = f"sv_{iv}_{kad}_k{k}_e{esik:g}_t{tut}"
            out.append((ad, iv, dict(tur="spot_vadeli", islem=ISLEM, kaynak=kay, k=k, esik=esik, tut=tut)))
    return out


if __name__ == "__main__":
    cfg = configs()
    if len(sys.argv) > 1:
        a, b = (int(x) for x in sys.argv[1].split(":"))
        cfg = cfg[a:b]
    tara(cfg, KLASOR / "tarama1.csv", log=log_to(KLASOR / "tarama1.log"))
