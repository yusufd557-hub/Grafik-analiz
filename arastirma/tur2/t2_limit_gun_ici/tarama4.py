"""Aşama 4 (dev_train, 1× ve 2×): fitil yüzeyinin kenar kontrolü (1h k=4,5; 5m k=10) ve 5m trend uzunluğu."""
import sys

from ortak import degerlendir, done

grup = sys.argv[1]
CSV = f"tarama4_{grup}.csv"
bitti = done(CSV)


def run(name, interval, **p):
    if "t2_limit_gun_ici_" + name in bitti:
        return
    degerlendir(name, interval, CSV, cost2=True, **p)


T = dict(trend_gun=50, trend_mod="ile")
if grup == "F1":
    for H in (1, 3, 6, 12):
        run(f"fitil_1h_k4.5_H{H}_t50", "1h", yontem="fitil", k=4.5, H=H, sig_n=168, **T)
if grup == "F5":
    for H in (12, 24, 48):
        run(f"fitil_5m_k10_H{H}_t50", "5m", yontem="fitil", k=10, H=H, sig_n=288, **T)
    for tg in (30, 100):
        run(f"fitil_5m_k6_H24_t{tg}", "5m", yontem="fitil", k=6, H=24, sig_n=288, trend_gun=tg, trend_mod="ile")
