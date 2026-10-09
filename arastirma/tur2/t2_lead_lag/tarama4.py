"""Aşama 2-A: baz (vadeli/spot log fiyat farkı düzeyi z-skoru), piyasa emri, dev_train 1×.

İsimler tarama2 ile aynı düzende; defterde olan yapılandırma yeniden çalıştırılmaz.
"""
import itertools

from ortak import KLASOR, log_to, tara

ISLEM = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
KAYNAK = {"kendi": "kendi", "hepsi": "hepsi"}


def configs():
    out = []
    grid = (
        ("15m", (48, 96, 192), (3.5, 4.0, 5.0), (4, 8, 16)),
        ("5m", (288,), (4.0, 5.0, 6.0), (12, 24, 48)),
        ("1h", (24, 48), (3.0, 4.0), (4, 8)),
    )
    for iv, wins, esiks, tuts in grid:
        for (kad, kay), win, esik, tut in itertools.product(KAYNAK.items(), wins, esiks, tuts):
            out.append((f"baz_{iv}_{kad}_w{win}_e{esik:g}_t{tut}", iv,
                        dict(tur="baz", islem=ISLEM, kaynak=kay, win=win, esik=esik, tut=tut)))
    return out


if __name__ == "__main__":
    tara(configs(), KLASOR / "tarama4.csv", log=log_to(KLASOR / "tarama4.log"))
