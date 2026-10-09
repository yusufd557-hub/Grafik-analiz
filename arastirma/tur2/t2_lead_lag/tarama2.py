"""Aşama 1-B/D: prim endeksi (1h), spot_vadeli 1h, baz (15m/1h); piyasa emri, dev_train 1×."""
import itertools

from ortak import KLASOR, log_to, tara

ISLEM = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]


def configs():
    out = []
    for win, esik, tut in itertools.product((24, 168), (2.0, 3.0), (4, 8, 24)):
        out.append((f"prim_1h_w{win}_e{esik:g}_t{tut}", "1h", dict(tur="prim", islem=ISLEM, win=win, esik=esik, tut=tut)))
    for kad, kay in (("kendi", "kendi"), ("hepsi", "hepsi")):
        for esik, tut in itertools.product((3.0, 4.0), (2, 6)):
            out.append((f"sv_1h_{kad}_k1_e{esik:g}_t{tut}", "1h", dict(tur="spot_vadeli", islem=ISLEM, kaynak=kay, k=1, esik=esik, tut=tut)))
    for iv, win, esik, tut in (("15m", 96, 3.0, 8), ("15m", 96, 4.0, 8), ("1h", 24, 2.0, 8), ("1h", 168, 2.0, 8), ("1h", 168, 3.0, 8)):
        out.append((f"baz_{iv}_kendi_w{win}_e{esik:g}_t{tut}", iv, dict(tur="baz", islem=ISLEM, kaynak="kendi", win=win, esik=esik, tut=tut)))
    return out


if __name__ == "__main__":
    tara(configs(), KLASOR / "tarama2.csv", log=log_to(KLASOR / "tarama2.log"))
