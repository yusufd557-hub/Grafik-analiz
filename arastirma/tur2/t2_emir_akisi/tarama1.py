"""Aşama 1 — kenar haritası (vadeli, PORT3, piyasa emri, devam yönü; dönüşün brütü bunun tam tersidir).

Kullanım: python tarama1.py <grup>   (grup: akis, patlama, uyumsuzluk, cvd_aralik, spot_vadeli)
"""
import sys

sys.path.insert(0, __import__("os").path.dirname(__file__))
from ortak import degerlendir  # noqa: E402

N_BARS = {"5m": [1, 12, 72, 288], "15m": [1, 4, 24, 96], "1h": [1, 6, 24, 72]}
HOLDS = {"5m": [12, 48, 288], "15m": [4, 16, 96], "1h": [1, 6, 24]}
L = 2000
grup = sys.argv[1]
ivs = sys.argv[2].split(",") if len(sys.argv) > 2 else ["1h", "15m", "5m"]

for iv in ivs:
    for hold in HOLDS[iv]:
        if grup == "akis":
            for n in N_BARS[iv]:
                for k in (2.0, 3.0):
                    degerlendir(f"a1_akis_{iv}_n{n}_k{k}_h{hold}", "futures", iv, "tarama1.csv",
                                kind="akis", n=n, L=L, k=k, mode="devam", hold=hold)
        elif grup == "patlama":
            for vol_v in (None, 2.0):
                for k in (3.0, 4.0):
                    degerlendir(f"a1_patlama_{iv}_v{vol_v}_k{k}_h{hold}", "futures", iv, "tarama1.csv",
                                kind="patlama", n=1, L=L, k=k, mode="devam", hold=hold, vol_v=vol_v)
        elif grup == "uyumsuzluk":
            for n in N_BARS[iv][1:]:
                for k in (2.0, 3.0):
                    degerlendir(f"a1_uyum_{iv}_n{n}_k{k}_h{hold}", "futures", iv, "tarama1.csv",
                                kind="uyumsuzluk", n=n, L=L, k=k, mode="devam", hold=hold)
        elif grup == "cvd_aralik":
            for n in N_BARS[iv][1:]:
                for k in (0.5, 0.8):
                    degerlendir(f"a1_cvdar_{iv}_n{n}_k{k}_h{hold}", "futures", iv, "tarama1.csv",
                                kind="cvd_aralik", n=n, L=L, k=k, mode="devam", hold=hold)
        elif grup == "spot_vadeli":
            for n in N_BARS[iv]:
                for k in (2.0, 3.0):
                    degerlendir(f"a1_spotvad_{iv}_n{n}_k{k}_h{hold}", "futures", iv, "tarama1.csv",
                                kind="spot_vadeli", n=n, L=L, k=k, mode="devam", hold=hold)
