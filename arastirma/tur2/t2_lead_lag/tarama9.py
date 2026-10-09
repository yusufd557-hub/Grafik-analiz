"""Aşama 2-F: yalnız-uzun varyantının komşulukta dayanıklılığı ve uzun + limit birleşimi (dev_train 1×; seçilenler 2×)."""
import itertools

from ortak import KLASOR, log_to, tara

ISLEM = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
LIM = dict(limit_bps=2.0, limit_mod="tum", limit_bar=2)


def configs():
    out = []
    for kad, esik, tut in itertools.product(("hepsi", "kendi"), (4.0, 5.0, 6.0), (12, 48)):
        ad = f"baz_5m_{kad}_w288_e{esik:g}_t{tut}_uzun"
        out.append((ad, "5m", dict(tur="baz", islem=ISLEM, kaynak=kad, win=288, esik=esik, tut=tut, taraf="uzun")))
    for k, esik, tut in itertools.product((3, 6), (4.0, 5.0), (12, 36)):
        out.append((f"sv_5m_hepsi_k{k}_e{esik:g}_t{tut}_uzun", "5m",
                    dict(tur="spot_vadeli", islem=ISLEM, kaynak="hepsi", k=k, esik=esik, tut=tut, taraf="uzun")))
    out.append(("baz_15m_kendi_w192_e5_t8_uzun_limt2b2", "15m",
                dict(tur="baz", islem=ISLEM, kaynak="kendi", win=192, esik=5.0, tut=8, taraf="uzun", **LIM)))
    out.append(("baz_5m_hepsi_w288_e5_t12_uzun_limt2b2", "5m",
                dict(tur="baz", islem=ISLEM, kaynak="hepsi", win=288, esik=5.0, tut=12, taraf="uzun", **LIM)))
    out.append(("baz_5m_kendi_w288_e6_t12_uzun_limt2b2", "5m",
                dict(tur="baz", islem=ISLEM, kaynak="kendi", win=288, esik=6.0, tut=12, taraf="uzun", **LIM)))
    out.append(("sv_5m_hepsi_k4_e4_t12_uzun_limt2b2", "5m",
                dict(tur="spot_vadeli", islem=ISLEM, kaynak="hepsi", k=4, esik=4.0, tut=12, taraf="uzun", **LIM)))
    return out


if __name__ == "__main__":
    tara(configs(), KLASOR / "tarama9.csv", log=log_to(KLASOR / "tarama9.log"))
