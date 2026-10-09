"""Tarama 4: kanal uzunluğu / çıkış toplulukları (4h) ve 1h kanal varyantları. Yalnız dev_train, 1× ve 2×."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ortak  # noqa: E402

L = dict(model="logit", ozellik="tam")
configs = []
add = lambda iv, **p: configs.append((iv, p))  # noqa: E731
N4 = "n=14,20,30,48"
IZ60 = dict(cikis="iz", iz_k=3.0, H=60)
B60 = dict(cikis="bariyer", tp=3.0, sl=1.5, H=60)
MIX = dict(iz_k=3.0, tp=3.0, sl=1.5, H=60)
add("4h", birincil="kanal", topluluk=N4, **IZ60, **L)
add("4h", birincil="kanal", topluluk=N4, **B60, **L)
add("4h", birincil="kanal", topluluk=N4 + ";cikis=iz,bariyer", **MIX, model="hepsi")
add("4h", birincil="kanal", topluluk=N4 + ";cikis=iz,bariyer", **MIX, **L)
add("4h", birincil="kanal", topluluk=N4 + ";cikis=iz,bariyer", **MIX, **L, delta=0.03)
add("4h", birincil="kanal", topluluk=N4 + ";cikis=iz,bariyer", **MIX, model="logit", ozellik="temel")
add("4h", birincil="kanal", topluluk=N4 + ";cikis=iz,bariyer", **MIX, model="hgb", ozellik="tam")
# 1h
I1 = dict(cikis="iz", iz_k=3.0, H=120)
add("1h", birincil="kanal", n=96, cikis="bariyer", tp=3.0, sl=1.5, H=72, **L)
add("1h", birincil="kanal", n=192, **I1, model="hepsi")
add("1h", birincil="kanal", n=192, **I1, **L)
add("1h", birincil="kanal", n=96, **I1, **L, delta=0.05)
add("1h", birincil="kanal", topluluk="n=48,96,192", **I1, **L)

if __name__ == "__main__":
    print(len(configs), "yapılandırma", flush=True)
    ortak.tara(configs, "tarama4.csv", maliyetler=(1.0, 2.0))
    print("BITTI", flush=True)
