"""Aşama 2: umut veren bölgelerin yüzeyi ve filtreler. Yalnız dev_train (1× ve 2× maliyet)."""
import itertools
import sys

from ortak import train_eval

configs = []

# A. 4h kanal yüzeyi: n × atr_k × hacim_k (spot PORT3 ve vadeli PORT3 iki yön)
for n, ak, hk, (mk, yon) in itertools.product((30, 45, 60, 90, 120), (2.0, 3.0, 4.0), (0, 1.25, 1.5, 2.0), (("spot", None), ("futures", "iki"))):
    p = {"yontem": "kanal", "n": n, "atr_n": 14, "atr_k": ak}
    if hk:
        p["hacim_k"] = hk
    if yon == "uzun":
        p["yon"] = "uzun"
    configs.append(("4h", mk, "PORT3", p))

# B. 4h kanal, vadeli yalnız alım
for n, hk in itertools.product((30, 45, 60, 90, 120), (0, 1.5)):
    p = {"yontem": "kanal", "n": n, "atr_n": 14, "atr_k": 3.0, "yon": "uzun"}
    if hk:
        p["hacim_k"] = hk
    configs.append(("4h", "futures", "PORT3", p))

# C. 4h kanal (n=60, atr_k=3, hacim_k=1.5) + oynaklık rejimi / trend filtresi
for mk in ("spot", "futures"):
    base = {"yontem": "kanal", "n": 60, "atr_n": 14, "atr_k": 3.0, "hacim_k": 1.5}
    for va, vu in ((None, 0.5), (None, 0.8), (0.2, None), (0.5, None)):
        p = dict(base, rejim_n=1080)
        if va is not None:
            p["vol_alt"] = va
        if vu is not None:
            p["vol_ust"] = vu
        configs.append(("4h", mk, "PORT3", p))
    for tn in (200, 600):
        configs.append(("4h", mk, "PORT3", dict(base, trend_n=tn)))

# D. 1d kanal
for n, hk, mk in itertools.product((10, 20, 40), (0, 1.5), ("spot", "futures")):
    p = {"yontem": "kanal", "n": n, "atr_n": 14, "atr_k": 3.0}
    if hk:
        p["hacim_k"] = hk
    configs.append(("1d", mk, "PORT3", p))

# E. Sıkışma + geniş ATR çıkışı (4h), ve 1h uzun sıkışma
for ms, ak, kc, mk in itertools.product((6, 12), (3.0, 4.0), (1.5, 2.0), ("spot", "futures")):
    p = {"yontem": "sikisma", "bb_n": 20, "bb_k": 2.0, "kc_k": kc, "min_sik": ms, "pencere": 3, "atr_n": 14, "atr_k": ak}
    configs.append(("4h", mk, "PORT3", p))
for ms, cikis in itertools.product((12, 24), ("orta", "atr")):
    p = {"yontem": "sikisma", "bb_n": 20, "bb_k": 2.0, "kc_k": 1.5, "min_sik": ms, "pencere": 3, "atr_n": 14}
    if cikis == "orta":
        p["cikis_orta"] = True
    else:
        p["atr_k"] = 4.0
    configs.append(("1h", "spot", "PORT3", p))

# F. Williams + trend filtresi (1h spot)
for k, tn in itertools.product((0.6, 0.8, 1.0), (0, 120)):
    p = {"yontem": "williams", "k": k, "stop": "yok"}
    if tn:
        p["trend_n"] = tn
    configs.append(("1h", "spot", "PORT3", p))

# G. 1d NR7 + ATR iz
for ak, mk in itertools.product((2.0, 4.0), ("spot", "futures")):
    configs.append(("1d", mk, "PORT3", {"yontem": "nr", "nr_n": 7, "atr_n": 14, "atr_k": ak}))

print("yapılandırma sayısı:", len(configs), flush=True)
part = int(sys.argv[1]) if len(sys.argv) > 1 else 0
nparts = int(sys.argv[2]) if len(sys.argv) > 2 else 1
for i, (iv, mk, uni, p) in enumerate(configs):
    if i % nparts != part:
        continue
    row = train_eval(iv, mk, uni, p, tag="a2")
    print(i, row["name"], "ret1=%.3f sh1=%.2f ret2=%.3f tr=%s sec=%s" % (row["ret1"] or 0, row["sharpe1"] or 0, row["ret2"] or 0, row["trades"], row["sec"]), flush=True)
print("bitti", flush=True)
