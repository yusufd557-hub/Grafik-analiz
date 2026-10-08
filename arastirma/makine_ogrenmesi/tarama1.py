"""Aşama 1: geniş harita (yalnız dev_train, 1× ve 2× maliyet).

aralık × piyasa (spot yalnız alım / vadeli iki yön) × model × H; varsayılanlar:
genişleyen pencere, k=1, örtüşen eşleme, temel özellikler.
"""
import sys

from ortak import degerlendir

H_SET = {"1d": (4, 8, 16), "4h": (6, 12, 24), "1h": (4, 12, 24)}
araliklar = sys.argv[1:] or ["1d", "4h", "1h"]
for interval in araliklar:
    for market in ("futures", "spot"):
        for model in ("logit", "hgb_clf", "hgb_reg"):
            for H in H_SET[interval]:
                degerlendir(interval, market, asama="1", model=model, H=H)
