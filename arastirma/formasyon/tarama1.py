"""Aşama 1: ders kitabı değerleri, geniş tarama (yalnız dev_train, 1× ve 2× maliyet)."""
import sys

from ortak import train_eval
from grafik_analiz.strategies.formasyon import GRAFIK_GRUPLARI, MUM_GRUPLARI

MODES = [("spot", "uzun"), ("futures", "iki")]
INTERVALS = ("1h", "4h", "1d")

jobs = []
# a) bütün grafik formasyonları
for iv in INTERVALS:
    for market, yon in MODES:
        for cikis in ("hedef", "sure"):
            for tn in (0, 200):
                p = {"yontem": "grafik", "tipler": "hepsi", "yon": yon, "cikis": cikis}
                if cikis == "sure":
                    p["max_bar"] = 20
                if tn:
                    p["trend_n"] = tn
                jobs.append(("1a", iv, market, p))
# b) grafik formasyon grupları
for g in GRAFIK_GRUPLARI:
    for iv in INTERVALS:
        for market, yon in MODES:
            jobs.append(("1b", iv, market, {"yontem": "grafik", "tipler": g, "yon": yon, "cikis": "hedef"}))
# c) mum formasyonu grupları
for g in MUM_GRUPLARI:
    for iv in INTERVALS:
        for market, yon in MODES:
            jobs.append(("1c", iv, market, {"yontem": "mum", "tipler": g, "yon": yon, "cikis": "sure", "tutma": 10}))

print("iş sayısı", len(jobs), flush=True)
for i, (tag, iv, market, p) in enumerate(jobs):
    r = train_eval(iv, market, "PORT3", p, tag)
    print(i, tag, r["name"], f"ret1={r['ret1']:.3f} sh1={r['sharpe1']} ret2={r['ret2']:.3f} sh2={r['sharpe2']} n={r['trades']} exp={r['exposure']} t={r['sec']}", flush=True)
