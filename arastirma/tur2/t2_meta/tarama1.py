"""Tarama 1: birincil olayların "hepsi" (model yok) temel çizgisi. Yalnız dev_train, 1×."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ortak  # noqa: E402

configs = []
CIK_TREND = {"4h": [dict(cikis="bariyer", tp=3.0, sl=1.5, H=30), dict(cikis="iz", iz_k=3.0, H=60)],
             "1h": [dict(cikis="bariyer", tp=3.0, sl=1.5, H=72), dict(cikis="iz", iz_k=3.0, H=120)]}
CIK_DONUS = {"4h": [dict(cikis="bariyer", tp=2.0, sl=2.0, H=12), dict(cikis="bariyer", tp=0.0, sl=3.0, H=6)],
             "1h": [dict(cikis="bariyer", tp=2.0, sl=2.0, H=24), dict(cikis="bariyer", tp=0.0, sl=3.0, H=12)]}
CIK_FON = {"4h": [dict(cikis="bariyer", tp=2.0, sl=2.0, H=12), dict(cikis="bariyer", tp=0.0, sl=3.0, H=18)],
           "1h": [dict(cikis="bariyer", tp=2.0, sl=2.0, H=24), dict(cikis="bariyer", tp=0.0, sl=3.0, H=48)]}
KANAL = {"4h": [20, 48, 120], "1h": [48, 120, 240]}
EMA = {"4h": [(20, 100), (50, 200)], "1h": [(50, 200), (100, 400)]}
DONUS = {"4h": [(6, 2.5), (6, 3.5), (24, 2.5), (24, 3.5)], "1h": [(4, 3.0), (4, 4.0), (24, 3.0), (24, 4.0)]}
FON = [2.0, 3.0]
for iv in ("4h", "1h"):
    for n in KANAL[iv]:
        for c in CIK_TREND[iv]:
            configs.append((iv, dict(birincil="kanal", n=n, model="hepsi", **c)))
    for f, s in EMA[iv]:
        for c in CIK_TREND[iv]:
            configs.append((iv, dict(birincil="ema", hizli=f, yavas=s, model="hepsi", **c)))
    for k, z in DONUS[iv]:
        for c in CIK_DONUS[iv]:
            configs.append((iv, dict(birincil="donus", k=k, z=z, model="hepsi", **c)))
    for fz in FON:
        for c in CIK_FON[iv]:
            configs.append((iv, dict(birincil="fonlama", fz=fz, model="hepsi", **c)))

if __name__ == "__main__":
    print(len(configs), "yapılandırma", flush=True)
    ortak.tara(configs, "tarama1.csv")
    print("BITTI", flush=True)
