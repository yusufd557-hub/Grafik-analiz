"""Aşama 2b — inceltme (vadeli, PORT3, piyasa emri, dev_train 1× ve 2×).

Kullanım: python tarama3.py <grup>
  artik15, artik5, uyum15, uyum5
"""
import sys

sys.path.insert(0, __import__("os").path.dirname(__file__))
from ortak import degerlendir  # noqa: E402

L = 2000
grup = sys.argv[1]
GRID = {
    "artik15": ("akis_artik", "15m", (12, 24, 48), (2.5, 3.0, 3.5), (4, 8, 16, 32)),
    "artik5": ("akis_artik", "5m", (36, 72, 144), (2.5, 3.0, 3.5), (12, 24, 48)),
    "uyum15": ("uyumsuzluk", "15m", (12, 24, 48), (2.5, 3.0, 3.5), (2, 4, 8)),
    "uyum5": ("uyumsuzluk", "5m", (36, 72, 144), (2.5, 3.0, 3.5), (6, 12, 24)),
}
kind, iv, ns, ks, holds = GRID[grup]
tag = "artik" if kind == "akis_artik" else "uyum"
for n in ns:
    for k in ks:
        for hold in holds:
            degerlendir(f"a3_{tag}_{iv}_n{n}_k{k}_h{hold}", "futures", iv, "tarama3.csv", cost2=True,
                        kind=kind, n=n, L=L, k=k, mode="devam", hold=hold)
