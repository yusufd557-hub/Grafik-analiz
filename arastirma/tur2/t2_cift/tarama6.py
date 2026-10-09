"""Tarama 6: öncü şok yapılandırmalarının duyarlılığı (yalnız dev_train). Bkz. NOTLAR.md."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from ortak import tara  # noqa: E402

BASE = dict(hedge="bir", z_tur="sok", z_exit=None, limit_bar=2, limit_mod="tum")
ADAY = {
    "A": dict(ciftler=["SOLBTC"], k=6, z_in=4.0, max_bar=6, limit_bps=20.0),
    "B": dict(ciftler=["SOLBTC"], k=6, z_in=5.0, max_bar=6, limit_bps=10.0),
    "C": dict(ciftler=["SOLBTC", "SOLETH"], k=6, z_in=5.0, max_bar=6, limit_bps=10.0),
    "D": dict(ciftler=["SOLBTC", "SOLETH"], k=12, z_in=5.0, max_bar=3, limit_bps=10.0),
}
konf = []
for key, a in ADAY.items():
    for vw in (250, 1000):
        konf.append(("1h", dict(**BASE, **{**a, "vol_win": vw})))
    konf.append(("1h", dict(**BASE, **{**a, "vol_win": 500, "z_in": 4.5})))
    if key != "A":
        konf.append(("1h", dict(**BASE, **{**a, "vol_win": 500, "limit_bps": 20.0})))
    konf.append(("1h", dict(**BASE, **{**a, "vol_win": 500})))  # merkez (defterden)
print(len(konf), "yapılandırma", flush=True)
df = tara(konf, str(Path(__file__).parent / "tarama6.csv"))
cols = ["ad", "ret", "ret2", "sharpe", "mdd", "trades", "alfa", "beta", "maliyet", "fonlama", "maruz"]
print(df[[c for c in cols if c in df]].to_string(float_format=lambda x: f"{x:.3f}"))
