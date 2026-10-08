"""Aşama 1 (yalnız dev_train): bütün yöntemlerin geniş taraması, ders kitabı / keşif değerleri."""
import pandas as pd

from grafik_analiz.strategies.mevsimsellik import make_spec
from ortak import degerlendir

M = {"spot": "spot", "futures": "fut"}
cfgs = []
# A. ay dönümü (1d)
for a, b in [(1, 3), (2, 2), (3, 3), (4, 4), (5, 5)]:
    for m in ("spot", "futures"):
        cfgs.append((f"tom_1d_{M[m]}_PORT3_a{a}_b{b}", "1d", m, "PORT3", {"yontem": "ay_donumu", "a": a, "b": b}))
cfgs.append(("tom_1d_fut_PORT3_a3_b3_uzunkisa", "1d", "futures", "PORT3", {"yontem": "ay_donumu", "a": 3, "b": 3, "yon": "uzun_kisa"}))
# B. haftanın günü (1d)
for tag, g in [("hs", [5, 6]), ("hi", [0, 1, 2, 3, 4]), ("persiz", [0, 1, 2, 4, 5, 6]), ("pzt_car", [0, 2])]:
    for m in ("spot", "futures"):
        cfgs.append((f"dow_1d_{M[m]}_PORT3_{tag}", "1d", m, "PORT3", {"yontem": "hafta_gunu", "gunler": g}))
# C. sabit saatler (1h)
for m in ("spot", "futures"):
    cfgs.append((f"saat_1h_{M[m]}_PORT3_utc21_22", "1h", m, "PORT3", {"yontem": "saat", "saatler_uzun": [21, 22]}))
    cfgs.append((f"saat_1h_{M[m]}_PORT3_ny17_18_hi", "1h", m, "PORT3", {"yontem": "saat", "tz": "America/New_York", "saatler_uzun": [17, 18], "hafta_ici": True}))
cfgs.append(("saat_1h_fut_PORT3_u21_22_k2_3", "1h", "futures", "PORT3", {"yontem": "saat", "saatler_uzun": [21, 22], "saatler_kisa": [2, 3]}))
POS = [0, 5, 6, 7, 10, 12, 13, 15, 18, 19, 21, 22]
NEG = [2, 3, 9, 14]
cfgs.append(("saat_1h_spot_PORT3_kesif_pozitif", "1h", "spot", "PORT3", {"yontem": "saat", "saatler_uzun": POS}))
cfgs.append(("saat_1h_fut_PORT3_kesif_poz_neg", "1h", "futures", "PORT3", {"yontem": "saat", "saatler_uzun": POS, "saatler_kisa": NEG}))
# D. fonlama anı (vadeli)
for e in (0.0003, 0.0005):
    cfgs.append((f"fon_1h_fut_PORT3_e{e:g}_b0_t60", "1h", "futures", "PORT3", {"yontem": "fonlama", "esik": e, "bas_dk": 0, "tut_dk": 60}))
cfgs.append(("fon_1h_fut_PORT3_e0.0003_b0_t120", "1h", "futures", "PORT3", {"yontem": "fonlama", "esik": 0.0003, "bas_dk": 0, "tut_dk": 120}))
cfgs.append(("fon_15m_fut_PORT3_e0.0003_b0_t30", "15m", "futures", "PORT3", {"yontem": "fonlama", "esik": 0.0003, "bas_dk": 0, "tut_dk": 30}))
cfgs.append(("fon_1h_fut_PORT3_e0.0003_bm60_t60_kisa", "1h", "futures", "PORT3", {"yontem": "fonlama", "esik": 0.0003, "bas_dk": -60, "tut_dk": 60, "yon": "kisa"}))
# E. uyarlamalı saat (1h)
for L in (90, 365):
    for e in (5, 10):
        cfgs.append((f"usaat_1h_fut_PORT3_L{L}_e{e}", "1h", "futures", "PORT3", {"yontem": "uyarlamali_saat", "L": L, "esik_bp": e}))
cfgs.append(("usaat_1h_spot_PORT3_L365_e10", "1h", "spot", "PORT3", {"yontem": "uyarlamali_saat", "L": 365, "esik_bp": 10, "kisa": False}))
# F. uyarlamalı ay içi gün (1d)
for L in (0, 24):
    for e in (20, 50):
        cfgs.append((f"uay_1d_spot_PORT3_L{L}_e{e}", "1d", "spot", "PORT3", {"yontem": "uyarlamali_ay", "L_ay": L, "esik_bp": e}))
cfgs.append(("uay_1d_fut_PORT3_L0_e20", "1d", "futures", "PORT3", {"yontem": "uyarlamali_ay", "L_ay": 0, "esik_bp": 20}))

print("yapılandırma:", len(cfgs))
rows = []
for name, iv, m, u, p in cfgs:
    row = degerlendir(make_spec(name, iv, m, u, p), "1")
    rows.append(row)
    print(f"{name:45s} R1x {row['total_return_1x']:8.3f} S1x {row['sharpe_1x']:5.2f} R2x {row['total_return_2x']:8.3f} S2x {row['sharpe_2x']:5.2f} "
          f"MDD {row['max_drawdown_1x']:6.3f} n {row['trades_1x']:6d} exp {row['exposure_1x']:.2f} cost {row['total_costs_1x']:.2f}", flush=True)
