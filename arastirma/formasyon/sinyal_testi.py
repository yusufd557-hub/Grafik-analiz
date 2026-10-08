"""Sinyal doğruluk testleri (getiri hesaplamaz, deftere yazmaz)."""
import time

import numpy as np
import pandas as pd

from grafik_analiz.research import assert_causal, load, load_funding
from grafik_analiz.strategies import formasyon as F

df = load("BTCUSDT", "4h", "spot", "dev")
br = F._breakouts(df, (2.0, 4.0))
print("kırılım sayısı", len(br), br["key"].value_counts().to_dict())
print(br.head(5).to_string())

# 1) Pozisyon girişleri kırılım barlarında mı?
p = {"tipler": "hepsi", "yon": "iki", "cikis": "hedef"}
pos = F._grafik_leg(df, np.ones(len(df), bool), p)
chg = np.flatnonzero(np.diff(np.concatenate([[0], pos])) != 0)
entries = [i for i in chg if pos[i] != 0]
bars = set(br["bar"].tolist())
print("giriş", len(entries), "kırılım barında olmayan giriş:", sum(i not in bars for i in entries))

# 2) Hedef/stop çıkışları kapanışla doğru mu (ilk 5 işlem)
close = df["close"].to_numpy()
sub = br.iloc[F._dedupe(br["bar"].to_numpy(), br["dir"].to_numpy())]
for _, r in sub.head(5).iterrows():
    j = int(r["bar"]); d = r["dir"]
    k = j + 1
    while k < len(pos) and pos[k] == d and k < j + r["outcome_bars"] + 2:
        k += 1
    print(r["key"], "dir", d, "giriş", df.index[j], "kapanış", round(close[j], 1), "hedef", round(r["target"], 1), "stop", round(r["stop"], 1),
          "çıkış barı", df.index[min(k, len(df)-1)], "kapanış", round(close[min(k, len(df)-1)], 1), "tutulan", k - j)

# 3) Vadeli 1d maske
dff = load("BTCUSDT", "1d", "futures", "dev")
fund = load_funding("BTCUSDT", "dev")
sig = F.sinyal({("futures", "BTCUSDT"): dff}, {"BTCUSDT": fund}, yontem="mum", tipler="hepsi", yon="iki", tutma=10)[("futures", "BTCUSDT")]
print("fonlama öncesi sıfır olmayan pozisyon:", int((sig[sig.index < fund.index[0]] != 0).sum()), "toplam sıfır olmayan", int((sig != 0).sum()))

# 4) Spot kırpma
sig = F.sinyal({("spot", "BTCUSDT"): df}, {}, yontem="grafik", tipler="hepsi", yon="iki")[("spot", "BTCUSDT")]
print("spot min/max", sig.min(), sig.max())

# 5) assert_causal (deftere yazmaz)
for interval, market, params in [
    ("4h", "futures", {"yontem": "grafik", "tipler": "hepsi", "yon": "iki", "cikis": "hedef", "trend_n": 200}),
    ("1h", "spot", {"yontem": "grafik", "tipler": ["bayrak", "ucgen"], "yon": "uzun", "cikis": "sure", "max_bar": 20, "hacim_k": 1.5}),
    ("1d", "futures", {"yontem": "mum", "tipler": "hepsi", "yon": "iki", "cikis": "atr", "stop_k": 2, "hedef_atr": 3, "tutma": 10, "trend_n": 50}),
]:
    spec = F.make_spec("test", interval, market, "PORT3", params)
    t0 = time.time()
    assert_causal(spec, fractions=(0.3, 0.55, 0.8, 0.97))
    print("assert_causal geçti", interval, market, params["yontem"], round(time.time() - t0, 1), "sn")
