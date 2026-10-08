"""Kısa listedeki yapılandırmaların dev_train günlük getiri korelasyonu ve al-tut betası (seri 2024 öncesine kesilir)."""
import pandas as pd

from grafik_analiz.research import DEV_TRAIN_END, StrategySpec, daily_returns, run
from grafik_analiz.strategies.formasyon import make_spec
from ortak import done_keys, key_of, name_for

ADAY = {
    "F1": ("4h", "futures", {"yontem": "grafik", "tipler": ["ucgen", "kama"], "yon": "uzun", "cikis": "hedef", "trend_n": 200}),
    "F2": ("4h", "futures", {"yontem": "grafik", "tipler": ["ucgen", "kama"], "yon": "iki", "cikis": "hedef", "hacim_k": 1.5}),
    "F3": ("4h", "futures", {"yontem": "grafik", "tipler": "hepsi", "yon": "uzun", "cikis": "sure", "max_bar": 10, "trend_n": 200}),
    "F4": ("1d", "futures", {"yontem": "grafik", "tipler": "hepsi", "yon": "iki", "cikis": "hedef", "olcekler": [2.0, 3.0, 4.0]}),
    "F5": ("1d", "futures", {"yontem": "mum", "tipler": "marubozu", "yon": "iki", "cikis": "atr", "stop_k": 2.0, "hedef_atr": 4.0, "tutma": 20}),
}
dk = done_keys()
series = {}
for k, (iv, m, p) in ADAY.items():
    assert key_of(iv, m, "PORT3", p) in dk, k
    res = run(make_spec(name_for(iv, m, "PORT3", p), iv, m, "PORT3", p), "dev", 1.0)
    r = res.returns[res.returns.index < DEV_TRAIN_END]
    series[k] = daily_returns(r)

def hep_uzun(data, funding):
    out = {}
    for (market, sym), df in data.items():
        s = pd.Series(1.0, index=df.index)
        s[df["close_time"] < funding[sym].index[0]] = 0.0
        out[(market, sym)] = s
    return out

bh = run(StrategySpec("al_tut", "formasyon_kiyas", "1d", tuple(("futures", c) for c in ("BTCUSDT", "ETHUSDT", "SOLUSDT")), hep_uzun, {}), "dev", 1.0)
series["AL_TUT"] = daily_returns(bh.returns[bh.returns.index < DEV_TRAIN_END])
df = pd.DataFrame(series).dropna()
df = df[df.index >= "2020-01-01"]
print("gün", len(df), df.index[0], df.index[-1])
print(df.corr().round(2))
for k in ADAY:
    beta = df[k].cov(df["AL_TUT"]) / df["AL_TUT"].var()
    print(k, "beta", round(beta, 3))
