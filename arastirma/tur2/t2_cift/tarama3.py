"""Tarama 3: yayılım şoku sönümlenmesi + limit emir + üç çift portföyü (yalnız dev_train).

Tarama 2'de pozitif çıkan bölge (1h, bir, k 3/6, z_in 3/4, tutma 3/6) etrafında:
çift (SOLBTC, SOLETH, üçlü portföy) × limit emir modu. Limitsiz tekli çiftler
tarama 2'de defterde olduğundan yeniden değerlendirilmez (defterden alınır).
"""
import itertools
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from ortak import tara  # noqa: E402

LIM = [
    {},
    dict(limit_bps=5.0, limit_bar=1, limit_mod="tum"),
    dict(limit_bps=10.0, limit_bar=2, limit_mod="tum"),
    dict(limit_bps=5.0, limit_bar=1, limit_mod="giris"),
]
konf = []
for ciftler, k, zin, hold, lim in itertools.product(
    [["SOLBTC"], ["SOLETH"], ["ETHBTC", "SOLBTC", "SOLETH"]], [3, 6], [3.0, 4.0], [3, 6], LIM
):
    p = dict(ciftler=ciftler, hedge="bir", z_tur="sok", k=k, vol_win=500, z_in=zin, z_exit=None, max_bar=hold, **lim)
    konf.append(("1h", p))
print(len(konf), "yapılandırma", flush=True)
df = tara(konf, str(Path(__file__).parent / "tarama3.csv"))
cols = ["ad", "ret", "ret2", "sharpe", "mdd", "trades", "alfa", "beta", "maliyet", "fonlama", "maruz"]
print(df.sort_values("sharpe", ascending=False)[[c for c in cols if c in df]].head(40).to_string(float_format=lambda x: f"{x:.3f}"))
