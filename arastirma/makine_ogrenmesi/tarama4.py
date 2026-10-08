"""Aşama 3: sağlamlık / komşuluk (yalnız dev_train)."""
import sys

from ortak import degerlendir

parca = sys.argv[1] if len(sys.argv) > 1 else "vadeli"
A = "3"
if parca == "vadeli":
    base = dict(model="hgb_reg", egitim="spot")
    for k in (2.0, 4.0):
        degerlendir("1h", "futures", asama=A, H=4, k=k, yon="iki", **base)
    degerlendir("1h", "futures", asama=A, H=4, k=4.0, yon="uzun", **base)
    for H in (6, 8):
        for k in (2.0, 3.0):
            degerlendir("1h", "futures", asama=A, H=H, k=k, yon="uzun", **base)
        degerlendir("1h", "futures", asama=A, H=H, k=3.0, yon="iki", **base)
    for yon in ("uzun", "iki"):
        degerlendir("1h", "futures", asama=A, H=4, k=3.0, yon=yon, ozellik="temel+btc", **base)
    for yon in ("uzun", "iki"):
        degerlendir("1h", "futures", asama=A, H=4, k=3.0, yon=yon, yeniden=3, **base)
    degerlendir("1h", "futures", asama=A, model="hgb_clf", H=4, k=3.0, yon="iki", egitim="spot")
    for yon in ("uzun", "iki"):
        degerlendir("1h", "futures", asama=A, model="logit", H=4, k=3.0, yon=yon, egitim="spot")
if parca == "spot":
    for k in (2.0, 3.0):
        degerlendir("1h", "spot", asama=A, model="hgb_reg", H=4, k=k, yeniden=3)
    degerlendir("1h", "spot", asama=A, model="hgb_reg", H=4, k=2.5)
