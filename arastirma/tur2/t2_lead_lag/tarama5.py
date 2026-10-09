"""Aşama 2-B: spot_vadeli "hepsi" (üç coinin spot−vadeli getiri farkı z-ortalaması) komşuluğu,
piyasa emri, dev_train 1×. İsimler tarama1 ile aynı düzende (pencere 288 varsayılan; 576 ayrı adla).
"""
import itertools

from ortak import KLASOR, log_to, tara

ISLEM = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]


def configs():
    out = []
    for k, esik, tut in itertools.product((2, 3, 4, 6), (4.0, 4.5, 5.0, 6.0), (6, 12, 36, 72)):
        out.append((f"sv_5m_hepsi_k{k}_e{esik:g}_t{tut}", "5m",
                    dict(tur="spot_vadeli", islem=ISLEM, kaynak="hepsi", k=k, esik=esik, tut=tut)))
    for k, esik, tut in itertools.product((3,), (4.5, 5.0), (12, 36)):
        out.append((f"sv_5m_hepsi_k{k}_e{esik:g}_t{tut}_w576", "5m",
                    dict(tur="spot_vadeli", islem=ISLEM, kaynak="hepsi", k=k, esik=esik, tut=tut, win=576)))
    for k, esik, tut in itertools.product((2, 3), (4.0, 5.0), (4, 12)):
        out.append((f"sv_15m_hepsi_k{k}_e{esik:g}_t{tut}", "15m",
                    dict(tur="spot_vadeli", islem=ISLEM, kaynak="hepsi", k=k, esik=esik, tut=tut)))
    return out


if __name__ == "__main__":
    tara(configs(), KLASOR / "tarama5.csv", log=log_to(KLASOR / "tarama5.log"))
