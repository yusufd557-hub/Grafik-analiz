"""Aşama 2 (yalnız dev_train): ay dönümü pencere yüzeyi a, b = 1..6 (spot ve vadeli PORT3),
tek taraflı pencereler (yalnız ay sonu / yalnız ay başı) ve BTC+ETH (PORT2) evreni."""
from grafik_analiz.strategies.mevsimsellik import make_spec
from ortak import degerlendir

M = {"spot": "spot", "futures": "fut"}
cfgs = []
for m in ("spot", "futures"):
    for a in range(1, 7):
        for b in range(1, 7):
            cfgs.append((f"tom_1d_{M[m]}_PORT3_a{a}_b{b}", "1d", m, "PORT3", {"yontem": "ay_donumu", "a": a, "b": b}))
for a, b in [(0, 3), (3, 0), (0, 4), (4, 0)]:
    cfgs.append((f"tom_1d_fut_PORT3_a{a}_b{b}", "1d", "futures", "PORT3", {"yontem": "ay_donumu", "a": a, "b": b}))
for m in ("spot", "futures"):
    for a, b in [(3, 3), (4, 4), (3, 4), (4, 3)]:
        cfgs.append((f"tom_1d_{M[m]}_PORT2_a{a}_b{b}", "1d", m, "PORT2", {"yontem": "ay_donumu", "a": a, "b": b}))
print("yapılandırma (öncekiler dahil):", len(cfgs))
for name, iv, m, u, p in cfgs:
    row = degerlendir(make_spec(name, iv, m, u, p), "2")
    print(f"{name:32s} R1x {row['total_return_1x']:8.3f} S1x {row['sharpe_1x']:5.2f} R2x {row['total_return_2x']:8.3f} S2x {row['sharpe_2x']:5.2f} "
          f"MDD {row['max_drawdown_1x']:6.3f} n {row['trades_1x']:4d} exp {row['exposure_1x']:.2f} fon {row['total_funding_1x']:.3f}", flush=True)
