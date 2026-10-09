"""Aşama 0 tanılama: ham öncü–izleyen ilişkisi (yalnız eğitim verisi, < 2025-01-01).

Strateji değerlendirmesi değildir. Bir sonraki barın açılıştan açılışa getirisi
(stratejinin gerçekleşen getirisi) ile liderin son k barlık getirisi arasındaki
ilişki bps cinsinden ölçülür.
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


for interval in ("5m", "15m"):
    o, c = panel(interval)
    r = np.log(c).diff()  # bar t getirisi (kapanıştan kapanışa)
    fwd = np.log(o.shift(-2) / o.shift(-1))  # t+1 açılış -> t+2 açılış (gerçekleşen)
    print(f"=== {interval} vadeli, eğitim: {o.index[0]} .. {o.index[-1]}")
    for lead in COINS:
        for fol in COINS:
            if lead == fol:
                continue
            for k in (1, 2, 3):
                x = r[lead].rolling(k).sum()
                own = r[fol].rolling(k).sum()
                df = pd.concat([x.rename("x"), own.rename("own"), fwd[fol].rename("y")], axis=1).dropna()
                if len(df) < 1000:
                    continue
                X = np.column_stack([np.ones(len(df)), df["x"], df["own"]])
                coef, *_ = np.linalg.lstsq(X, df["y"].to_numpy(), rcond=None)
                cx = np.corrcoef(df["x"], df["y"])[0, 1]
                # Büyük lider hareketleri: |x| > 3 std (kayan değil, burada yalnız tanı)
                sd = df["x"].std()
                big = df[df["x"].abs() > 3 * sd]
                m = (np.sign(big["x"]) * big["y"]).mean() * 1e4
                # artık: izleyen liderden geride
                res = df["x"] - df["own"]
                bigr = df[(df["x"].abs() > 3 * sd)]
                mm = (np.sign(bigr["x"] - bigr["own"]) * bigr["y"]).mean() * 1e4
                print(f"{lead[:3]}->{fol[:3]} k={k}: corr={cx:+.4f} b_lead={coef[1]:+.4f} b_own={coef[2]:+.4f} n={len(df)} | |x|>3sd n={len(big)} yön_ort={m:+.2f}bps artık_yön_ort={mm:+.2f}bps")
