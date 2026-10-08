"""Aşama 2a: işlem eşiği k (maliyet katı) ve vadeli yalnız alım (yalnız dev_train).

Aşama 1'de brüt sinyali olan ama maliyetle eriyen (1h) ya da 2× maliyette zayıflayan
bölgeler için k ∈ {2, 3}. Vadelide iki yön zayıf olduğu için yalnız alım (yon="uzun").
Aynı model yapılandırması için tahminler süreç içi önbellekten gelir.
"""
import sys

from ortak import degerlendir

parca = sys.argv[1] if len(sys.argv) > 1 else "hepsi"
if parca in ("1h", "hepsi"):
    for model in ("logit", "hgb_clf", "hgb_reg"):
        for H in (4, 12):
            for k in (2.0, 3.0):
                degerlendir("1h", "spot", asama="2a", model=model, H=H, k=k)
    for model in ("logit", "hgb_clf"):
        for H in (12, 24):
            for k in (2.0, 3.0):
                degerlendir("1h", "futures", asama="2a", model=model, H=H, k=k)
        for k in (1.0, 2.0):
            degerlendir("1h", "futures", asama="2a", model=model, H=12, k=k, yon="uzun")
if parca in ("4h", "hepsi"):
    for model in ("logit", "hgb_clf", "hgb_reg"):
        for H in (6, 12):
            for k in (2.0, 3.0):
                degerlendir("4h", "spot", asama="2a", model=model, H=H, k=k)
    for model in ("hgb_reg", "hgb_clf"):
        for k in (2.0, 3.0):
            degerlendir("4h", "futures", asama="2a", model=model, H=6, k=k)
        for H in (6, 12):
            degerlendir("4h", "futures", asama="2a", model=model, H=H, k=1.0, yon="uzun")
