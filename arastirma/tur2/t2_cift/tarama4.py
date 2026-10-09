"""Tarama 4: şok sönümlenmesi inceltme, limit emirli (yalnız dev_train).

(a) Izgara: çift (SOLBTC, SOLETH, SOLBTC+SOLETH) × k (3/6/12) × z_in (3,5/4/5) ×
    tutma (3/6/12), limit 10 bp / 2 bar / her değişimde.
(b) Limit parametreleri: merkez (k6, z4, tutma 6) için bps (5/10/20) × bar (1/2/3).
Tarama 3 ile çakışan yapılandırmalar defterden alınır.
"""
import itertools
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from ortak import tara  # noqa: E402

CIFT = [["SOLBTC"], ["SOLETH"], ["SOLBTC", "SOLETH"]]
konf = []
for ciftler, k, zin, hold in itertools.product(CIFT, [3, 6, 12], [3.5, 4.0, 5.0], [3, 6, 12]):
    p = dict(ciftler=ciftler, hedge="bir", z_tur="sok", k=k, vol_win=500, z_in=zin, z_exit=None, max_bar=hold,
             limit_bps=10.0, limit_bar=2, limit_mod="tum")
    konf.append(("1h", p))
for ciftler, bps, bar in itertools.product(CIFT, [5.0, 10.0, 20.0], [1, 2, 3]):
    p = dict(ciftler=ciftler, hedge="bir", z_tur="sok", k=6, vol_win=500, z_in=4.0, z_exit=None, max_bar=6,
             limit_bps=bps, limit_bar=bar, limit_mod="tum")
    if ("1h", p) not in konf:
        konf.append(("1h", p))
print(len(konf), "yapılandırma", flush=True)
df = tara(konf, str(Path(__file__).parent / "tarama4.csv"))
cols = ["ad", "ret", "ret2", "sharpe", "mdd", "trades", "alfa", "beta", "maliyet", "fonlama", "maruz"]
print(df.sort_values("sharpe", ascending=False)[[c for c in cols if c in df]].head(50).to_string(float_format=lambda x: f"{x:.3f}"))
