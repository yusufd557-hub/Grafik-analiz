"""Aşama 3 (yalnız dev_train): pencere zamanlaması duyarlılığı (4h barlar, ±4/±8 saat kaydırma), a=3, b=3 vadeli PORT3."""
from grafik_analiz.strategies.mevsimsellik import make_spec
from ortak import degerlendir

cfgs = []
for k in (-8, -4, 4, 8):
    cfgs.append((f"tom_4h_fut_PORT3_a3_b3_k{k:+d}", "4h", "futures", "PORT3", {"yontem": "ay_donumu", "a": 3, "b": 3, "kayma_saat": k}))
for name, iv, m, u, p in cfgs:
    row = degerlendir(make_spec(name, iv, m, u, p), "3")
    print(f"{name:32s} R1x {row['total_return_1x']:8.3f} S1x {row['sharpe_1x']:5.2f} R2x {row['total_return_2x']:8.3f} S2x {row['sharpe_2x']:5.2f} "
          f"MDD {row['max_drawdown_1x']:6.3f} n {row['trades_1x']:4d} exp {row['exposure_1x']:.2f}", flush=True)
