"""Aşama 2 (dev_train, 1× maliyet): donus 1h komşuluğu + 15m/5m karşılıkları (grup B),
fitil 1h komşuluğu + 5m/15m derin seviyeler (grup A)."""
import sys

from ortak import degerlendir, done

grup = sys.argv[1]
CSV = f"tarama2_{grup}.csv"
bitti = done(CSV)


def run(name, interval, **p):
    if "t2_limit_gun_ici_" + name in bitti:
        return
    degerlendir(name, interval, CSV, **p)


if grup == "B":
    base = dict(yontem="donus", n=4, esik=3, vol_n=500, yon="uzun", trend_gun=50, trend_mod="ile", H=12, sig_n=168)

    def v(**kw):
        p = dict(base)
        p.update(kw)
        return p

    for d in (0.75, 1.5, 2.0):
        run(f"donus_1h_n4_e3_t50_H12_lim{d}s_m3", "1h", **v(giris="limit", d_sig=d, m=3))
    for m in (1, 6):
        run(f"donus_1h_n4_e3_t50_H12_lim1.0s_m{m}", "1h", **v(giris="limit", d_sig=1.0, m=m))
    for m in (3, 6):
        run(f"donus_1h_n4_e3_t50_H12_lim1.0s_m{m}_refsin", "1h", **v(giris="limit", d_sig=1.0, m=m, ref="sinyal"))
    for e in (2.5, 3.5):
        run(f"donus_1h_n4_e{e}_t50_H12_piyasa", "1h", **v(esik=e, giris="piyasa"))
        run(f"donus_1h_n4_e{e}_t50_H12_lim1.0s_m3", "1h", **v(esik=e, giris="limit", d_sig=1.0, m=3))
    for nn in (2, 6):
        run(f"donus_1h_n{nn}_e3_t50_H12_piyasa", "1h", **v(n=nn, giris="piyasa"))
        run(f"donus_1h_n{nn}_e3_t50_H12_lim1.0s_m3", "1h", **v(n=nn, giris="limit", d_sig=1.0, m=3))
    for H in (6, 24):
        run(f"donus_1h_n4_e3_t50_H{H}_lim1.0s_m3", "1h", **v(H=H, giris="limit", d_sig=1.0, m=3))
    for tg in (30, 100):
        run(f"donus_1h_n4_e3_t{tg}_H12_lim1.0s_m3", "1h", **v(trend_gun=tg, giris="limit", d_sig=1.0, m=3))
    run("donus_1h_n4_e3_t0_H12_lim1.0s_m3", "1h", **v(trend_gun=0, trend_mod="yok", giris="limit", d_sig=1.0, m=3))
    run("donus_1h_n4_e3_t50_H12_lim1.0s_m3_cik5b", "1h", **v(giris="limit", d_sig=1.0, m=3, cikis_bps=5, cikis_m=3))
    run("donus_1h_n4_e3_t50_H24_lim1.0s_m3_tp3s", "1h", **v(H=24, giris="limit", d_sig=1.0, m=3, tp_sig=3.0))
    # 15m karşılığı: 4 saatlik hareket (n=16), 12 saat tutma (H=48), σ 1 gün (96 bar)
    b15 = dict(yontem="donus", n=16, esik=3, vol_n=2000, yon="uzun", trend_gun=50, trend_mod="ile", H=48, sig_n=96)
    run("donus_15m_n16_e3_t50_H48_piyasa", "15m", giris="piyasa", **b15)
    run("donus_15m_n16_e3_t50_H48_lim1.0s_m12", "15m", giris="limit", d_sig=1.0, m=12, **b15)
    run("donus_15m_n16_e3_t50_H48_lim2.0s_m12", "15m", giris="limit", d_sig=2.0, m=12, **b15)
    # 5m karşılığı: n=48, H=144, σ 1 gün (288 bar)
    b5 = dict(yontem="donus", n=48, esik=3, vol_n=6000, yon="uzun", trend_gun=50, trend_mod="ile", H=144, sig_n=288)
    run("donus_5m_n48_e3_t50_H144_piyasa", "5m", giris="piyasa", **b5)
    run("donus_5m_n48_e3_t50_H144_lim2.0s_m36", "5m", giris="limit", d_sig=2.0, m=36, **b5)
    run("donus_5m_n48_e3_t50_H144_lim3.5s_m36", "5m", giris="limit", d_sig=3.5, m=36, **b5)

if grup == "A":
    f1 = dict(yontem="fitil", sig_n=168)
    for k in (2.5, 3.5, 4):
        for H in (1, 3, 6):
            run(f"fitil_1h_k{k}_H{H}", "1h", k=k, H=H, **f1)
    run("fitil_1h_k3_H3", "1h", k=3, H=3, **f1)
    run("fitil_1h_k3_H6_t50", "1h", k=3, H=6, trend_gun=50, trend_mod="ile", **f1)
    run("fitil_1h_k3_H1_t50", "1h", k=3, H=1, trend_gun=50, trend_mod="ile", **f1)
    for sn in (72, 336):
        run(f"fitil_1h_k3_H6_s{sn}", "1h", yontem="fitil", k=3, H=6, sig_n=sn)
    run("fitil_1h_k3_H6_cik5b", "1h", k=3, H=6, cikis_bps=5, cikis_m=3, **f1)
    run("fitil_1h_k3_H1_cik5b", "1h", k=3, H=1, cikis_bps=5, cikis_m=3, **f1)
    run("fitil_1h_k3_tp2_H12", "1h", k=3, H=12, tp_sig=2.0, **f1)
    f15 = dict(yontem="fitil", sig_n=96)
    for k in (5, 6):
        run(f"fitil_15m_k{k}_H16", "15m", k=k, H=16, **f15)
    run("fitil_15m_k4_tp2_H32", "15m", k=4, H=32, tp_sig=2.0, **f15)
    f5 = dict(yontem="fitil", sig_n=288)
    run("fitil_5m_k8_H24", "5m", k=8, H=24, **f5)
    run("fitil_5m_k6_H48", "5m", k=6, H=48, **f5)
    run("fitil_5m_k6_tp2_H48", "5m", k=6, H=48, tp_sig=2.0, **f5)
    run("fitil_5m_k6_H24_t50", "5m", k=6, H=24, trend_gun=50, trend_mod="ile", **f5)
