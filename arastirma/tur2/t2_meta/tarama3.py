"""Tarama 3: 4h Donchian kırılımı + meta model etrafında tek boyutlu incelemeler. Yalnız dev_train, 1×."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ortak  # noqa: E402

IZ = dict(cikis="iz", iz_k=3.0, H=60)
BA = dict(cikis="bariyer", tp=3.0, sl=1.5, H=30)
L = dict(model="logit", ozellik="tam")
configs = []
add = lambda iv, **p: configs.append((iv, p))  # noqa: E731

# 1. kanal uzunluğu
for n in (14, 30):
    for c in (IZ, BA):
        add("4h", birincil="kanal", n=n, model="hepsi", **c)
        add("4h", birincil="kanal", n=n, **c, **L)
# 2. özellik kümesi
for n in (20, 48):
    for c in (IZ, BA):
        for oz in ("fiyat", "temel"):
            add("4h", birincil="kanal", n=n, **c, model="logit", ozellik=oz)
add("4h", birincil="kanal", n=20, **IZ, model="hgb", ozellik="fiyat")
# 3. düzenlileştirme
for c in (IZ, BA):
    for C in (0.03, 0.3, 1.0):
        add("4h", birincil="kanal", n=20, **c, **L, C=C)
# 4. karar kuralı
for c in (IZ, BA):
    for d in (0.03, 0.06):
        add("4h", birincil="kanal", n=20, **c, **L, delta=d)
    add("4h", birincil="kanal", n=20, **c, **L, kural="ev")
# 5-6. çıkış
for c in (dict(cikis="iz", iz_k=2.0, H=60), dict(cikis="iz", iz_k=4.0, H=60), dict(cikis="iz", iz_k=3.0, H=30), dict(cikis="iz", iz_k=3.0, H=120),
          dict(cikis="bariyer", tp=2.0, sl=1.0, H=30), dict(cikis="bariyer", tp=4.0, sl=2.0, H=30), dict(cikis="bariyer", tp=3.0, sl=1.5, H=60)):
    add("4h", birincil="kanal", n=20, model="hepsi", **c)
    add("4h", birincil="kanal", n=20, **c, **L)
# 7. takvim
add("4h", birincil="kanal", n=20, **IZ, **L, yeniden=3)
add("4h", birincil="kanal", n=20, **IZ, **L, pencere_gun=730)
add("4h", birincil="kanal", n=20, **IZ, **L, min_olay=150)
add("4h", birincil="kanal", n=20, **IZ, **L, min_olay=500)
# 8. örnek ağırlığı
for c in (IZ, BA):
    add("4h", birincil="kanal", n=20, **c, **L, agirlik="getiri")
    add("4h", birincil="kanal", n=20, **c, model="hgb", ozellik="tam", agirlik="getiri")
# 9. düzenli hgb
add("4h", birincil="kanal", n=20, **IZ, model="hgb", ozellik="tam", hgb_iter=50, hgb_yaprak=4, hgb_min_yaprak=100)
add("4h", birincil="kanal", n=120, **BA, model="hgb", ozellik="tam", min_olay=150, hgb_iter=50, hgb_yaprak=4, hgb_min_yaprak=100)
# 10. yalnız uzun
add("4h", birincil="kanal", n=20, **IZ, model="hepsi", yon="uzun")
add("4h", birincil="kanal", n=20, **IZ, **L, yon="uzun")
# 11. 1h kanal
I1 = dict(cikis="iz", iz_k=3.0, H=120)
add("1h", birincil="kanal", n=48, **I1, model="logit", ozellik="fiyat")
add("1h", birincil="kanal", n=48, **I1, **L, C=0.03)
add("1h", birincil="kanal", n=48, **I1, **L, delta=0.05)
add("1h", birincil="kanal", n=96, **I1, model="hepsi")
add("1h", birincil="kanal", n=96, **I1, **L)

if __name__ == "__main__":
    print(len(configs), "yapılandırma", flush=True)
    ortak.tara(configs, "tarama3.csv")
    print("BITTI", flush=True)
