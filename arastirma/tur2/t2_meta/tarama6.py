"""Tarama 6: dondurma kuralının gerektirdiği eksik ölçüler (yalnız dev_train).

- 2× maliyet: 4h kanal n20 bariyer H60 logit; 1h kanal n96 iz3 H120 logit.
- "hepsi" temel çizgisi: 4h kanal topluluğu n=14,20,30,48 bariyer H60 (1×).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ortak  # noqa: E402

L = dict(model="logit", ozellik="tam")
if __name__ == "__main__":
    ortak.tara([("4h", dict(birincil="kanal", n=20, cikis="bariyer", tp=3.0, sl=1.5, H=60, **L)),
                ("1h", dict(birincil="kanal", n=96, cikis="iz", iz_k=3.0, H=120, **L))], "tarama6.csv", maliyetler=(2.0,))
    ortak.tara([("4h", dict(birincil="kanal", topluluk="n=14,20,30,48", cikis="bariyer", tp=3.0, sl=1.5, H=60, model="hepsi"))], "tarama6.csv", maliyetler=(1.0,))
    print("BITTI", flush=True)
