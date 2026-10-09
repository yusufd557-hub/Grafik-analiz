"""Aşama 2c — eşlenmiş kontrol, dayanıklılık, limit emir, spot ve 1h (dev_train, 1× ve 2×).

Kullanım: python tarama4.py <grup>
  kontrol  : getiri dönüş, k {4, 5}, merkez noktalarda (akışsız, işlem sayısı eşlenmiş kontrol)
  dayanim  : L {1000, 4000}, k 4, yön (uzun/kisa), exit_z 0 — merkez noktalarda
  limit    : limit emir yürütmesi (uyumsuzluk merkezleri)
  spot     : spot sürümü (yalnız uzun, spot maliyeti)
  saat     : 1h uyumsuzluk
"""
import sys

sys.path.insert(0, __import__("os").path.dirname(__file__))
from ortak import degerlendir  # noqa: E402

CSV = "tarama4.csv"
grup = sys.argv[1]

# Merkez noktalar (Aşama 2b, dev_train)
UYUM = [("5m", 72, 3.5, 12), ("15m", 24, 3.5, 2), ("5m", 36, 3.5, 24)]
ARTIK = [("5m", 144, 3.0, 24), ("15m", 12, 3.5, 8)]


def run(tag, market, iv, **p):
    degerlendir(f"a4_{tag}", market, iv, CSV, cost2=True, **p)


if grup == "kontrol":
    for iv, n, hold in [("5m", 72, 12), ("5m", 36, 24), ("5m", 144, 12), ("15m", 24, 2), ("15m", 24, 4)]:
        for k in (4.0, 5.0):
            run(f"getiri_donus_{iv}_n{n}_k{k}_h{hold}", "futures", iv,
                kind="getiri", n=n, L=2000, k=k, mode="donus", hold=hold)
elif grup == "dayanim":
    for kind, tag, centers in (("uyumsuzluk", "uyum", UYUM), ("akis_artik", "artik", ARTIK)):
        for iv, n, k, hold in centers:
            base = dict(kind=kind, n=n, L=2000, k=k, mode="devam", hold=hold)
            for L in (1000, 4000):
                run(f"{tag}_{iv}_n{n}_k{k}_h{hold}_L{L}", "futures", iv, **{**base, "L": L})
            run(f"{tag}_{iv}_n{n}_k4.0_h{hold}", "futures", iv, **{**base, "k": 4.0})
            for side in ("uzun", "kisa"):
                run(f"{tag}_{iv}_n{n}_k{k}_h{hold}_{side}", "futures", iv, **{**base, "side": side})
            run(f"{tag}_{iv}_n{n}_k{k}_h{hold}_ez0", "futures", iv, **{**base, "exit_z": 0.0})
elif grup == "limit":
    for iv, n, k, hold in UYUM[:2]:
        base = dict(kind="uyumsuzluk", n=n, L=2000, k=k, mode="devam", hold=hold, exec="limit")
        for lim_in in (0.0, 10.0, 30.0):
            run(f"uyum_{iv}_n{n}_k{k}_h{hold}_limg{int(lim_in)}", "futures", iv, **{**base, "lim_in": lim_in})
        run(f"uyum_{iv}_n{n}_k{k}_h{hold}_limc10", "futures", iv, **{**base, "lim_out": 10.0, "out_timeout": 3})
elif grup == "spot":
    for iv, n, k, hold in UYUM:
        run(f"uyum_spot_{iv}_n{n}_k{k}_h{hold}", "spot", iv,
            kind="uyumsuzluk", n=n, L=2000, k=k, mode="devam", hold=hold, side="uzun")
    for iv, n, k, hold in ARTIK:
        run(f"artik_spot_{iv}_n{n}_k{k}_h{hold}", "spot", iv,
            kind="akis_artik", n=n, L=2000, k=k, mode="devam", hold=hold, side="uzun")
elif grup == "saat":
    for n in (6, 12):
        for k in (3.0, 3.5):
            for hold in (1, 3):
                run(f"uyum_1h_n{n}_k{k}_h{hold}", "futures", "1h",
                    kind="uyumsuzluk", n=n, L=2000, k=k, mode="devam", hold=hold)
else:
    raise SystemExit(f"bilinmeyen grup {grup}")
