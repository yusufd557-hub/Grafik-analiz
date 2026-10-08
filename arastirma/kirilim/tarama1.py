"""Aşama 1: geniş, kaba ızgara. Yalnız dev_train (1× ve 2× maliyet)."""
import itertools
import sys

from ortak import train_eval

configs = []
MARKETS = (("futures", "PORT3"), ("spot", "PORT3"))

# A. Donchian kanal kırılımı
for iv, n, cikis, hk, (mk, uni) in itertools.product(("15m", "1h", "4h"), (20, 60), ("kanal", "atr"), (0, 1.5), MARKETS):
    p = {"yontem": "kanal", "n": n, "atr_n": 14}
    if cikis == "kanal":
        p["n_cikis"] = n // 2
    else:
        p["atr_k"] = 3.0
    if hk:
        p["hacim_k"] = hk
    configs.append((iv, mk, uni, p))

# B. Sıkışma (BB içinde KC) kırılımı
for iv, ms, cikis, (mk, uni) in itertools.product(("15m", "1h", "4h"), (4, 12), ("orta", "atr"), MARKETS):
    p = {"yontem": "sikisma", "bb_n": 20, "bb_k": 2.0, "kc_k": 1.5, "min_sik": ms, "pencere": 3, "atr_n": 14}
    if cikis == "orta":
        p["cikis_orta"] = True
    else:
        p["atr_k"] = 2.5
    configs.append((iv, mk, uni, p))

# C. NR-k kırılımı
for iv, k, cikis, (mk, uni) in itertools.product(("1h", "4h", "1d"), (4, 7), ("zaman", "atr"), MARKETS):
    p = {"yontem": "nr", "nr_n": k, "atr_n": 14}
    if cikis == "zaman":
        p["max_bar"] = 6
    else:
        p["atr_k"] = 3.0
    configs.append((iv, mk, uni, p))

# D. Günlük açılış aralığı kırılımı (00:00 UTC), 15m
for orh, stop, gen, (mk, uni) in itertools.product((1, 2, 4), ("yok", "karsi"), (None, 0.5), MARKETS):
    p = {"yontem": "acilis", "or_saat": orh, "stop": stop}
    if gen:
        p["genislik_ust"] = gen
    configs.append(("15m", mk, uni, p))

# E. Williams oynaklık kırılımı
for iv, k, stop, (mk, uni) in itertools.product(("15m", "1h"), (0.3, 0.5, 0.7), ("yok", "acilis"), MARKETS):
    p = {"yontem": "williams", "k": k, "stop": stop}
    configs.append((iv, mk, uni, p))

print("yapılandırma sayısı:", len(configs), flush=True)
part = int(sys.argv[1]) if len(sys.argv) > 1 else 0
nparts = int(sys.argv[2]) if len(sys.argv) > 2 else 1
for i, (iv, mk, uni, p) in enumerate(configs):
    if i % nparts != part:
        continue
    row = train_eval(iv, mk, uni, p, tag="a1")
    print(i, row["name"], "ret1=%.3f sh1=%.2f ret2=%.3f tr=%s sec=%s" % (row["ret1"] or 0, row["sharpe1"] or 0, row["ret2"] or 0, row["trades"], row["sec"]), flush=True)
print("bitti", flush=True)
