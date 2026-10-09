"""Motor doğrulaması (sentetik veri): motorun izlediği pozisyon backtest'inkiyle aynı mı,
seri kısaltılınca geçmiş sinyaller değişiyor mu. Gerçek veriye bakılmaz."""
import numpy as np
import pandas as pd

from grafik_analiz.research.backtest import backtest_leg
from grafik_analiz.strategies import t2_limit_gun_ici as lg

rng = np.random.default_rng(7)


def sentetik(n, freq="5min"):
    idx = pd.date_range("2021-01-01", periods=n, freq=freq, tz="UTC")
    r = rng.standard_t(4, n) * 0.002
    c = 100 * np.exp(np.cumsum(r))
    o = np.r_[100.0, c[:-1]] * (1 + rng.normal(0, 0.0001, n))
    hi = np.maximum(o, c) * (1 + np.abs(rng.normal(0, 0.0015, n)))
    lo = np.minimum(o, c) * (1 - np.abs(rng.normal(0, 0.0015, n)))
    return pd.DataFrame({"open": o, "high": hi, "low": lo, "close": c, "volume": 1.0}, index=idx)


cases = [
    dict(yontem="fitil", k=2.0, sig_n=100, H=6),
    dict(yontem="fitil", k=1.5, sig_n=100, H=12, tp_sig=1.0),
    dict(yontem="fitil", k=1.5, sig_n=100, H=12, tp_sig=1.0, sl_sig=3.0, yon="iki"),
    dict(yontem="fitil", k=1.0, sig_n=100, H=6, cikis_bps=3, cikis_m=3, yon="kisa"),
    dict(yontem="fitil", k=1.0, sig_n=100, H=6, yon="iki", trend_gun=1, trend_mod="ile"),
    dict(yontem="donus", n=4, esik=2.0, vol_n=200, d_sig=0.5, m=3, H=6),
    dict(yontem="donus", n=4, esik=2.0, vol_n=200, giris="piyasa", H=6, yon="iki"),
    dict(yontem="donus", n=4, esik=2.0, vol_n=200, d_bps=5, m=4, ref="sinyal", H=6, tp_bps=20, yon="iki"),
    dict(yontem="orb", or_saat=1, giris="seviye", m=6, yon="iki"),
    dict(yontem="orb", or_saat=2, giris="limit", d_bps=5, m=3, cikis_bps=2, cikis_m=2, yon="iki"),
    dict(yontem="orb", or_saat=2, giris="piyasa", yon="iki", orb_mod="ters"),
    dict(yontem="saat", bas_saat=21, sure_saat=2, d_bps=2, cikis_bps=2, cikis_m=3),
    dict(yontem="saat", bas_saat=3, sure_saat=1, giris="piyasa"),
]
df = sentetik(20000)
for p in cases:
    tgt, lim, orders, exits, posv = lg.leg_orders(df, p)
    sig = pd.DataFrame({"target": tgt, "limit": lim}, index=df.index)
    lr = backtest_leg(df, sig, market="futures", symbol="X")
    ok = np.allclose(posv, lr.position.to_numpy())
    # nedensellik: kesik seri
    bad = 0
    for frac in (0.3, 0.55, 0.81, 0.97):
        k = int(len(df) * frac)
        part = lg.leg_signal(df.iloc[:k], p)
        a = sig.iloc[:k]
        for col in ("target", "limit"):
            x, y = a[col].to_numpy(), part[col].to_numpy()
            both = np.isnan(x) & np.isnan(y)
            d = np.where(both, 0.0, np.abs(x - y))
            d = np.nan_to_num(d, nan=np.inf)
            bad += int((d > 1e-9).sum())
    nf = sum(1 for o in orders if o[3])
    print(p["yontem"], "poz_esit", ok, "kesik_fark", bad, "emir", len(orders), "dolan", nf, "maker", sum(1 for o in orders if o[3] and not o[5]), "cikis", len(exits), "islem", len(lr.trades))
