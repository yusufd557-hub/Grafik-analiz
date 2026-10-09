"""Tarama 2: yayılım şoku sönümlenmesi (z_tur='sok'), piyasa emri (yalnız dev_train)."""
import itertools
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from ortak import tara  # noqa: E402

konf = []
for cift, hedge, k, zin, hold in itertools.product(["ETHBTC", "SOLBTC", "SOLETH"], ["bir", "oyn"], [1, 3, 6], [3.0, 4.0], [3, 6, 12]):
    p = dict(ciftler=[cift], hedge=hedge, z_tur="sok", k=k, vol_win=500, z_in=zin, z_exit=None, max_bar=hold)
    if hedge == "oyn":
        p["hedge_win"] = 500
    konf.append(("1h", p))
for cift, hedge, k, zin, hold in itertools.product(["ETHBTC", "SOLBTC", "SOLETH"], ["bir", "oyn"], [1, 2], [3.0, 4.0], [1, 3]):
    p = dict(ciftler=[cift], hedge=hedge, z_tur="sok", k=k, vol_win=500, z_in=zin, z_exit=None, max_bar=hold)
    if hedge == "oyn":
        p["hedge_win"] = 500
    konf.append(("4h", p))
print(len(konf), "yapılandırma", flush=True)
df = tara(konf, str(Path(__file__).parent / "tarama2.csv"))
cols = ["ad", "ret", "ret2", "sharpe", "mdd", "trades", "alfa", "beta", "maliyet", "fonlama", "maruz"]
print(df.sort_values("sharpe", ascending=False)[cols].head(40).to_string(float_format=lambda x: f"{x:.3f}"))
