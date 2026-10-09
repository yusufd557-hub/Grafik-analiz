"""Tarama 5: trend yönünde geri çekilme (düzey z-skoru + uzun pencereli trend filtresi), yalnız dev_train.

Tanılamaya göre yayılımlar 1 günden uzun ufuklarda trend yapıyor (VR > 1), kısa ufukta
hafif dönüyor. Burada kısa pencereli düzey z'si yalnız uzun pencereli yayılım trendi
yönünde (rejim="trend", eşik 0: yalnız trend yönü; eşik 1: yalnız güçlü ters trendde
engelle) ortalamaya dönüş için kullanılır. Çıkış z = 0 ya da en fazla `max_bar` bar.
"""
import itertools
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from ortak import tara  # noqa: E402

CIFT = [["ETHBTC"], ["SOLBTC"], ["SOLETH"], ["ETHBTC", "SOLBTC", "SOLETH"]]
konf = []
# 1h: z penceresi 24/48 bar, uzun pencere 500/1500 bar
for ciftler, zw, zin, rw, esik in itertools.product(CIFT, [24, 48], [2.0, 2.5], [500, 1500], [0.0, 1.0]):
    p = dict(ciftler=ciftler, hedge="bir", z_win=zw, z_in=zin, z_exit=0.0, max_bar=zw,
             rejim="trend", rejim_win=rw, rejim_esik=esik, limit_bps=10.0, limit_bar=2, limit_mod="tum")
    konf.append(("1h", p))
# 4h: z penceresi 12/30 bar, uzun pencere 180/500 bar
for ciftler, zw, zin, rw, esik in itertools.product(CIFT, [12, 30], [2.0, 2.5], [180, 500], [0.0, 1.0]):
    p = dict(ciftler=ciftler, hedge="bir", z_win=zw, z_in=zin, z_exit=0.0, max_bar=zw,
             rejim="trend", rejim_win=rw, rejim_esik=esik, limit_bps=10.0, limit_bar=2, limit_mod="tum")
    konf.append(("4h", p))
print(len(konf), "yapılandırma", flush=True)
df = tara(konf, str(Path(__file__).parent / "tarama5.csv"))
cols = ["ad", "ret", "ret2", "sharpe", "mdd", "trades", "alfa", "beta", "maliyet", "fonlama", "maruz"]
print(df.sort_values("sharpe", ascending=False)[[c for c in cols if c in df]].head(40).to_string(float_format=lambda x: f"{x:.3f}"))
