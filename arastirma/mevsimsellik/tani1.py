"""Tanı 1 (yalnız dev_train, deftere yazılmaz): al-tut kıyası, ay dönümü yıllık kararlılığı ve plasebo.

- Al-tut: harness run() + summarize, yalnız dev_train penceresi.
- Yıllık: deftere yazılmış ay dönümü yapılandırmalarının yıl ve bacak bazında getirisi (veri 2024 öncesine kesilir).
- Plasebo: aynı 6 günlük pencere ayın X. gününe göre kaydırılır (X = 1 ay dönümü), brüt günlük getiri.
"""
import numpy as np
import pandas as pd

from grafik_analiz.research import PERIODS, StrategySpec, run, summarize
from grafik_analiz.strategies.mevsimsellik import make_spec
from ortak import COINS, bar_returns, train_backtest, train_frame, yillik

pd.set_option("display.width", 250)


def hep_uzun(data, funding):
    out = {}
    for leg, df in data.items():
        s = pd.Series(1.0, index=df.index)
        if leg[0] == "futures":
            f = funding[leg[1]]
            s[df["close_time"] < f.index.min()] = 0.0
        out[leg] = s
    return out


print("=== Al-tut (dev_train, 1d) ===")
bh = {}
for m in ("spot", "futures"):
    for u in ("BTCUSDT", "ETHUSDT", "SOLUSDT", "PORT3", "PORT2"):
        legs = tuple((m, c) for c in (COINS if u == "PORT3" else COINS[:2] if u == "PORT2" else (u,)))
        spec = StrategySpec(f"al_tut_{m}_{u}", "mevsimsellik_kiyas", "1d", legs, hep_uzun, {})
        res = run(spec, "dev", 1.0)
        s = summarize(res.returns, res.trades, res.exposure, res.costs, res.funding, *PERIODS["dev_train"])
        r = res.returns[res.returns.index < PERIODS["dev_train"][1]]
        yr = (1 + r).groupby(r.index.year).prod() - 1
        bh[(m, u)] = yr
        print(f"{m:7s} {u:8s} getiri {s['total_return']:8.2f} Sharpe {s['sharpe']:5.2f} MDD {s['max_drawdown']:6.3f} başlangıç {s['start'][:10]} | yıllık: " + " ".join(f"{y}:{v:+.2f}" for y, v in yr.items()))

print("\n=== Ay dönümü yıllık getiri (dev_train, 1× maliyet) ===")
for name, m, a, b in [("tom_1d_spot_PORT3_a3_b3", "spot", 3, 3), ("tom_1d_fut_PORT3_a3_b3", "futures", 3, 3),
                      ("tom_1d_spot_PORT3_a4_b4", "spot", 4, 4), ("tom_1d_fut_PORT3_a4_b4", "futures", 4, 4),
                      ("tom_1d_fut_PORT3_a2_b2", "futures", 2, 2), ("tom_1d_spot_PORT3_a1_b3", "spot", 1, 3)]:
    spec = make_spec(name, "1d", m, "PORT3", {"yontem": "ay_donumu", "a": a, "b": b})
    yr = yillik(spec)
    yr2 = yillik(spec, 2.0)
    print(f"{name:28s} 1x: " + " ".join(f"{y}:{v:+.3f}" for y, v in yr.items()) + " | 2x: " + " ".join(f"{y}:{v:+.3f}" for y, v in yr2.items()))
    res = train_backtest(spec)
    for leg, lr in res.legs.items():
        n = lr.net
        ly = (1 + n).groupby(n.index.year).prod() - 1
        print(f"     {leg[1]}: " + " ".join(f"{y}:{v:+.3f}" for y, v in ly.items()))

print("\n=== Plasebo: 6 günlük pencere [X-3, X+2] (X = ayın günü; X=1 ay dönümü), 3 coin ort. brüt günlük getiri (bp) ===")
for m in ("spot", "futures"):
    rets = {}
    for c in COINS:
        df = train_frame(c, "1d", m)
        if m == "futures":
            df = df[df.index >= "2020-01-01"]
        rets[c] = bar_returns(df)
    res = []
    for X in range(1, 29):
        vals = []
        for c, r in rets.items():
            idx = r.index.tz_localize(None)
            inside = np.zeros(len(idx), dtype=bool)
            for k in (-1, 0, 1):
                per = (idx.to_period("M") + k).to_timestamp() + pd.to_timedelta(X - 1, unit="D")
                diff = (idx - per).days
                inside |= (diff >= -3) & (diff <= 2)
            vals.append(r[inside].mean() * 1e4 - r[~inside].mean() * 1e4)
        res.append((X, np.mean(vals)))
    s = pd.Series(dict(res))
    print(f"{m}: " + " ".join(f"{k}:{v:5.1f}" for k, v in s.items()))
    print(f"   X=1 sırası: {int((s >= s[1]).sum())}/28 ; ortanca fark {s.median():.1f} bp")
