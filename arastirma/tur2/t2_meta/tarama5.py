"""Tarama 5: son birkaç yön (1h kanal uzun çıkış, 4h havuzlanmış birincil, 4h EMA). Yalnız dev_train, 1× ve 2×."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ortak  # noqa: E402

L = dict(model="logit", ozellik="tam")
configs = []
add = lambda iv, **p: configs.append((iv, p))  # noqa: E731
# 1h kanal, 4h'teki 10 günlük tutmaya benzer uzun çıkışlar
add("1h", birincil="kanal", n=96, cikis="bariyer", tp=3.0, sl=1.5, H=240, **L)
add("1h", birincil="kanal", n=96, cikis="iz", iz_k=4.0, H=240, model="hepsi")
add("1h", birincil="kanal", n=96, cikis="iz", iz_k=4.0, H=240, **L)
# 4h havuzlanmış birincil (tek model, "tur" özelliği)
add("4h", birincil="kanal+donus+fonlama", n=20, k=6, z=2.5, fz=2.0, cikis="bariyer", tp=3.0, sl=1.5, H=60, model="hepsi")
add("4h", birincil="kanal+donus+fonlama", n=20, k=6, z=2.5, fz=2.0, cikis="bariyer", tp=3.0, sl=1.5, H=60, **L)
# 4h EMA kesişimi, düşük min_olay
add("4h", birincil="ema", hizli=20, yavas=100, cikis="bariyer", tp=3.0, sl=1.5, H=60, model="hepsi", min_olay=150)
add("4h", birincil="ema", hizli=20, yavas=100, cikis="bariyer", tp=3.0, sl=1.5, H=60, **L, min_olay=150)

if __name__ == "__main__":
    print(len(configs), "yapılandırma", flush=True)
    ortak.tara(configs, "tarama5.csv", maliyetler=(1.0, 2.0))
    print("BITTI", flush=True)
