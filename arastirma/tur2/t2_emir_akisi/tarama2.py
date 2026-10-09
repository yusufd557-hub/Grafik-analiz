"""Aşama 2a — kontroller (vadeli, PORT3, piyasa emri, dev_train 1×).

Gruplar:
  getiri_donus : akışsız fiyat kontrolü — n barlık getiri z-skoru, dönüş yönü
                 (uyumsuzluk ızgarasıyla aynı n/k/hold).
  artik        : fiyatla açıklanamayan akış (akis_artik), devam yönü.
  gartik_donus : akışla açıklanamayan fiyat hareketi (getiri_artik), dönüş yönü; yalnız k=3.

Kullanım: python tarama2.py <grup> [aralıklar]
"""
import sys

sys.path.insert(0, __import__("os").path.dirname(__file__))
from ortak import degerlendir  # noqa: E402

N_BARS = {"5m": [12, 72, 288], "15m": [4, 24, 96], "1h": [6, 24, 72]}
HOLDS = {"5m": [12, 48, 288], "15m": [4, 16, 96], "1h": [1, 6, 24]}
L = 2000
grup = sys.argv[1]
ivs = sys.argv[2].split(",") if len(sys.argv) > 2 else ["1h", "15m", "5m"]

for iv in ivs:
    for hold in HOLDS[iv]:
        for n in N_BARS[iv]:
            for k in (2.0, 3.0):
                if grup == "getiri_donus":
                    degerlendir(f"a2_getiri_donus_{iv}_n{n}_k{k}_h{hold}", "futures", iv, "tarama2.csv",
                                kind="getiri", n=n, L=L, k=k, mode="donus", hold=hold)
                elif grup == "artik":
                    degerlendir(f"a2_artik_{iv}_n{n}_k{k}_h{hold}", "futures", iv, "tarama2.csv",
                                kind="akis_artik", n=n, L=L, k=k, mode="devam", hold=hold)
                elif grup == "gartik_donus":
                    if k != 3.0:
                        continue
                    degerlendir(f"a2_gartik_donus_{iv}_n{n}_k{k}_h{hold}", "futures", iv, "tarama2.csv",
                                kind="getiri_artik", n=n, L=L, k=k, mode="donus", hold=hold)
                else:
                    raise SystemExit(f"bilinmeyen grup {grup}")
