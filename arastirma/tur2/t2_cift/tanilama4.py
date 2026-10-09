"""Tanılama 4 (yalnız eğitim, veri 31.12.2024'te kesilir): tarama 3–4'te deftere yazılmış
şok yapılandırmalarının yıllık getiri / brüt / maliyet / fonlama dökümü."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from ortak import egitim_dokumu  # noqa: E402

L = dict(hedge="bir", z_tur="sok", vol_win=500, z_exit=None, limit_mod="tum")
K = [
    (["SOLBTC"], 6, 4.0, 6, 10.0, 2),
    (["SOLBTC"], 6, 4.0, 6, 20.0, 2),
    (["SOLBTC"], 6, 5.0, 6, 10.0, 2),
    (["SOLBTC", "SOLETH"], 6, 5.0, 6, 10.0, 2),
    (["SOLBTC", "SOLETH"], 12, 5.0, 3, 10.0, 2),
    (["SOLBTC", "SOLETH"], 6, 4.0, 6, 20.0, 2),
    (["SOLETH"], 6, 5.0, 6, 10.0, 2),
    (["SOLBTC"], 12, 3.5, 3, 10.0, 2),
]
for c, k, z, h, bps, bar in K:
    p = dict(ciftler=c, k=k, z_in=z, max_bar=h, limit_bps=bps, limit_bar=bar, **L)
    d = egitim_dokumu("1h", p)
    print("-".join(c), f"k{k} z{z} h{h} lim{bps}/{bar}",
          "yillik", json.dumps(d["yillik"]), "brut", round(d["brut_toplam"], 4),
          "maliyet", round(d["maliyet_toplam"], 4), "fonlama", round(d["fonlama_toplam"], 4), flush=True)
