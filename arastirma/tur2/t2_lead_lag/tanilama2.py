"""Aşama 0 tanılama 2: kayan beta ile artık (izleyen − β·lider) ve ufuk tepkisi.
Yalnız eğitim verisi (< 2025-01-01). Kayan istatistikler geriye dönük.
"""
import numpy as np
import pandas as pd

from grafik_analiz.research import protocol
from grafik_analiz.research.data import load

assert protocol.PROTOCOL_VERSION == "2"
END = protocol.DEV_TRAIN_END
COINS = ("BTCUSDT", "ETHUSDT", "SOLUSDT")


def panel(interval, market="futures"):
    o, c = {}, {}
    for s in COINS:
        df = load(s, interval, market, "dev")
        df = df[df.index < END]
        o[s] = df["open"]
        c[s] = df["close"]
    return pd.DataFrame(o), pd.DataFrame(c)


for interval, win in (("5m", 288), ("15m", 96)):
    o, c = panel(interval)
    r = np.log(c).diff()
    lo = np.log(o)
    print(f"=== {interval}")
    for lead, fol in (("BTCUSDT", "ETHUSDT"), ("BTCUSDT", "SOLUSDT"), ("ETHUSDT", "SOLUSDT"), ("ETHUSDT", "BTCUSDT")):
        for k in (1, 3):
            x = r[lead].rolling(k).sum()
            y = r[fol].rolling(k).sum()
            beta = (r[fol].rolling(win).cov(r[lead]) / r[lead].rolling(win).var()).shift(1)
            e = y - beta * x
            ze = e / (r[fol] - beta * r[lead]).rolling(win).std().shift(1) / np.sqrt(k)
            zx = x / r[lead].rolling(win).std().shift(1) / np.sqrt(k)
            rows = []
            for h in (1, 2, 3, 6, 12):
                fwd = lo[fol].shift(-1 - h) - lo[fol].shift(-1)  # t+1 açılış -> t+1+h açılış
                fwdl = lo[lead].shift(-1 - h) - lo[lead].shift(-1)
                fwd_res = fwd - beta * fwdl
                for thr in (2.0, 3.0, 4.0):
                    m = ze.abs() > thr
                    s = -np.sign(ze[m])
                    v = (s * fwd[m]).dropna()
                    vr = (s * fwd_res[m]).dropna()
                    # lider büyük hareket + izleyen geride
                    m2 = (zx.abs() > thr) & (np.sign(ze) == -np.sign(zx)) & (ze.abs() > 1)
                    v2 = (np.sign(zx[m2]) * fwd[m2]).dropna()
                    yrs = (s * fwd[m]).groupby(fwd[m].index.year).mean() * 1e4
                    rows.append((h, thr, len(v), v.mean() * 1e4, vr.mean() * 1e4, len(v2), v2.mean() * 1e4, " ".join(f"{y}:{a:+.1f}" for y, a in yrs.items())))
            for h, thr, n, a, ar, n2, a2, yy in rows:
                print(f"{lead[:3]}->{fol[:3]} k={k} h={h:2d} |ze|>{thr}: n={n:6d} izleyen={a:+6.2f}bps artık={ar:+6.2f}bps | lider|z|>{thr}&geride n={n2:5d} {a2:+6.2f}bps | yıllar {yy}")
