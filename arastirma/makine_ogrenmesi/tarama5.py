"""Aşama 4: vadeli egitim=spot bölgesinin son komşuları ve 4h sürümü (yalnız dev_train)."""
import sys

from ortak import degerlendir

parca = sys.argv[1] if len(sys.argv) > 1 else "a"
A = "4"
base = dict(egitim="spot")
if parca == "a":
    # hgb_clf komşuları (H4 tahminleri bir kez hesaplanır, k/yon önbellekten)
    for k in (2.0, 4.0):
        degerlendir("1h", "futures", asama=A, model="hgb_clf", H=4, k=k, yon="iki", **base)
    for yon in ("uzun", "iki"):
        degerlendir("1h", "futures", asama=A, model="hgb_clf", H=6, k=3.0, yon=yon, **base)
if parca == "b":
    reg = dict(hgb_min_yaprak=500, hgb_lr=0.03, hgb_iter=200)
    for yon in ("uzun", "iki"):
        degerlendir("1h", "futures", asama=A, model="hgb_reg", H=4, k=3.0, yon=yon, **reg, **base)
    for yon in ("uzun", "iki"):
        degerlendir("4h", "futures", asama=A, model="hgb_reg", H=6, k=2.0, yon=yon, **base)
