"""Tarama 1: temel z-skoru çift stratejisi, piyasa emri, filtre yok (yalnız dev_train)."""
import itertools
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from ortak import tara  # noqa: E402

konf = []
zw = {"1h": [48, 168, 500], "4h": [30, 90, 180]}
for iv in ["1h", "4h"]:
    for cift, hedge, w, zin in itertools.product(["ETHBTC", "SOLBTC", "SOLETH"], ["bir", "oyn", "ols"], zw[iv], [1.5, 2.0, 2.5]):
        p = dict(ciftler=[cift], hedge=hedge, z_win=w, z_in=zin, z_exit=0.0)
        if hedge == "oyn":
            p["hedge_win"] = 2 * w
        konf.append((iv, p))
print(len(konf), "yapılandırma", flush=True)
df = tara(konf, str(Path(__file__).parent / "tarama1.csv"))
cols = ["ad", "ret", "ret2", "sharpe", "mdd", "trades", "alfa", "beta", "maliyet", "fonlama", "maruz"]
pd_opts = dict(float_format=lambda x: f"{x:.3f}")
print(df.sort_values("sharpe", ascending=False)[cols].head(30).to_string(**pd_opts))
