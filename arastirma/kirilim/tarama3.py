"""Aşama 3: sınır ve duyarlılık kontrolleri. Yalnız dev_train (1× ve 2× maliyet)."""
import itertools
import sys

from ortak import train_eval

configs = []
# a) atr_k ızgara sınırının ötesi
for ak, n, hk, mk in itertools.product((5.0, 6.0), (60, 120), (0, 1.25), ("spot", "futures")):
    p = {"yontem": "kanal", "n": n, "atr_n": 14, "atr_k": ak}
    if hk:
        p["hacim_k"] = hk
    configs.append(("4h", mk, "PORT3", p))
# b) oynaklık rejimi filtresi duyarlılığı
fut = {"yontem": "kanal", "n": 90, "atr_n": 14, "atr_k": 4.0, "hacim_k": 1.25}
for vu in (0.7, 0.8, 0.9):
    configs.append(("4h", "futures", "PORT3", dict(fut, rejim_n=1080, vol_ust=vu)))
for rn in (540, 2160):
    configs.append(("4h", "futures", "PORT3", dict(fut, rejim_n=rn, vol_ust=0.8)))
configs.append(("4h", "futures", "PORT3", {"yontem": "kanal", "n": 60, "atr_n": 14, "atr_k": 4.0, "hacim_k": 1.25, "rejim_n": 1080, "vol_ust": 0.8}))
configs.append(("4h", "spot", "PORT3", {"yontem": "kanal", "n": 60, "atr_n": 14, "atr_k": 4.0, "hacim_k": 1.25, "rejim_n": 1080, "vol_ust": 0.8}))
# c) vadeli yalnız alım, atr_k=4
for n in (60, 90):
    configs.append(("4h", "futures", "PORT3", {"yontem": "kanal", "n": n, "atr_n": 14, "atr_k": 4.0, "hacim_k": 1.25, "yon": "uzun"}))

print("yapılandırma sayısı:", len(configs), flush=True)
part = int(sys.argv[1]) if len(sys.argv) > 1 else 0
nparts = int(sys.argv[2]) if len(sys.argv) > 2 else 1
for i, (iv, mk, uni, p) in enumerate(configs):
    if i % nparts != part:
        continue
    row = train_eval(iv, mk, uni, p, tag="a3")
    print(i, row["name"], "ret1=%.3f sh1=%.2f mdd=%.2f ret2=%.3f tr=%s" % (row["ret1"] or 0, row["sharpe1"] or 0, row["mdd1"] or 0, row["ret2"] or 0, row["trades"]), flush=True)
print("bitti", flush=True)
