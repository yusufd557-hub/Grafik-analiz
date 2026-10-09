"""Aşama 1-C: coinler arası yetişme (yetis) ve lider yönü (lider); ETH/SOL vadeli, lider BTC.

Piyasa emri ve limit emir (her değişimde, 3 bar sonra piyasaya dönüş), dev_train 1×.
"""
import itertools

from ortak import KLASOR, log_to, tara

IZ = ["ETHUSDT", "SOLUSDT"]


def configs():
    out = []
    for iv, ks, tuts in (("5m", (1, 3), (3, 12)), ("15m", (1,), (2, 6))):
        for k, esik, le, tut in itertools.product(ks, (3.0, 4.0), (None, 3.0), tuts):
            lad = "x" if le is None else f"{le:g}"
            out.append((f"yetis_{iv}_k{k}_e{esik:g}_l{lad}_t{tut}", iv,
                        dict(tur="yetis", islem=IZ, lider="BTCUSDT", k=k, esik=esik, lider_esik=le, tut=tut)))
    # Lider yönü: tanılamada büyük BTC hareketinden sonra ETH/SOL kısa vadede ters döndü (yon=-1);
    # yetişme hipotezi için yon=+1 de ölçülür.
    for iv, k, tut in (("5m", 1, 3), ("5m", 3, 12), ("15m", 1, 2), ("15m", 2, 6)):
        for yon in (1, -1):
            out.append((f"lider_{iv}_k{k}_e4_t{tut}_y{yon:+d}", iv,
                        dict(tur="lider", islem=IZ, lider="BTCUSDT", k=k, esik=4.0, tut=tut, yon=yon)))
    # Limit emirli yetişme (her değişimde, kapanıştan 0 / 3 bps, 3 bar sonra piyasa)
    for iv, k, tut in (("5m", 1, 3), ("5m", 1, 12), ("15m", 1, 2)):
        for bps in (0.0, 3.0):
            out.append((f"yetis_{iv}_k{k}_e4_lx_t{tut}_lim{bps:g}", iv,
                        dict(tur="yetis", islem=IZ, lider="BTCUSDT", k=k, esik=4.0, lider_esik=None, tut=tut,
                             limit_bps=bps, limit_mod="tum", limit_bar=3)))
    return out


if __name__ == "__main__":
    tara(configs(), KLASOR / "tarama3.csv", log=log_to(KLASOR / "tarama3.log"))
