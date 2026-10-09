"""Tarama 2: birincil olaylar üzerinde meta model (hgb / logit, tam özellik, kural taban δ=0). Yalnız dev_train, 1×.

Seyrek birincillerde (eğitimde < ~800 olay) min_olay=150; bunlar için "hepsi" temel çizgisi de aynı
takvimle yeniden ölçülür.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ortak  # noqa: E402

T4 = [dict(cikis="bariyer", tp=3.0, sl=1.5, H=30), dict(cikis="iz", iz_k=3.0, H=60)]
T1 = [dict(cikis="bariyer", tp=3.0, sl=1.5, H=72), dict(cikis="iz", iz_k=3.0, H=120)]
D1 = [dict(cikis="bariyer", tp=2.0, sl=2.0, H=24), dict(cikis="bariyer", tp=0.0, sl=3.0, H=12)]
D4 = [dict(cikis="bariyer", tp=2.0, sl=2.0, H=12), dict(cikis="bariyer", tp=0.0, sl=3.0, H=6)]

prim = []  # (interval, params, seyrek)
for n in (20, 48, 120):
    for c in T4:
        prim.append(("4h", dict(birincil="kanal", n=n, **c), n == 120))
for n in (48, 120, 240):
    for c in T1:
        prim.append(("1h", dict(birincil="kanal", n=n, **c), False))
for k, z in ((4, 3.0), (4, 4.0), (24, 3.0)):
    for c in D1:
        prim.append(("1h", dict(birincil="donus", k=k, z=z, **c), True))
for c in D4:
    prim.append(("4h", dict(birincil="donus", k=6, z=2.5, **c), True))
for c in (dict(cikis="bariyer", tp=2.0, sl=2.0, H=24), dict(cikis="bariyer", tp=0.0, sl=3.0, H=48)):
    prim.append(("1h", dict(birincil="fonlama", fz=2.0, **c), True))
for c in D4[:1] + [dict(cikis="bariyer", tp=0.0, sl=3.0, H=18)]:
    prim.append(("4h", dict(birincil="fonlama", fz=2.0, **c), True))

configs = []
for iv, p, seyrek in prim:
    extra = {"min_olay": 150} if seyrek else {}
    if seyrek:
        configs.append((iv, dict(p, model="hepsi", **extra)))
    configs.append((iv, dict(p, model="hgb", ozellik="tam", **extra)))
    configs.append((iv, dict(p, model="logit", ozellik="tam", **extra)))

if __name__ == "__main__":
    print(len(configs), "yapılandırma", flush=True)
    ortak.tara(configs, "tarama2.csv")
    print("BITTI", flush=True)
