"""Aşama 4 (yalnız dev_train): kademeli (yamuk) ay dönümü topluluğu ve seçilen pencerenin BTC+ETH sürümü."""
import pandas as pd

from grafik_analiz.strategies.mevsimsellik import make_spec
from ortak import degerlendir, train_backtest, yillik

cfgs = [
    ("tomk_1d_fut_PORT3_a2-5_b2-5", "1d", "futures", "PORT3", {"yontem": "ay_donumu_kademeli", "a_alt": 2, "a_ust": 5, "b_alt": 2, "b_ust": 5}),
    ("tomk_1d_spot_PORT3_a2-5_b2-5", "1d", "spot", "PORT3", {"yontem": "ay_donumu_kademeli", "a_alt": 2, "a_ust": 5, "b_alt": 2, "b_ust": 5}),
    ("tom_1d_fut_PORT2_a4_b5", "1d", "futures", "PORT2", {"yontem": "ay_donumu", "a": 4, "b": 5}),
]
for name, iv, m, u, p in cfgs:
    spec = make_spec(name, iv, m, u, p)
    row = degerlendir(spec, "4")
    print(f"{name:32s} R1x {row['total_return_1x']:8.3f} S1x {row['sharpe_1x']:5.2f} R2x {row['total_return_2x']:8.3f} S2x {row['sharpe_2x']:5.2f} "
          f"MDD {row['max_drawdown_1x']:6.3f} n {row['trades_1x']:4d} exp {row['exposure_1x']:.2f} maliyet {row['total_costs_1x']:.3f}", flush=True)
    y = yillik(spec)
    y2 = yillik(spec, 2.0)
    print(f"    yıllık 1x: " + " ".join(f"{k}:{v:+.3f}" for k, v in y.items()) + "  | 2x>0: " + f"{(y2 > 0).sum()}/{(y2 != 0).sum()}")
    if name.startswith("tomk_1d_fut"):
        res = train_backtest(spec)
        pos = res.legs[("futures", "BTCUSDT")].position
        print(pos["2023-01-24":"2023-02-08"].to_string())
