"""Aşama 2b: 1h kısa ufuklu yalnız alım bölgesinin çevresi (yalnız dev_train)."""
import sys

from ortak import degerlendir

parca = sys.argv[1] if len(sys.argv) > 1 else "spot"
A = "2b"
if parca == "spot":
    # a) ufuk
    for model in ("hgb_reg", "hgb_clf"):
        for H in (6, 8):
            for k in (2.0, 3.0):
                degerlendir("1h", "spot", asama=A, model=model, H=H, k=k)
    # d) eşleme (önbellekten)
    for k in (2.0, 3.0):
        degerlendir("1h", "spot", asama=A, model="hgb_reg", H=4, k=k, esleme="esik")
    # b) özellik seti
    for oz in ("temel+mum", "temel+btc"):
        for k in (2.0, 3.0):
            degerlendir("1h", "spot", asama=A, model="hgb_reg", H=4, k=k, ozellik=oz)
    # c) kayan pencere
    for w in (730, 1095):
        for k in (2.0, 3.0):
            degerlendir("1h", "spot", asama=A, model="hgb_reg", H=4, k=k, pencere_gun=w)
    # e) HGB düzenlileştirme
    for extra in ({"hgb_min_yaprak": 500, "hgb_lr": 0.03, "hgb_iter": 200}, {"hgb_yaprak": 31, "hgb_min_yaprak": 100}):
        for k in (2.0, 3.0):
            degerlendir("1h", "spot", asama=A, model="hgb_reg", H=4, k=k, **extra)
if parca == "vadeli":
    for eg in ("kendi", "spot"):
        for k in (2.0, 3.0):
            degerlendir("1h", "futures", asama=A, model="hgb_reg", H=4, k=k, yon="uzun", egitim=eg)
        degerlendir("1h", "futures", asama=A, model="hgb_reg", H=4, k=3.0, yon="iki", egitim=eg)
    for k in (2.0, 3.0):
        degerlendir("1h", "futures", asama=A, model="hgb_reg", H=4, k=k, yon="uzun", ozellik="temel+fon")
    for k in (2.0, 3.0):
        degerlendir("1h", "futures", asama=A, model="hgb_clf", H=4, k=k, yon="uzun", egitim="spot")
