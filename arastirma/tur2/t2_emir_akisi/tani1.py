"""Tanı 1 (yalnız dev_train): aşırı fiyat düşüşü olaylarında akışın ek bilgisi.

5m vadeli BTC/ETH/SOL, n=72, L=2000. Olay barı t: kapanışta bilinen skorlar.
İleri getiri: t+1 açılışından t+1+h açılışına (strateji yürütmesiyle aynı), h=12.
Defterle ilgisi yok (strateji değerlendirmesi değil); dev_valid'e bakılmaz.
"""
import numpy as np
import pandas as pd

from grafik_analiz.research.data import load
from grafik_analiz.research.protocol import DEV_TRAIN_END
from grafik_analiz.strategies import t2_emir_akisi as ea

IV, N, L, H = "5m", 72, 2000, 12
rows = []
for sym in ea.COINS:
    df = load(sym, IV, "futures", scope="dev")
    df = df[df.index < DEV_TRAIN_END]
    close = df["close"].astype(float)
    zf = ea._zscore(ea.flow(df, N), L)
    zr = ea._zscore(np.log(close).diff(N), L)
    o = df["open"].astype(float)
    fwd = o.shift(-(H + 1)) / o.shift(-1) - 1.0  # tanı: geleceğe bakan etiket, yalnız ölçüm için
    rows.append(pd.DataFrame({"sym": sym, "zf": zf, "zr": zr, "u": zf - zr, "fwd": fwd}).dropna())
d = pd.concat(rows)
print(f"gözlem {len(d)}, corr(zf, zr) = {d[['zf','zr']].corr().iloc[0,1]:.3f}")


def show(mask, label):
    x = d[mask]
    print(f"{label:45s} n={len(x):6d}  ort ileri {x.fwd.mean()*1e4:+7.1f} bps  medyan {x.fwd.median()*1e4:+6.1f}  "
          f"isabet {np.mean(x.fwd>0):.2f}  ort zr {x.zr.mean():+.2f} zf {x.zf.mean():+.2f}")


show(d.u > 3.5, "uyumsuzluk > 3,5 (uzun)")
show(d.zr < -5, "zr < -5 (fiyat dönüşü uzun)")
show(d.zr < -4, "zr < -4")
show((d.u > 3.5) & (d.zr < -4), "u>3,5 ve zr<-4")
show((d.u > 3.5) & (d.zr >= -4), "u>3,5 ve zr>=-4")
show((d.zr < -4) & (d.u <= 3.5), "zr<-4 ve u<=3,5")
print("\nzr < -4 olaylarında zf'ye göre üçte birlikler:")
ev = d[d.zr < -4].copy()
ev["q"] = pd.qcut(ev.zf, 3, labels=["zf düşük (satış ağır)", "orta", "zf yüksek"])
for q, g in ev.groupby("q", observed=True):
    print(f"  {q:22s} n={len(g):5d} ort {g.fwd.mean()*1e4:+7.1f} bps isabet {np.mean(g.fwd>0):.2f} zr ort {g.zr.mean():+.2f}")
print("\nzr aralığına göre, akış yüksek/düşük (zf - beklenen):")
ev = d[d.zr < -3].copy()
b = np.polyfit(d.zr, d.zf, 1)
ev["res"] = ev.zf - np.polyval(b, ev.zr)
ev["zb"] = pd.cut(ev.zr, [-np.inf, -6, -5, -4, -3])
for zb, g in ev.groupby("zb", observed=True):
    hi, lo = g[g.res > 0], g[g.res <= 0]
    print(f"  zr {str(zb):14s} n={len(g):5d}  artık>0: {hi.fwd.mean()*1e4:+7.1f} bps (n={len(hi)})  artık<=0: {lo.fwd.mean()*1e4:+7.1f} bps (n={len(lo)})")
# basit regresyon: olaylarda (zr<-3) ileri getiri ~ zr + zf
X = np.column_stack([np.ones(len(ev)), ev.zr, ev.zf])
coef, *_ = np.linalg.lstsq(X, ev.fwd.to_numpy(), rcond=None)
res = ev.fwd.to_numpy() - X @ coef
cov = (res @ res) / (len(ev) - 3) * np.linalg.inv(X.T @ X)
print("\nzr<-3 olaylarında fwd ~ 1 + zr + zf: katsayı (bps) ve t:",
      [f"{c*1e4:+.1f} (t {c/np.sqrt(cov[i,i]):+.2f})" for i, c in enumerate(coef)])
