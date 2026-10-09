"""Aşama 2-D: coinler arası baz öncülüğü — BTC'nin baz sapması → ETH/SOL vadeli (piyasa emri, dev_train 1×)."""
from ortak import KLASOR, log_to, tara

IZ = ["ETHUSDT", "SOLUSDT"]


def configs():
    out = []
    for iv, win, esik, tut in (("5m", 288, 5.0, 12), ("5m", 288, 6.0, 12), ("15m", 192, 5.0, 8), ("15m", 96, 4.0, 8)):
        out.append((f"baz_{iv}_BTCkaynak_iz_w{win}_e{esik:g}_t{tut}", iv,
                    dict(tur="baz", islem=IZ, kaynak="BTCUSDT", win=win, esik=esik, tut=tut)))
    return out


if __name__ == "__main__":
    tara(configs(), KLASOR / "tarama7.csv", log=log_to(KLASOR / "tarama7.log"))
