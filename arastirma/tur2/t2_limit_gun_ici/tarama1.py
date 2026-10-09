"""Aşama 1: kaba ızgara (dev_train, 1× maliyet). Vadeli PORT3.

A) fitil: bekleyen derin alış limiti (yalnız alım), 5m/15m/1h; birkaç açığa satış ve iki yön kontrolü.
B) donus: tur 1 ret sinyali, giriş piyasa (kontrol) ve limit.
C) orb: 15m açılış aralığı kırılımı, giriş piyasa / seviye limiti / kapanış altı limit.
D) saat: tur 1'in incelediği saat pencereleri, limit giriş/çıkış.
"""
import sys

from ortak import degerlendir, done

grup = sys.argv[1] if len(sys.argv) > 1 else "hepsi"
CSV = "tarama1.csv" if grup in ("A", "hepsi") else f"tarama1_{grup}.csv"
bitti = done(CSV)


def run(name, interval, **p):
    full = "t2_limit_gun_ici_" + name
    if full in bitti:
        return
    degerlendir(name, interval, CSV, **p)


if grup in ("A", "hepsi"):
    # 5m: σ = son 1 günün (288 bar) bar getirisi std'si
    for k in (2, 3, 4, 6):
        for H in (1, 6, 24):
            run(f"fitil_5m_k{k}_H{H}", "5m", yontem="fitil", k=k, sig_n=288, H=H)
        run(f"fitil_5m_k{k}_tp1_H24", "5m", yontem="fitil", k=k, sig_n=288, H=24, tp_sig=1.0)
    for k in (2, 3, 4):
        for H in (1, 4):
            run(f"fitil_15m_k{k}_H{H}", "15m", yontem="fitil", k=k, sig_n=96, H=H)
        run(f"fitil_15m_k{k}_tp1_H16", "15m", yontem="fitil", k=k, sig_n=96, H=16, tp_sig=1.0)
    for k in (2, 3):
        for H in (1, 6):
            run(f"fitil_1h_k{k}_H{H}", "1h", yontem="fitil", k=k, sig_n=168, H=H)
    for k in (3, 4):
        run(f"fitil_5m_kisa_k{k}_H6", "5m", yontem="fitil", k=k, sig_n=288, H=6, yon="kisa")
    run("fitil_5m_iki_k3_H6", "5m", yontem="fitil", k=3, sig_n=288, H=6, yon="iki")

if grup in ("B", "hepsi"):
    # Tur 1 dönüş sinyali (ret): yükselen trendde dip alımı ve iki yönlü saf dönüş.
    base1h = dict(yontem="donus", n=4, esik=3, vol_n=500, yon="uzun", trend_gun=50, trend_mod="ile", H=12, sig_n=168)
    run("donus_1h_n4_e3_t50_H12_piyasa", "1h", giris="piyasa", **base1h)
    for d in (0.25, 0.5, 1.0):
        run(f"donus_1h_n4_e3_t50_H12_lim{d}s_m3", "1h", giris="limit", d_sig=d, m=3, **base1h)
    base15 = dict(yontem="donus", n=4, esik=3, vol_n=500, yon="uzun", trend_gun=50, trend_mod="ile", H=16, sig_n=96)
    run("donus_15m_n4_e3_t50_H16_piyasa", "15m", giris="piyasa", **base15)
    for d in (0.5, 1.0):
        run(f"donus_15m_n4_e3_t50_H16_lim{d}s_m4", "15m", giris="limit", d_sig=d, m=4, **base15)
    base5 = dict(yontem="donus", n=12, esik=3, vol_n=1500, yon="uzun", trend_gun=50, trend_mod="ile", H=48, sig_n=288)
    run("donus_5m_n12_e3_t50_H48_piyasa", "5m", giris="piyasa", **base5)
    for d in (0.5, 1.0):
        run(f"donus_5m_n12_e3_t50_H48_lim{d}s_m6", "5m", giris="limit", d_sig=d, m=6, **base5)
    iki15 = dict(yontem="donus", n=4, esik=3, vol_n=500, yon="iki", H=8, sig_n=96)
    run("donus_15m_iki_n4_e3_H8_piyasa", "15m", giris="piyasa", **iki15)
    run("donus_15m_iki_n4_e3_H8_lim1.0s_m4", "15m", giris="limit", d_sig=1.0, m=4, **iki15)
    iki5 = dict(yontem="donus", n=1, esik=4, vol_n=1500, yon="iki", H=12, sig_n=288)
    run("donus_5m_iki_n1_e4_H12_piyasa", "5m", giris="piyasa", **iki5)
    run("donus_5m_iki_n1_e4_H12_lim1.0s_m3", "5m", giris="limit", d_sig=1.0, m=3, **iki5)

if grup in ("C", "hepsi"):
    # 15m açılış aralığı kırılımı (UTC gün), gün sonu çıkış.
    for orh in (1, 2, 4):
        b = dict(yontem="orb", or_saat=orh, yon="iki", sig_n=96)
        run(f"orb_15m_or{orh}_piyasa", "15m", giris="piyasa", **b)
        run(f"orb_15m_or{orh}_seviye_m8", "15m", giris="seviye", m=8, **b)
        run(f"orb_15m_or{orh}_lim10b_m4", "15m", giris="limit", d_bps=10, m=4, **b)
    run("orb_15m_or2_seviye_m8_cik5b", "15m", yontem="orb", or_saat=2, yon="iki", sig_n=96, giris="seviye", m=8, cikis_bps=5, cikis_m=4)
    for orh in (1, 2):
        run(f"orb_15m_or{orh}_ters_lim10b_m4", "15m", yontem="orb", or_saat=orh, yon="iki", sig_n=96, orb_mod="ters", giris="limit", d_bps=10, m=4)

if grup in ("D", "hepsi"):
    # Saat pencereleri (UTC), 15m barlarda limit giriş/çıkış.
    run("saat_15m_21_2_uzun_piyasa", "15m", yontem="saat", bas_saat=21, sure_saat=2, yon="uzun", giris="piyasa", sig_n=96)
    run("saat_15m_21_2_uzun_lim3b_cik3b", "15m", yontem="saat", bas_saat=21, sure_saat=2, yon="uzun", d_bps=3, cikis_bps=3, cikis_m=4, sig_n=96)
    run("saat_15m_22_1_uzun_lim3b_cik3b", "15m", yontem="saat", bas_saat=22, sure_saat=1, yon="uzun", d_bps=3, cikis_bps=3, cikis_m=4, sig_n=96)
    run("saat_15m_02_1_kisa_lim3b_cik3b", "15m", yontem="saat", bas_saat=2, sure_saat=1, yon="kisa", d_bps=3, cikis_bps=3, cikis_m=4, sig_n=96)
